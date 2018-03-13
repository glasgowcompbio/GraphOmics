$(document).ready(function() {

  const defaultDataTablesSettings = {
    "dom": "rtp",
    "pageLength": 20,
    // "scrollY": "400px",
    // "scrollCollapse": true,
    "searching": true
  };

  const tables = [ // the ordering in this list is important! do not change it.

    {
      "tableName": "transcripts_table",
      "tableData": transcripts,
      "options": {
        "visible": true,
        "pk": "transcript_pk"
      },
      "relationship": {"with": "transcript_proteins", "using": "transcript_pk"}
    },

    {
      "tableName": "transcript_proteins",
      "tableData": transcript_proteins,
      "options": {
        "visible": false
      },
      "relationship": {"with": "proteins_table", "using": "protein_pk"}
    },

    {
      "tableName": "proteins_table",
      "tableData": proteins,
      "options": {
        "visible": true,
        "pk": "protein_pk"
      },
      "relationship": {"with": "protein_reactions", "using": "protein_pk"}
    },

    {
      "tableName": "protein_reactions",
      "tableData": protein_reactions,
      "options": {
        "visible": false
      },
      "relationship": {"with": "reactions_table", "using": "reaction_pk"}
    },

    {
      "tableName": "reactions_table",
      "tableData": reactions,
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
      "tableData": compounds,
      "options": {
        "visible": true,
        "pk": "compound_pk"
      }
    },

    {
      "tableName": "compound_reactions",
      "tableData": compound_reactions,
      "options": {
        "visible": false
      },
      "relationship": {"with": "compounds_table", "using": "compound_pk"}
    },

    {
      "tableName": "reaction_pathways",
      "tableData": reaction_pathways,
      "options": {
        "visible": false
      },
      "relationship": {"with": "pathways_table", "using": "pathway_pk"}
    },

    {
      "tableName": "pathways_table",
      "tableData": pathways,
      "options": {
        "visible": true,
        "pk": "pathway_pk"
      }
    }

  ];

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

});