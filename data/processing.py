###
#
# Given, in the data/output/scan/results directory:
#
# * domains.csv - federal domains, subset of .gov domain list.
#
# * pshtt.csv - domain-scan, based on pshtt
# * tls.csv - domain-scan, based on ssllabs-scan
# * analytics.csv - domain-scan, based on analytics.usa.gov data
#
###

import errno
import logging
import csv
import json
import yaml
import os
import glob
import slugify
import datetime
import subprocess

from statistics import mean

this_dir = os.path.dirname(__file__)

META = yaml.safe_load(open(os.path.join(this_dir, "../meta.yml")))
DOMAINS = os.environ.get("DOMAINS", META["data"]["domains_url"])

# domains.csv is downloaded and live-cached during the scan
INPUT_DOMAINS_DATA = os.path.join(this_dir, "./output/scan/cache")
INPUT_SCAN_DATA = os.path.join(this_dir, "./output/scan/results")

# Base directory for scanned subdomain data.
SUBDOMAIN_SCAN_DATA = os.path.join(this_dir, "./output/subdomains/scan")
SUBDOMAIN_AGENCY_OUTPUT = os.path.join(this_dir, "./output/subdomains/agencies/")
# Maps domain-scan names to specific sources,
# and whitelists which sources we know how to process.
SUBDOMAIN_SOURCES = {'censys': 'censys', 'url': 'dap'}

###
# Main task flow.

from app import models
from app.models import Report, Domain, Agency
from app.data import LABELS, DOMAIN_TYPES


# Read in data from domains.csv, and scan data from domain-scan.
# All database operations are made in the run() method.
#
# This method blows away the database and rebuilds it from the given data.

def run(date):
  if date is None:
    date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")

  # Reset the database.
  print("Clearing the database.")
  models.clear_database()
  Report.create(date)

  # Read in domains and agencies from domains.csv.
  # Returns dicts of values ready for saving as Domain and Agency objects.
  domains, agencies = load_domain_data()

  # Read in domain-scan CSV data.
  scan_data = load_scan_data(domains)

  # Load in some manual exclusion data.
  analytics_ineligible = yaml.safe_load(open(os.path.join(this_dir, "ineligible/analytics.yml")))
  analytics_ineligible_map = {}
  for domain in analytics_ineligible:
    analytics_ineligible_map[domain] = True

  # Pull out a few pshtt.csv fields as general domain metadata.
  for domain_name in scan_data.keys():
    analytics = scan_data[domain_name].get('analytics', None)
    if analytics:
      ineligible = analytics_ineligible_map.get(domain_name, False)
      domains[domain_name]['exclude']['analytics'] = ineligible


    pshtt = scan_data[domain_name].get('pshtt', None)
    if pshtt is None:
      # generally means scan was on different domains.csv, but
      # invalid domains can hit this.
      print("[%s][WARNING] No pshtt data for domain!" % domain_name)

      # Remove the domain from further consideration.
      # Destructive, so have this done last.
      del domains[domain_name]
    else:
      # print("[%s] Updating with pshtt metadata." % domain_name)
      domains[domain_name]['live'] = boolean_for(pshtt['Live'])
      domains[domain_name]['redirect'] = boolean_for(pshtt['Redirect'])
      domains[domain_name]['canonical'] = pshtt['Canonical URL']


  # Save what we've got to the database so far.

  sorted_domains = list(domains.keys())
  sorted_domains.sort()
  sorted_agencies = list(agencies.keys())
  sorted_agencies.sort()

  for domain_name in sorted_domains:
    Domain.create(domains[domain_name])
    print("[%s] Created." % domain_name)
  for agency_name in sorted_agencies:
    Agency.create(agencies[agency_name])
    # print("[%s] Created." % agency_name)


  # Calculate high-level per-domain conclusions for each report.
  domain_reports, subdomain_reports = process_domains(domains, agencies, scan_data)

  # Convenience: write out subdomain reports as CSVs per-agency.
  save_subdomain_reports(subdomain_reports)

  # Save them in the database.
  sorted_types = list(domain_reports.keys())
  sorted_types.sort()
  for report_type in sorted_types:

    sorted_reports = list(domain_reports[report_type].keys())
    sorted_reports.sort()

    for domain_name in sorted_reports:
      print("[%s][%s] Adding report." % (report_type, domain_name))
      Domain.add_report(domain_name, report_type, domain_reports[report_type][domain_name])

  # Calculate agency-level summaries.
  update_agency_totals()

  # Create top-level summaries.
  reports = latest_reports()
  for report in reports:
    Report.update(report)

  print_report()


