const myLinker = (function() {

  let linkerResultsManager = {
      init: function (data) {

      const defaultDataTablesSettings = {
        "dom": "prt",
        "pageLength": 10,
        // "scrollY": "400px",
        // "scrollCollapse": true,
        "searching": true,
        // see https://datatables.net/plug-ins/dataRender/ellipsis
        "columnDefs": [ {
          targets: 1,
          render: $.fn.dataTable.render.ellipsis(50, false)
        } ]
      };

      const tables = [ // the ordering in this list is important! do not change it.

        {
          "tableName": "transcripts_table",
          "tableData": data.transcripts,
          "options": {
            "visible": true,
            "pk": "transcript_pk"
          },
          "relationship": {"with": "transcript_proteins", "using": "transcript_pk"}
        },

        {
          "tableName": "transcript_proteins",
          "tableData": data.transcript_proteins,
          "options": {
            "visible": false
          },
          "relationship": {"with": "proteins_table", "using": "protein_pk"}
        },

        {
          "tableName": "proteins_table",
          "tableData": data.proteins,
          "options": {
            "visible": true,
            "pk": "protein_pk"
          },
          "relationship": {"with": "protein_reactions", "using": "protein_pk"}
        },

        {
          "tableName": "protein_reactions",
          "tableData": data.protein_reactions,
          "options": {
            "visible": false
          },
          "relationship": {"with": "reactions_table", "using": "reaction_pk"}
        },

        {
          "tableName": "reactions_table",
          "tableData": data.reactions,
          "options": {
            "visible": true,
            "pk": "reaction_pk"
          },
          "relationship": [
              {"with": "compound_reactions", "using": "reaction_pk"},
              {"with": "reaction_pathways", "using": "reaction_pk"}
          ]
        },

        {
          "tableName": "compounds_table",
          "tableData": data.compounds,
          "options": {
            "visible": true,
            "pk": "compound_pk"
          }
        },

        {
          "tableName": "compound_reactions",
          "tableData": data.compound_reactions,
          "options": {
            "visible": false
          },
          "relationship": {"with": "compounds_table", "using": "compound_pk"}
        },

        {
          "tableName": "reaction_pathways",
          "tableData": data.reaction_pathways,
          "options": {
            "visible": false
          },
          "relationship": {"with": "pathways_table", "using": "pathway_pk"}
        },

        {
          "tableName": "pathways_table",
          "tableData": data.pathways,
          "options": {
            "visible": true,
            "pk": "pathway_pk"
          }
        }

      ];

      // https://stackoverflow.com/questions/24383805/datatables-change-number-of-pagination-buttons
      // $.fn.DataTable.ext.pager.numbers_length = 3;

      FiRDI.init(tables, defaultDataTablesSettings);

      // Hide certain columns
      const columnsToHidePerTable = [
        {"tableName": "transcripts_table", "columnNames": ["transcript_pk"]},
        {"tableName": "proteins_table", "columnNames": ["protein_pk"]},
        {"tableName": "compounds_table", "columnNames": ["compound_pk"]},
        {"tableName": "reactions_table", "columnNames": ["reaction_pk"]},
        {"tableName": "pathways_table", "columnNames": ["pathway_pk"]}
      ];

      columnsToHidePerTable.forEach(function(tableInfo) {
        $('#' + tableInfo['tableName']).DataTable()
          .columns(tableInfo['columnNames'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
          .visible(false);
      });

      // enable global search box
      $('#global_filter').on('keyup click', function () {
          let val = $('#global_filter').val();
          $.fn.dataTable.tables( { api: true } ).search(val).draw();
      });

      }
  }

  return {
    init: linkerResultsManager.init.bind(linkerResultsManager)
  };

})();


$(document).ready(function() {

    let pqr = myLinker.init(data);

});