var Tables = {

  // wraps renderTable around a given $("table")
  // e.g. Tables.init($("table"), data)
  init: function(data, options) {
    // assign data
    if (!options.data) options.data = data;

    // add common options to all renderTables requests
    if (!options.responsive) options.responsive = true;

    var customInit = function() {}; // noop
    if (options.initComplete) customInit = options.initComplete;
    options.initComplete = function() {
      Utils.searchLinks(this);
      customInit(this);
    }

    if (!options.oLanguage) {
      options.oLanguage = {
        "sSearch": "Søk:",
        "sLengthMenu": "Viser _MENU_ oppføringer",
        "sEmptyTable": "Ingen data for visning i denne tabellen",
        "sInfo": "Viser _START_ - _END_ av _TOTAL_ oppføringer",
        "sInfoEmpty": "Viser 0 - 0 av 0 oppføringer",
        "sInfoFiltered": "(av totalt _MAX_ oppføringer)",
        "oPaginate": {
          "sPrevious": "<<",
          "sNext": ">>"
        }
      };
    }

    options.language = {
      search: "Søk:",
      lengthMenu: "Viser _MENU_ oppføringer",
      emptyTable: "Ingen data for visning i denne tabellen",
      info: "Viser _START_ - _END_ av _TOTAL_ oppføringer",
      infoEmpty: "Viser 0 - 0 av 0 oppføringer",
      infoFiltered: "(av totalt _MAX_ oppføringer)",
      paginate: {
        previous: "<<",
        next: ">>"
      }
    };

    // Paginate to 100 per-page by default.
    if (!options.dom) options.dom = 'pCftrip';
    if (!options.pageLength) options.pageLength = 100;

    var table = $("table").DataTable(options);

    // Wire up accessible pagination controls.
    Utils.updatePagination();
    table.on("draw.dt",function(){
      Utils.updatePagination();
    });

    return table;
  },

  // sets some agency-table-specific options
  initAgency: function(data, options) {
    // Don't paginate agency tables by default.
    if (!options.pageLength) options.pageLength = 150;
    if (!options.dom) options.dom = 'Cftri';

    // Order by 2nd column (number of services) by default.
    if (!options.order) options.order = [[1, "desc"]];

    return Tables.init(data, options);
  },

  // common render function for displaying booleans as Yes/No
  boolean: function(data, type) {
    if (type == "sort") return data;
    else return {false: "No", true: "Yes"}[data];
  },

  // common render function for linking domains to canonical URLs
  canonical: function(data, type, row) {
    if (type == "sort") return data;
    else return "<a href=\"" + row.canonical + "\" target=\"blank\">" + data + "</a>";
  },

  // occasionally useful (see https/domains.js for example)
  noop: function() {return ""},

  // common render helper for percent bars
  percentBar: function(data) {
    return '' +
      '<div class="progress-bar-indication">' +
        '<span class="meter width' + data + '" style="width: ' + data + '%">' +
          '<p>' + data + '%</p>' +
        '</span>' +
      '</div>';
  },

  // common pattern for percent bars:
  // given row[report] and row[report][field], will
  // compare against row[report].eligible
  percent: function(report, field, totals) {
    if (!totals) totals = false; // be explicit

    return function(data, type, row) {
      var set = totals ? row.totals : row;
      var numerator = set[report][field];
      var denominator = set[report].eligible;

      // don't divide by 0!
      if (denominator == 0) {
        if (type == "sort") return -1; // shrug?
        else return "&mdash;";
      }

      var percent = Utils.percent(numerator, denominator);
      if (type == "sort") return percent;
      return Tables.percentBar(percent);
    }
  },

  // helpful for reports where parent domains have totals for subdomains
  percentTotals: function(report, field) {
    return Tables.percent(report, field, true);
  },

  // common rendering function for agency service/domain counts
  agencyServices: function(category) {
    return function(data, type, row) {
      if (type == "sort") return data;
      else return "" +
        "<a href=\"/" + category + "/domains/#" +
          QueryString.stringify({q: row.name}) + "\">" +
          data +
        "</a>";
    };
  }

};

$(function() {
  // if a datatable is searched, sync it to the URL hash
  $('table').on('search.dt', function(e, settings) {
    var query = $("input[type=search]").val();
    if (query)
      location.hash = QueryString.stringify({q: query});
    // TODO: Disabled because this callback runs on table init,
    // and zeroes out the location hash. Should be addressed.
    // else
    //   location.hash = '';
  });

  $('table').on('draw.dt', function() {
    // set max width on dataTable
    $(this).css('width', '100%');

    // add label for attribute for search
    $('.dataTables_filter label').attr('for', 'datatables-search');
    $('#DataTables_Table_0_filter').find('input[type="search"]').attr('id', 'datatables-search');
  });
});
