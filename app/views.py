
from flask import render_template, Response, redirect, url_for
from app import models
from app.data import FIELD_MAPPING
import ujson

def register(app):

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
      response = Response(ujson.dumps(models.Report.latest().get(report_name, {})))
      response.headers['Content-Type'] = 'application/json'
      return response

  # Detailed data per-domain, used to power the data tables.
  @app.route("/data/domains/<report_name>.<ext>")
  def domain_report(report_name, ext):
      if '-' in report_name:
        report_name, domain_type = report_name.split('-')
        domains = models.Domain.eligible_for_type(domain_type, report_name)
      else:
        domains = models.Domain.eligible(report_name)

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
      return redirect(url_for('https_domains', domain_type='federal'))

  @app.route("/https/agencies/")
  def legacy_https_agencies():
      return redirect(url_for('https_agencies', domain_type='federal'))

  @app.route("/https/info/")
  def legacy_https_guide():
      return redirect(url_for('https_guide', domain_type='federal'))

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
      response = Response(render_template("feed.xml"))
      response.headers['Content-Type'] = 'application/rss+xml'
      return response

  #@app.route("/accessibility/domains/")
  #def accessibility_domains():
  #  return render_template("accessibility/domains.html")

  #@app.route("/accessibility/agencies/")
  #def accessibility_agencies():
  #  return render_template("accessibility/agencies.html")

  #@app.route("/accessibility/guidance/")
  #def accessibility_guide():
  #  return render_template("accessibility/guide.html")

def report_name_for(domain_type):
    return 'https-' + domain_type