# Reads in input CSVs (domain list).
def load_domain_data():

  domain_map = {}
  agency_map = {}

  # if domains.csv wasn't cached, download it anew
  domains_path = os.path.join(INPUT_DOMAINS_DATA, "domains.csv")
  if not os.path.exists(domains_path):
    print("Downloading domains.csv...")
    mkdir_p(INPUT_DOMAINS_DATA)
    shell_out(["wget", DOMAINS, "-O", domains_path])

  if not os.path.exists(domains_path):
    print("Couldn't download domains.csv")
    exit(1)

  with open(domains_path, newline='') as csvfile:
    for row in csv.reader(csvfile):
      if row[0].lower().startswith("domain"):
        continue

      domain_name = row[0].lower().strip()
      domain_type = nice_domain_type_for(row[1].strip())
      agency_name = row[2].strip()
      state = ''

      if domain_type != "federal":
        agency_name = row[3].strip() # City
        state = row[4].strip()

      agency_slug = slugify.slugify(agency_name)
      branch = "" # empty branch disables analytics

      # Exclude cities, counties, tribes, etc.
      #if domain_type != "Federal Agency":
      #  continue

      # There are a few erroneously marked non-federal domains.
      #if branch == "non-federal":
      #  continue

      if domain_name not in domain_map:
        domain_map[domain_name] = {
          'domain': domain_name,
          'domain_type': domain_type,
          'agency_name': agency_name,
          'agency_slug': agency_slug,
          'branch': branch,
          'state': state,
          'exclude': {}
        }

      if agency_slug not in agency_map:
        agency_map[agency_slug] = {
          'name': agency_name,
          'slug': agency_slug,
          'type': domain_type,
          'branch': branch,
          'state': state,
          'total_domains': 1
        }

      else:
        agency_map[agency_slug]['total_domains'] += 1

  return domain_map, agency_map


