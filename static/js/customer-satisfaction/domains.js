$(document).ready(function () {

  $.get("/static/data/tables/customer-satisfaction/domains.json", function(data) {
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
    custsat: {
      false: "No",
      true: "Yes"
    }
  };



  var display = function(set) {
    return function(data, type) {
      if (type == "sort")
        return set[data];
      else
        return set[data];
    }
  };

  var renderTable = function(data) {
    var table = $("table").DataTable({

      responsive: true,

      data: data,

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
          data: "participating",
          render: display(names.custsat)
        },
        {
          data:"service-list",
          render: Utils.custSatList
        }
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

      "oLanguage": {
        "oPaginate": {
          "sPrevious": "<<",
          "sNext": ">>"
        }
      },

      csv: "/data/domains/customer-satisfaction.csv",

      dom: 'LCftrip'

    });

    $('table tbody').on('click', 'td:not(.sorting_1)', function(e) {
      $(this).siblings("th.sorting_1").click();
    });

    Utils.detailsKeyboardCtrl();
    Utils.updatePagination();
    table.on("draw.dt",function(){
       Utils.detailsKeyboardCtrl();
       Utils.updatePagination();
    });
  };

});
