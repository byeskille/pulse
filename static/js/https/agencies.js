$(document).ready(function () {

  var report_url = $('script[data-agency-report-url]').attr('data-agency-report-url');
  $.get(report_url, function(data) {
    renderTable(data.data);
  });

  var percentBar = function(field) {
    return function(data, type, row) {
      if (type == "sort")
        return row.https[field];
      return Utils.progressBar(Utils.percent(
        row.https[field], row.https.eligible
      ));
    };
  }

  var renderTable = function(data) {
    $("table").DataTable({
      responsive: true,
      initComplete: Utils.searchLinks,

      data: data,

      columns: [
        {data: "name"},
        {
          data: "https.eligible",
          render: Utils.filterAgency("https")
        },
        {data: "https.uses"},
        {data: "https.enforces"},
        {data: "https.hsts"},
        //{data: "https.grade"}
      ],

      // order by number of domains
      order: [[1, "desc"]],

      columnDefs: [
        {
          targets: 0,
          cellType: "td",
          createdCell: function (td) {
            td.scope = "row";
          },
          width: "40%"
        },
        {
          targets: 1,
          width: "55px"
        },
        {
          render: percentBar("uses"),
          targets: 2,
        },
        {
          render: percentBar("enforces"),
          targets: 3,
        },
        {
          render: percentBar("hsts"),
          targets: 4,
        },
        /*{
          render: percentBar("grade"),
          targets: 5,
        }*/
      ],

      pageLength: 25,

      "oLanguage": {
        "sSearch": "Søk:",
        "sLengthMenu": "Vis _MENU_ oppføringer",
        "sInfo": "Vis _START_ - _END_ fra _TOTAL_ oppføringer",
        "sInfoFiltered": "(av totalt _MAX_ oppføringer)",
        "oPaginate": {
          "sPrevious": "<<",
          "sNext": ">>"
        }
      },

      dom: 'Lftrip'

    });
  };

});