# Load in data from the CSVs produced by domain-scan.
# The 'domains' map is used to ignore any untracked domains.
def load_scan_data(domains):

  scan_data = {}
  for domain_name in domains.keys():
    scan_data[domain_name] = {}

  headers = []
  with open(os.path.join(INPUT_SCAN_DATA, "pshtt.csv"), newline='') as csvfile:
    for row in csv.reader(csvfile):
      if (row[0].lower() == "domain"):
        headers = row
        continue

      domain = row[0].lower()
      if not domains.get(domain):
        if domains.get(strip_www(domain)):
          domain = strip_www(domain)
        else:
          # print("[pshtt] Skipping %s, not a federal domain from domains.csv." % domain)
          continue

      dict_row = {}
      for i, cell in enumerate(row):
        dict_row[headers[i]] = cell
      scan_data[domain]['pshtt'] = dict_row

  if os.path.exists(os.path.join(INPUT_SCAN_DATA, "tls.csv")):
    headers = []
    with open(os.path.join(INPUT_SCAN_DATA, "tls.csv"), newline='') as csvfile:
      for row in csv.reader(csvfile):
        if (row[0].lower() == "domain"):
          headers = row
          continue

        domain = row[0].lower()
        if not domains.get(domain):
          # print("[tls] Skipping %s, not a federal domain from domains.csv." % domain)
          continue

        dict_row = {}
        for i, cell in enumerate(row):
          dict_row[headers[i]] = cell

        # For now: overwrite previous rows if present, use last endpoint.
        scan_data[domain]['tls'] = dict_row

  # Now, analytics measurement.
  if os.path.exists(os.path.join(INPUT_SCAN_DATA, "analytics.csv")):
    headers = []
    with open(os.path.join(INPUT_SCAN_DATA, "analytics.csv"), newline='') as csvfile:
      for row in csv.reader(csvfile):
        if (row[0].lower() == "domain"):
          headers = row
          continue

        domain = row[0].lower()
        if not domains.get(domain):
          # print("[analytics] Skipping %s, not a federal domain from domains.csv." % domain)
          continue

        # If it didn't appear in the pshtt data, skip it, we need this.
        # if not domains[domain].get('pshtt'):
        #   print("[analytics] Skipping %s, did not appear in pshtt.csv." % domain)
        #   continue

        dict_row = {}
        for i, cell in enumerate(row):
          dict_row[headers[i]] = cell

        scan_data[domain]['analytics'] = dict_row

  # And a11y! Only try to load it if it exists, since scan is not yet automated.
  if os.path.isfile(os.path.join(INPUT_SCAN_DATA, "a11y.csv")):
    headers = []
    with open(os.path.join(INPUT_SCAN_DATA, "a11y.csv"), newline='') as csvfile:
      for row in csv.reader(csvfile):
        if (row[0].lower() == "domain"):
          headers = row
          continue

        domain = row[0].lower()
        if not domains.get(domain):
          continue

        dict_row = {}
        for i, cell in enumerate(row):
          dict_row[headers[i]] = cell
        if not scan_data[domain].get('a11y'):
          scan_data[domain]['a11y'] = [dict_row]
        else:
          scan_data[domain]['a11y'].append(dict_row)

  # Customer satisfaction, as well. Same as a11y, only load if it exists
  if os.path.isfile(os.path.join(INPUT_SCAN_DATA, "third_parties.csv")):
    headers = []
    with open(os.path.join(INPUT_SCAN_DATA, "third_parties.csv"), newline='') as csvfile:
      for row in csv.reader(csvfile):
        if (row[0].lower() == "domain"):
          headers = row
          continue

        domain = row[0].lower()
        if not domains.get(domain):
          # print("[tls] Skipping %s, not a federal domain from domains.csv." % domain)
          continue

        dict_row = {}
        for i, cell in enumerate(row):
          dict_row[headers[i]] = cell

        scan_data[domain]['cust_sat'] = dict_row


  # Next, load in subdomain pshtt data (if present).
  subdomain_dirs = glob.glob("%s/*" % SUBDOMAIN_SCAN_DATA)
  for scan_dir in subdomain_dirs:
    sub_dir = os.path.split(scan_dir)[-1]
    source = SUBDOMAIN_SOURCES[sub_dir]

    # We scan subdomains with pshtt only.
    source_csv = os.path.join(SUBDOMAIN_SCAN_DATA, sub_dir, "results", "pshtt.csv")

  # Now, analytics measurement.
  if os.path.exists(os.path.join(INPUT_SCAN_DATA, "analytics.csv")):
    headers = []
    with open(source_csv, newline='') as csvfile:
      for row in csv.reader(csvfile):
        if (row[0].lower() == "domain"):
          headers = row
          continue

        subdomain = row[0].lower()
        domain = row[1].lower()
        if not domains.get(domain):
          print("[%s][%s] Skipping, not a subdomain of a tracked domain." % (source, subdomain))
          continue

        # If it didn't appear in the pshtt data, skip it, we need this.
        if domains[domain]['branch'] != 'executive':
          print("[%s][%s] Skipping, not displaying data on subdomains of legislative or judicial domains." % (source, subdomain))
          continue

        dict_row = {}
        for i, cell in enumerate(row):
          dict_row[headers[i]] = cell

        # Optimization: only bother storing in memory if Live is True.
        if boolean_for(dict_row['Live']):

          # Initialize subdomains obj if this is its first one.
          if scan_data[domain].get('subdomains') is None:
            scan_data[domain]['subdomains'] = {}

          if scan_data[domain]['subdomains'].get(source) is None:
            scan_data[domain]['subdomains'][source] = []

          # Store as an array, no need to reference by name.
          scan_data[domain]['subdomains'][source].append(dict_row)

  return scan_data

# Given the domain data loaded in from CSVs, draw conclusions,
# and filter/transform data into form needed for display.
def process_domains(domains, agencies, scan_data):

  reports = {
    'analytics': {},
    'https': {},
    'a11y': {},
    'cust_sat': {}
  }

  # Used to generate per-agency rolled-up subdomain downloads.
  subdomain_reports = {
    'https': {}
  }

  # For each domain, determine eligibility and, if eligible,
  # use the scan data to draw conclusions.
  for domain_name in domains.keys():

    if eligible_for_https(domains[domain_name]):
      reports['https'][domain_name] = https_report_for(
        domain_name, domains[domain_name], scan_data, subdomain_reports
      )

  return reports, subdomain_reports

