$(document).ready(function () {

  var report_url = $('script[data-domain-report-url]').attr('data-domain-report-url');
  $.get(report_url, function(data) {
    renderTable(data.data);
  });

  /**
  * I don't like this at all, but to keep the presentation synced
  * between the front-end table, and the CSV we generate, this is
  * getting replicated to the /data/update script in this repository,
  * and needs to be manually synced.
  *
  * The refactor that takes away from DataTables should also prioritize
  * a cleaner way to DRY (don't repeat yourself) this mess up.
  */

  var names = {
    uses: {
      "-1": "Nei",
      0: "Nei",
      1: "Ja", // (with certificate chain issues)
      2: "Ja"
    },

    enforces: {
      0: "", // N/A (no HTTPS)
      1: "Nei", // Present, not default
      2: "Ja", // Defaults eventually to HTTPS
      3: "Ja" // Defaults eventually + redirects immediately
    },

    hsts: {
      "-1": "", // N/A
      0: "Nei",  // No
      1: "Nei", // No, HSTS with short max-age (for canonical endpoint)
      2: "Ja" // Yes, HSTS for >= 1 year (for canonical endpoint)
    },

    preloaded: {
      0: "",  // No (don't display, since it's optional)
      1: "Forberedt",  // Preload-ready
      2: "Ja"  // Yes
    },

    grade: {
      "-1": "",
      0: "F",
      1: "T",
      2: "C",
      3: "B",
      4: "A-",
      5: "A",
      6: "A+"
    }
  };

  var display = function(set) {
    return function(data, type, row) {
      if (type == "sort")
        return data.toString();
      else
        return set[data.toString()];
    }
  };

  // Describe what's going on with this domain's subdomains.
  var subdomains = function(data, type, row) {
    if (type == "sort") return null;

    // If the domain is preloaded, responsibilities are absolved.
    if (row.https.preloaded == 2)
      return "Alle subdomener blir automatisk beskyttet ved hjelp av hardkoding (preloading).";

    if (row.https.preloaded == 1)
      return "Alle subdomener vil bli automatisk beskyttet når hardkodingen er ferdig (preloading).";

    if (!row.https.subdomains) {
      return "";
      if (row.https.uses >= 1)
        return "Ingen kjente subdomener funnet. " + l("preload", "vurder hardkoding (preloading).");
      else
        return "Ingen kjente subdomener funnet.";
    }

    var sources = [],
        message = "",
        pct = null;

    // TODO: make this a function.
    if (row.https.subdomains.censys) {
      pct = Utils.percent(row.https.subdomains.censys.enforces, row.https.subdomains.censys.eligible);
      message = n("" + pct + "%") + " of " +
        row.https.subdomains.censys.eligible + " offentlige domener "
        + l(censysUrlFor(row.domain), "kjent for Censys") +
        " alt på HTTPS.";
      sources.push(message);
    }

    if (row.https.subdomains.dap) {
      pct = Utils.percent(row.https.subdomains.dap.enforces, row.https.subdomains.dap.eligible);
      sources.push(n("" + pct + "%") + " of " +
        row.https.subdomains.dap.eligible + " public sites " +
        l(links.dap_data, "known to the Digital Analytics Program") +
        " enforce HTTPS.")
    }

    if (sources.length == 0)
      return "";

    sources.push("For more details, " + l(links.subdomains, "read our methodology") +
      ", or " + l(agencyDownloadFor(row), "download subdomain data for this agency") + ".");

    var p = "<p class=\"indents\">";
    return n("Known public subdomains: ") + p + sources.join("</p>" + p) + "</p>";
  };

  var linkGrade = function(data, type, row) {
    var grade = display(names.grade)(data, type);
    if (type == "sort")
      return grade;
    else if (grade == "")
      return ""
    else
      return "" +
        "<a href=\"" + labsUrlFor(row.canonical) + "\" target=\"blank\">" +
          grade +
        "</a>";
  };

  var labsUrlFor = function(domain) {
    return "https://www.ssllabs.com/ssltest/analyze.html?d=" + domain;
  };

  var censysUrlFor = function(domain) {
    return "https://censys.io/certificates?q=" +
      "parsed.subject.common_name:%22" + domain +
      "%22%20or%20parsed.extensions.subject_alt_name.dns_names:%22" + domain + "%22";
  };

  var agencyDownloadFor = function(row) {
    return "https://s3-us-gov-west-1.amazonaws.com/cg-4adefb86-dadb-4ecf-be3e-f1c7b4f6d084/live/subdomains/agencies/" + row["agency_slug"] + "/https.csv";
  };

  // Construct a sentence explaining the HTTP situation.
  var httpDetails = function(data, type, row) {

    if (type == "sort")
      return null;

    var https = row.https.uses;
    var behavior = row.https.enforces;
    var hsts = row.https.hsts;
    var hsts_age = row.https.hsts_age;
    var preloaded = row.https.preloaded;
    var grade = row.https.grade;

    var tls = [];

    // If an SSL Labs grade exists at all...
    if (row.https.grade >= 0) {

      if (row.https.sig == "SHA1withRSA")
        tls.push("Certificate uses a " + l("sha1", "weak SHA-1 signature"));

      if (row.https.ssl3 == true)
        tls.push("Supports the " + l("ssl3", "insecure SSLv3 protocol"));

      if (row.https.tls12 == false)
        tls.push("Lacks support for the " + l("tls12", "most recent version of TLS"));
    }

    // Though not found through SSL Labs, this is a TLS issue.
    if (https == 1)
      tls.push("Certificate chain not valid for all public clients. See " + l(labsUrlFor(row.canonical), "SSL Labs") + " for details.");

    // Non-urgent TLS details.
    var tlsDetails = "";
    if (grade >= 0) {
      if (tls.length > 0)
        tlsDetails += tls.join(". ") + ".";
      else if (grade < 6)
        tlsDetails += l(labsUrlFor(row.canonical), "Review SSL Labs report") + " to resolve TLS quality issues.";
    }

    // Principles of message crafting:
    //
    // * Only grant "perfect score!" if TLS quality issues are gone.
    // * Don't show TLS quality issues when pushing to preload.
    // * All flagged TLS quality issues should be reflected in the
    //   SSL Labs grade, so that agencies have fair warning of issues
    //   even before we show them.
    // * Don't speak explicitly about M-15-13, since not all domains
    //   are subject to OMB requirements.

    var details;
    // By default, if it's an F grade, *always* give TLS details.
    var urgent = (grade == 0);

    // CASE: Perfect score!
    // HSTS max-age is allowed to be weak, because client enforcement means that
    // the max-age is effectively overridden in modern browsers.
    if (
        (https >= 1) && (behavior >= 2) &&
        (hsts >= 1) && (preloaded == 2) &&
        (tls.length == 0) && (grade == 6))
      details = g("Perfekt! HTTPS is strictly enforced throughout the zone.");

    // CASE: Only issue is TLS quality issues.
    else if (
        (https >= 1) && (behavior >= 2) &&
        (hsts == 2) && (preloaded == 2)) {
      details = g("Nesten perfekt!") + " " + tlsDetails;
    }

    // CASE: HSTS preloaded, but HSTS header is missing.
    else if (
        (https >= 1) && (behavior >= 2) &&
        (hsts < 1) && (preloaded == 2))
      details = w("Advarsel:") + " Domenet er hardkodet inn i nettlesere (preload), men mangler HSTS-header. Dette kan " + l("stay_preloaded", "føre til at domenet fjernes fra preload-lister") + ".";

    // CASE: HTTPS+HSTS, preload-ready but not preloaded.
    else if (
        (https >= 1) && (behavior >= 2) &&
        (hsts == 2) && (preloaded == 1))
      details = g("Nesten perfekt!") + " Domenet er klart for å bli " + l("submit", "sendt inn for hardkoding i nettlesere (HSTS preload)") + ".";

    // CASE: HTTPS+HSTS (M-15-13 compliant), but no preloading.
    else if (
        (https >= 1) && (behavior >= 2) &&
        (hsts == 2) && (preloaded == 0))
      details = g("Alt på HTTPS.") + " For enda bedre sikkerhet, vurder å " + l("preload", "hardkode dette domenet inn i nettlesere (HSTS preload)") + ".";

    // CASE: HSTS, but HTTPS not enforced.
    else if ((https >= 1) && (behavior < 2) && (hsts == 2))
      details = n("Advarsel:") + " Domenet bruker " + l("hsts", "HSTS") + ", men sender selv ikke videre all trafikk til HTTPS.";

    // CASE: HTTPS w/valid chain supported and enforced, weak/no HSTS.
    else if ((https == 2) && (behavior >= 2) && (hsts < 2)) {
      if (hsts == 0)
        details = g("Nesten:") + " skru på" + l("hsts", "HSTS") + " slik at nettlesere selv kan holde seg på HTTPS.";
      else if (hsts == 1)
        details = n("Nesten:") + " Maksimumverdien for " + l("hsts", "HSTS") + " på (" + hsts_age + " sekunder) er for kort, og burde økes til minst 1 år (31536000 sekunder).";
    }

    // CASE: HTTPS w/invalid chain supported and enforced, no HSTS.
    else if ((https == 1) && (behavior >= 2) && (hsts < 2))
      details = n("Advarsel:") + " Domenet mangler " + l("hsts", "HSTS") + ", men den leverte sertifikatkjeden er muligens ikke gyldig og fungerer derfor kanskje ikke for alle klienter. HSTS hindrer at brukere klikker seg forbi advarsler. Se på " + l(labsUrlFor(row.canonical), "SSL Labs-rapporten") + " for flere detaljer.";

    // CASE: HTTPS supported, not enforced, no HSTS.
    else if ((https >= 1) && (behavior < 2) && (hsts < 2))
      details = n("Advarsel:") + " Dette domenet støtter HTTPS, men " + w("men har det ikke som standard for all trafikk") + ".";

    // CASE: HTTPS downgrades.
    else if (https == 0)
      details = w("Usikker:") + " Dette domenet videresender besøkende fra HTTPS til usikre HTTP."

    // CASE: HTTPS isn't supported at all.
    else if (https == -1)
      // TODO SUBCASE: It's a "redirect domain".
      // SUBCASE: Everything else.
      details = "Dette domenet støtter " + w("ikke HTTPS") + "."

    else
      details = "";

    // If there's an F grade, and TLS details weren't already included,
    // add an urgent warning.
    if (urgent)
      return details + " " + w("Warning: ") + l(labsUrlFor(row.canonical), "review SSL Labs report") + " to resolve TLS quality issues."
    else
      return details;
  };

  var links = {
    dap: "https://analytics.usa.gov",
    dap_data: "https://analytics.usa.gov/data/live/sites.csv",
    censys: "https://censys.io",
    hsts: "https://https.cio.gov/hsts/",
    sha1: "https://https.cio.gov/technical-guidelines/#signature-algorithms",
    ssl3: "https://https.cio.gov/technical-guidelines/#ssl-and-tls",
    tls12: "https://https.cio.gov/technical-guidelines/#ssl-and-tls",
    preload: "https://https.cio.gov/hsts/#hsts-preloading",
    subdomains: "/https/guidance/#subdomains",
    preloading_compliance: "https://https.cio.gov/guide/#options-for-hsts-compliance",
    stay_preloaded: "https://hstspreload.appspot.com/#continued-requirements",
    submit: "https://hstspreload.appspot.com"
  };

  var l = function(slug, text) {
    return "<a href=\"" + (links[slug] || slug) + "\" target=\"blank\">" + text + "</a>";
  };

  var g = function(text) {
    return "<strong class=\"success\">" + text + "</strong>";
  };

  var w = function(text) {
    return "<strong class=\"warning\">" + text + "</strong>";
  };

  var n = function(text) {
    return "<strong class=\"neutral\">" + text + "</strong>";
  }

  var renderTable = function(data) {
    var csv_url = $('script[data-domain-report-csv-url]').attr('data-domain-report-csv-url');
    var table = $("table").DataTable({

      data: data,

      responsive: {
          details: {
              type: "",
              display: $.fn.dataTable.Responsive.display.childRowImmediate
          }
      },

      initComplete: Utils.searchLinks,

      columns: [
        {
          data: "domain",
          width: "210px",
          cellType: "th",
          render: Utils.linkDomain
        },
        {data: "canonical"},
        {data: "agency_name"},
        {
          data: "https.uses",
          render: display(names.uses)
        },
        {
          data: "https.enforces",
          render: display(names.enforces)
        },
        {
          data: "https.hsts",
          render: display(names.hsts)
        },
        {
          data: "https.preloaded",
          render: display(names.preloaded)
        },
        /*
        {
          data: "https.grade",
          render: linkGrade
        },*/
        {
          data: "",
          render: httpDetails
        },
        {
          data: "",
          render: subdomains
        }
        /*
        {
          data: "TLS Issues",
          title: "TLS-Probleme",
          render: tlsDetails
        }*/
      ],

      columnDefs: [
        {
          targets: 0,
          cellType: "td",
          createdCell: function (td) {
            td.scope = "row";
          }
        }
      ],

      pageLength: 25,

      language: {
        search: "Søk:",
        lengthMenu: "Vis _MENU_ oppføringer",
        emptyTable: "Ingen data tilgjengelig",
        info: "Vis _START_ - _END_ av _TOTAL_ oppføringer",
        infoEmpty: "Vis 0 - 0 av 0 oppføringer",
        infoFiltered: "(av samlede _MAX_ oppføringer)",
        paginate: {
          previous: "<<",
          next: ">>"
        }
      },

      csv: csv_url,

      dom: 'LCftrip'

    });

  }

})
