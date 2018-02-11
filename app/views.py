
from flask import render_template, Response, redirect, url_for
from app import models
from app.data import FIELD_MAPPING
import os
import ujson

def register(app):

  @app.route("/data/")
  def data():
      return render_template("data.html")

  @app.route("/")
  def index():
      return render_template("index.html")

  @app.route("/about/")
  def about():
      return render_template("about.html")

  ##
  # Data endpoints.

  # High-level %'s, used to power the donuts.
  @app.route("/data/reports/<report_name>.json")
  def report(report_name):
      if '-' in report_name:
        report_name, domain_type = report_name.split('-')
        report = models.Report.latest_for_type(domain_type).get(report_name, {})
      else:
        report = models.Report.latest().get(report_name, {})
      response = Response(ujson.dumps(report))
      response.headers['Content-Type'] = 'application/json'
      return response

    # Detailed data per-parent-domain.
  @app.route("/data/domains/<report_name>.<ext>")
  def domain_report(report_name, ext):
      if '-' in report_name:
          report_name, domain_type = report_name.split('-')
          domains = models.Domain.eligible_parents_for_type(domain_type, report_name)
      else:
          domains = models.Domain.eligible_parents(report_name)
          domains = sorted(domains, key=lambda k: k['domain'])

      if ext == "json":
          response = Response(ujson.dumps({'data': domains}))
          response.headers['Content-Type'] = 'application/json'
      elif ext == "csv":
          response = Response(models.Domain.to_csv(domains, report_name))
          response.headers['Content-Type'] = 'text/csv'
      return response

  # Detailed data per-host for a given report.
  @app.route("/data/hosts/<report_name>.<ext>")
  def hostname_report(report_name, ext):
      domains = models.Domain.eligible(report_name)

      # sort by base domain, but subdomain within them
      domains = sorted(domains, key=lambda k: k['domain'])
      domains = sorted(domains, key=lambda k: k['base_domain'])

      if ext == "json":
          response = Response(ujson.dumps({'data': domains}))
          response.headers['Content-Type'] = 'application/json'
      elif ext == "csv":
          response = Response(models.Domain.to_csv(domains, report_name))
          response.headers['Content-Type'] = 'text/csv'
      return response

  # Detailed data for all subdomains of a given parent domain, for a given report.
  @app.route("/data/hosts/<domain>/<report_name>.<ext>")
  def hostname_report_for_domain(domain, report_name, ext):
    domains = models.Domain.eligible_for_domain(domain, report_name)

    # sort by hostname, but put the parent at the top if it exist
    domains = sorted(domains, key=lambda k: k['domain'])
    domains = sorted(domains, key=lambda k: k['is_parent'], reverse=True)

    if ext == "json":
        response = Response(ujson.dumps({'data': domains}))
        response.headers['Content-Type'] = 'application/json'
    elif ext == "csv":
        response = Response(models.Domain.to_csv(domains, report_name))
        response.headers['Content-Type'] = 'text/csv'
    return response

  @app.route("/data/agencies/<report_name>.json")
  def agency_report(report_name):
      if '-' in report_name:
          report_name, domain_type = report_name.split('-')
          domains = models.Agency.eligible_for_type(domain_type, report_name)
      else:
          domains = models.Agency.eligible(report_name)
      response = Response(ujson.dumps({'data': domains}))
      response.headers['Content-Type'] = 'application/json'
      return response

  @app.route("/https/<domain_type>/domains/")
  def https_domains(domain_type):
      report_name = report_name_for(domain_type)
      return render_template("https/domains.html", domain_type=domain_type, report_name=report_name)

  @app.route("/https/<domain_type>/agencies/")
  def https_agencies(domain_type):
      report_name = report_name_for(domain_type)
      return render_template("https/agencies.html", domain_type=domain_type, report_name=report_name)

  @app.route("/https/<domain_type>/info/")
  def https_guide(domain_type):
      report_name = report_name_for(domain_type)
      return render_template("https/guide.html", domain_type=domain_type, report_name=report_name)

  @app.route("/https/domains/")
  def legacy_https_domains():
      report_name = report_name_for('federal')
      return render_template("https/domains.html", domain_type='federal', report_name=report_name)

  @app.route("/https/agencies/")
  def legacy_https_agencies():
      report_name = report_name_for('federal')
      return render_template("https/agencies.html", domain_type='federal', report_name=report_name)

  @app.route("/https/info/")
  def legacy_https_guide():
      report_name = report_name_for('federal')
      return render_template("https/guide.html", domain_type='federal', report_name=report_name)

  @app.route("/agency/<slug>")
  def agency(slug=None):
      agency = models.Agency.find(slug)
      if agency is None:
          pass # TODO: 404

      return render_template("agency.html", agency=agency)

  @app.route("/domain/<hostname>")
  def domain(hostname=None):
      domain = models.Domain.find(hostname)
      if domain is None:
          pass # TODO: 404

      return render_template("domain.html", domain=domain)

  # Sanity-check RSS feed, shows the latest report.
  @app.route("/data/reports/feed/")
  def report_feed():
      report_federal = models.Report.latest_for_type("federal").get('https', {})
      report_city = models.Report.latest_for_type("city").get('https', {})
      response = Response(render_template("feed.xml", report_federal=report_federal, report_city=report_city))
      response.headers['Content-Type'] = 'application/rss+xml'
      return response


  @app.errorhandler(404)
  def page_not_found(e):
      return render_template('404.html'), 404

def report_name_for(domain_type):
    return 'https-' + domain_type