# Go through each report type and add agency totals for each type.
def update_agency_totals():
  all_agencies = Agency.all()

  # For each agency, update their report counts for every domain they have.
  for agency in all_agencies:

    # TODO: Do direct DB queries for answers, rather than iterating.

    # Analytics
    if False:
      eligible = Domain.eligible_for_agency(agency['slug'], 'analytics')

      agency_report = {
        'eligible': len(eligible),
        'participating': 0
      }

      for domain in eligible:
        report = domain['analytics']
        if report['participating'] == True:
          agency_report['participating'] += 1

      print("[%s][%s] Adding report." % (agency['slug'], 'analytics'))
      Agency.add_report(agency['slug'], 'analytics', agency_report)


    # HTTPS
    eligible = Domain.eligible_for_agency(agency['slug'], 'https')
    eligible_https = list(map(lambda w: w['https'], eligible))
    agency_report = total_https_report(eligible_https)
    # agency_report['subdomains'] = total_https_subdomain_report(eligible)

    print("[%s][%s] Adding report." % (agency['slug'], 'https'))
    Agency.add_report(agency['slug'], 'https', agency_report)


# TODO: A domain can also be eligible if it has eligible subdomains.
#       Has display ramifications.
def eligible_for_https(domain):
  return (domain["live"] == True)

# Given a pshtt report, fill in a dict with the conclusions.
def https_behavior_for(pshtt):
  report = {}

  # assumes that HTTPS would be technically present, with or without issues
  if (pshtt["Downgrades HTTPS"] == "True"):
    https = 0 # No
  else:
    if (pshtt["Valid HTTPS"] == "True"):
      https = 2 # Yes
    elif (
      (pshtt["HTTPS Bad Chain"] == "True") and
      (pshtt["HTTPS Bad Hostname"] == "False")
    ):
      https = 1 # Yes
    else:
      https = -1 # No

  report['uses'] = https


  ###
  # Is HTTPS enforced?

  if (https <= 0):
    behavior = 0 # N/A

  else:

    # "Yes (Strict)" means HTTP immediately redirects to HTTPS,
    # *and* that HTTP eventually redirects to HTTPS.
    #
    # Since a pure redirector domain can't "default" to HTTPS
    # for itself, we'll say it "Enforces HTTPS" if it immediately
    # redirects to an HTTPS URL.
    if (
      (pshtt["Strictly Forces HTTPS"] == "True") and
      (
        (pshtt["Defaults to HTTPS"] == "True") or
        (pshtt["Redirect"] == "True")
      )
    ):
      behavior = 3 # Yes (Strict)

    # "Yes" means HTTP eventually redirects to HTTPS.
    elif (
      (pshtt["Strictly Forces HTTPS"] == "False") and
      (pshtt["Defaults to HTTPS"] == "True")
    ):
      behavior = 2 # Yes

    # Either both are False, or just 'Strict Force' is True,
    # which doesn't matter on its own.
    # A "present" is better than a downgrade.
    else:
      behavior = 1 # Present (considered 'No')

  report['enforces'] = behavior


  ###
  # Characterize the presence and completeness of HSTS.

  if pshtt["HSTS Max Age"]:
    hsts_age = int(pshtt["HSTS Max Age"])
  else:
    hsts_age = None

  # Without HTTPS there can be no HSTS.
  if (https <= 0):
    hsts = -1  # N/A (considered 'No')
  else:

    # HSTS is present for the canonical endpoint.
    if (pshtt["HSTS"] == "True") and hsts_age:

      # Say No for too-short max-age's, and note in the extended details.
      if hsts_age >= 31536000:
        hsts = 2  # Yes
      else:
        hsts = 1  # No

    else:
      hsts = 0  # No

  # Separate preload status from HSTS status:
  #
  # * Domains can be preloaded through manual overrides.
  # * Confusing to mix an endpoint-level decision with a domain-level decision.
  if pshtt["HSTS Preloaded"] == "True":
    preloaded = 2  # Yes
  elif (pshtt["HSTS Preload Ready"] == "True"):
    preloaded = 1  # Ready for submission
  else:
    preloaded = 0  # No

  report['hsts'] = hsts
  report['hsts_age'] = hsts_age
  report['preloaded'] = preloaded

  return report

# 'eligible' should be a list of dicts with https report data.
def total_https_report(eligible):
  total_report = {
    'eligible': len(eligible),
    'uses': 0,
    'enforces': 0,
    'hsts': 0,
    'grade': 0
  }

  for report in eligible:

    # Needs to be enabled, with issues is allowed
    if report['uses'] >= 1:
      total_report['uses'] += 1

    # Needs to be Default or Strict to be 'Yes'
    if report['enforces'] >= 2:
      total_report['enforces'] += 1

    # Needs to be present with >= 1 year max-age for canonical endpoint
    if report['hsts'] >= 2:
      total_report['hsts'] += 1

    # Needs to be A- or above
    if (report.get('grade') is not None) and (report['grade'] >= 4):
      total_report['grade'] += 1

  return total_report

# Total up the number of eligible subdomains.
# Ignore preloaded domains.
def total_https_subdomain_report(eligible):
  total_report = {
    'eligible': 0,
    'uses': 0,
    'enforces': 0,
    'hsts': 0
  }

  for domain in eligible:
    if domain['https']['preloaded'] == 2:
      print("[%s] Skipping subdomain calculation, preloaded." % domain['domain'])
      continue

    subdomains = domain['https'].get('subdomains')
    if subdomains:
      for source in SUBDOMAIN_SOURCES:
        source_data = subdomains.get(source)
        if source_data:
          total_report['eligible'] += source_data['eligible']
          total_report['uses'] += source_data['uses']
          total_report['enforces'] += source_data['enforces']
          total_report['hsts'] += source_data['hsts']

  return total_report


# HTTPS conclusions for a domain based on pshtt/tls domain-scan data.
# Modified subdomain_reports in place.
def https_report_for(domain_name, domain, scan_data, subdomain_reports):
  pshtt = scan_data[domain_name]['pshtt']

  # Initialize to the value of the pshtt report.
  # (Moved to own method to make it reusable for subdomains.)
  report = https_behavior_for(pshtt)

  ###
  # Include the SSL Labs grade for a domain.

  # We may not have gotten any scan data from SSL Labs - it happens.
  tls = scan_data[domain_name].get('tls', None)

  fs = None
  sig = None
  ssl3 = None
  tls12 = None
  rc4 = None

  # Not relevant if no HTTPS
  if (report['uses'] <= 0):
    grade = -1 # N/A

  elif tls is None or tls.get('Grade', None) is None:
    # print("[https][%s] No TLS grade found." % domain)
    grade = -1 # N/A

  else:

    grade = {
      "F": 0,
      "T": 1,
      "C": 2,
      "B": 3,
      "A-": 4,
      "A": 5,
      "A+": 6
    }[tls["Grade"]]

    ###
    # Construct a sentence about the domain's TLS config.
    #
    # Consider SHA-1, FS, SSLv3, and TLSv1.2 data.

    fs = int(tls["Forward Secrecy"])
    sig = tls["Signature Algorithm"]
    rc4 = boolean_for(tls["RC4"])
    ssl3 = boolean_for(tls["SSLv3"])
    tls12 = boolean_for(tls["TLSv1.2"])

  report['grade'] = grade

  report['fs'] = fs
  report['sig'] = sig
  report['rc4'] = rc4
  report['ssl3'] = ssl3
  report['tls12'] = tls12

  # Initialize subdomain report gatherer if needed.
  agency = domain['agency_slug']
  if subdomain_reports['https'].get(agency) is None:
    subdomain_reports['https'][agency] = []

  # Now load the pshtt data from subdomains, for each source.
  if scan_data[domain_name].get('subdomains'):
    report['subdomains'] = {}
    for source in scan_data[domain_name]['subdomains']:
      print("[%s][%s] Aggregating subdomain data." % (domain_name, source))

      subdomains = scan_data[domain_name]['subdomains'][source]
      eligible = []

      for subdomain in subdomains:
        behavior = https_behavior_for(subdomain)
        eligible.append(behavior)

        # Store the subdomain CSV fields referenced in app/data.py.
        subdomain_reports['https'][agency].append({
          'domain': subdomain['Domain'],
          'base': subdomain['Base Domain'],
          'agency_name': domain['agency_name'],
          'source': source,
          'https': behavior
        })

      subtotals = total_https_report(eligible)
      del subtotals['grade']  # not measured for subdomains
      report['subdomains'][source] = subtotals

  return report


# Create a Report about each tracked stat.
def latest_reports():
  reports = []

  for domain_type in DOMAIN_TYPES:
    https_domains = Domain.eligible_for_type(domain_type, 'https')

    total = len(https_domains)
    uses = 0
    enforces = 0
    hsts = 0
    for domain in https_domains:
      report = domain['https']
      # HTTPS needs to be enabled.
      # It's okay if it has a bad chain.
      # However, it's not okay if HTTPS is downgraded.
      if (
        (report['uses'] >= 1) and
        (report['enforces'] >= 1)
      ):
        uses += 1

      # Needs to be Default or Strict to be 'Yes'
      if report['enforces'] >= 2:
        enforces += 1

      # Needs to be present with >= 1 year max-age on canonical endpoint
      if report['hsts'] >= 2:
        hsts += 1

      https_report = 'https-' + domain_type
      reports.append({
        https_report: {
          'eligible': total,
          'uses': uses,
          'enforces': enforces,
          'hsts': hsts
        }
      })

  return reports

# Hacky helper - print out the %'s after the command finishes.
def print_report():
  print()

  report = Report.latest()
  for report_type in report.keys():
    # The a11y report has a very different use than the others
    if report_type == "report_date" or report_type == "a11y":
      continue

    print("[%s]" % report_type)
    eligible = report[report_type]["eligible"]
    for key in report[report_type].keys():
      if key == "eligible":
        continue
      print("%s: %i" % (key, percent(report[report_type][key], eligible)))
    print()

# Convenience: save CSV reports of subdomains per-agency.
def save_subdomain_reports(subdomain_reports):
  # Only works for HTTPS right now.
  for agency in subdomain_reports['https']:
    print("[https][csv][%s] Saving CSV of agency subdomains." % agency)
    output = Domain.subdomains_to_csv(subdomain_reports['https'][agency])
    output_path = os.path.join(SUBDOMAIN_AGENCY_OUTPUT, agency, "https.csv")
    write(output, output_path)


### utilities

def shell_out(command, env=None):
    try:
        print("[cmd] %s" % str.join(" ", command))
        response = subprocess.check_output(command, shell=False, env=env)
        output = str(response, encoding='UTF-8')
        print(output)
        return output
    except subprocess.CalledProcessError:
        logging.warn("Error running %s." % (str(command)))
        exit(1)
        return None

def percent(num, denom):
  if denom == 0:
    return 0
  return round((num / denom) * 100)

# mkdir -p in python, from:
# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def write(content, destination, binary=False):
    mkdir_p(os.path.dirname(destination))

    if binary:
        f = open(destination, 'bw')
    else:
        f = open(destination, 'w', encoding='utf-8')
    f.write(content)
    f.close()


def boolean_for(string):
  if string == "False":
    return False
  else:
    return True

def branch_for(agency):
  if agency in [
    "Library of Congress",
    "The Legislative Branch (Congress)",
    "Government Printing Office",
    "Government Publishing Office",
    "Congressional Office of Compliance",
    "Stennis Center for Public Service",
    "U.S. Capitol Police",
    "Architect of the Capitol"
  ]:
    return "legislative"

  if agency in [
    "The Judicial Branch (Courts)",
    "The Supreme Court",
    "U.S Courts"
  ]:
    return "judicial"

  if agency in ["Non-Federal Agency"]:
    return "non-federal"

  else:
    return "executive"

def nice_domain_type_for(domain_type):
  if domain_type == 'City':
    return 'city'
  else:
    return 'federal'

def strip_www(domain):
    return domain.replace('www.', '')

### Run when executed.

if __name__ == '__main__':
    run(None)
