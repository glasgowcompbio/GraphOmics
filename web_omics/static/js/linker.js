import FiRDI from './firdi.js';
import InfoPanesManager from './info_panes_manager';

// https://stackoverflow.com/questions/1199352/smart-way-to-shorten-long-strings-with-javascript
String.prototype.trunc = String.prototype.trunc ||
      function(n){
          return (this.length > n) ? this.substr(0, n-1) + '&hellip;' : this;
      };

const defaultDataTablesSettings = {
    // "dom": "Brftip",
    "dom": "Brtip",
    "pageLength": 10,
    // "scrollY": "800px",
    // "scrollCollapse": true,
    "pagingType": "simple",
    "searching": true,
    "select": true,
    "columnDefs": [{
        targets: 2,
        createdCell: function(td, cellData, rowData, row, col) {
            if (rowData.obs === '-' || rowData.obs === null) {
                // do nothing
            } else if (rowData['significant_' + $('input[type=radio][name=inlineRadioOptions]:checked').val()]) {
                $(td).addClass('significant');
            } else if (rowData.obs) {
                $(td).addClass('observed');
            } else {
                $(td).addClass('inferred');
            }
        }
        // render: $.fn.dataTable.render.ellipsis(50, false)
    }, {
        "targets": '_all',
        defaultContent: '-',
        render: function(data, type, row) {
            if (typeof(data) == 'number') {
                return data.toFixed(2);
            } else if (typeof(data) == 'string') {
                return data.trunc(50);
            // } else if (data === null) {
            //     return '-'
            } else {
                return data;
            }
        }
    }],
    "order": [[2, "asc"]],
    'buttons': [
        {
            extend: 'colvis',
            columns: ':gt(1)'
        }
    ],
    'rowCallback': function (row, data, index) {
        // set tooltip
        function objToString (obj) {
            let str = '';
            for (let p in obj) {
                if (obj.hasOwnProperty(p) && obj[p] !== null && p.startsWith('padj')) {
                    str += p + ': ' + obj[p].toFixed(4) + '\n';
                }
            }
            return str;
        }
        const tooltip = objToString(data);
        if (tooltip.length > 0) {
            $(row).attr({
                'title': objToString(data)
            })
        }

        // set cell colours
        const colNames = Object.keys(data);
        if (colNames.includes('pathway_id') && colNames.includes('padj_fdr')) {
            // // colour pathway table
            // const idx = colNames.indexOf('pathway_id');
            // const pathway_id = data['pathway_id'];
            // const padj = data['padj_fdr'];
            // if (pathway_id !== '-' && padj !== null) {
            //     const colorScale = d3.scaleLinear()
            //         .range(["red", "green"])
            //         .domain([1, 0]);
            //     const colour = colorScale(padj);
            //     const idx = 2;
            //     $(row).find(`td:eq(${idx})`).css({
            //         'background-color': colour,
            //         'color': 'white'
            //     });
            // }
        } else {
            // colour other tables that have t-tests done
            const filtered = colNames.filter(x => x.indexOf('FC') > -1);
            const filteredIdx = filtered.map(x => {
                return colNames.indexOf(x);
            });
            const filtered_logfc = filtered.map(x => data[x]);
            const colorScale = d3.scale.linear()
                .range(["red", "green"])
                .domain([-2, 2]);
            const filteredColours = filtered_logfc.map(x => colorScale(x));
            for (let i = 0; i < filteredIdx.length; i++) {
                const idx = filteredIdx[i];
                const colour = filteredColours[i];
                const x = $(row).find(`td`).filter(function() {
                    // TODO: round to the specified decimal places and compare the string representation. Might not always work.
                    const dp = 2;
                    const val1 = parseFloat(this.textContent).toFixed(dp);
                    let val2 = filtered_logfc[i];
                    if (val2 === null) {
                        return false;
                    } else {
                        val2 = val2.toFixed(dp);
                    }
                    if (val2 === '-0.00') {
                        val2 = '0.00'
                    }
                    return val1 === val2;
                });
                if (x) {
                    x.css({
                        'background-color': colour,
                        'color': 'white'
                    });
                }
            }
        }
    }
    // 'responsive': true
};


class Linker {

    constructor(tableData, tableFields, viewNames) {
        this.tableData = tableData;
        this.tableFields = tableFields;
        this.viewNames = viewNames;

        const tables = [ // the ordering in this list is important! do not change it.

            {
                "tableName": "genes_table",
                "tableData": tableData.genes,
                "options": {
                    "visible": true,
                    "pk": "gene_pk",
                    "order_by": "gene_id"
                },
                "relationship": {"with": "gene_proteins", "using": "gene_pk"}
            },

            {
                "tableName": "gene_proteins",
                "tableData": tableData.gene_proteins,
                "options": {
                    "visible": false
                },
                "relationship": {"with": "proteins_table", "using": "protein_pk"}
            },

            {
                "tableName": "proteins_table",
                "tableData": tableData.proteins,
                "options": {
                    "visible": true,
                    "pk": "protein_pk",
                    "order_by": "protein_id"
                },
                "relationship": {"with": "protein_reactions", "using": "protein_pk"}
            },

            {
                "tableName": "protein_reactions",
                "tableData": tableData.protein_reactions,
                "options": {
                    "visible": false
                },
                "relationship": {"with": "reactions_table", "using": "reaction_pk"}
            },

            {
                "tableName": "reactions_table",
                "tableData": tableData.reactions,
                "options": {
                    "visible": true,
                    "pk": "reaction_pk",
                    "order_by": "reaction_id"
                },
                "relationship": [
                    {"with": "compound_reactions", "using": "reaction_pk"},
                    {"with": "reaction_pathways", "using": "reaction_pk"}
                ]
            },

            {
                "tableName": "compounds_table",
                "tableData": tableData.compounds,
                "options": {
                    "visible": true,
                    "pk": "compound_pk",
                    "order_by": "compound_id"
                }
            },

            {
                "tableName": "compound_reactions",
                "tableData": tableData.compound_reactions,
                "options": {
                    "visible": false
                },
                "relationship": {"with": "compounds_table", "using": "compound_pk"}
            },

            {
                "tableName": "reaction_pathways",
                "tableData": tableData.reaction_pathways,
                "options": {
                    "visible": false
                },
                "relationship": {"with": "pathways_table", "using": "pathway_pk"}
            },

            {
                "tableName": "pathways_table",
                "tableData": tableData.pathways,
                "options": {
                    "visible": true,
                    "pk": "pathway_pk",
                    "order_by": "pathway_id"
                }
            }

        ];

        // https://stackoverflow.com/questions/24383805/datatables-change-number-of-pagination-buttons
        // $.fn.DataTable.ext.pager.numbers_length = 3;

        const infoPanesManager = new InfoPanesManager(viewNames);
        const firdi = new FiRDI(tables, defaultDataTablesSettings, infoPanesManager);

        // Hide certain columns
        let columnsToHidePerTable = [
            {"tableName": "genes_table", "columnNames": ["obs", "gene_pk", "significant_all", "significant_any"]},
            {"tableName": "proteins_table", "columnNames": ["obs", "protein_pk", "significant_all", "significant_any"]},
            {"tableName": "compounds_table", "columnNames": ["obs", "compound_pk", "significant_all", "significant_any"]},
            {"tableName": "reactions_table", "columnNames": ["obs", "reaction_pk", "significant_all", "significant_any"]},
            {"tableName": "pathways_table", "columnNames": ["obs", "pathway_pk", "significant_all", "significant_any"]}
        ];

        columnsToHidePerTable.forEach(function (tableInfo) {
            const tableAPI = $('#' + tableInfo['tableName']).DataTable();
            // get all column names containing the word 'padj' or 'species' to hide as well
            const colNames = tableAPI.settings()[0].aoColumns.map(x => x.sName);
            const filtered = colNames.filter(x => x.indexOf('padj') > -1 || x.indexOf('species') > -1);
            tableInfo['columnNames'] = tableInfo['columnNames'].concat(filtered);
            // get all columns names for the raw data and hide them as well
            const colData = tableFields[tableInfo['tableName']];
            if (colData) {
                tableInfo['colData'] = colData;
                tableAPI
                    .columns(tableInfo['colData'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                    .visible(false);
            }
            // do the hiding here
            tableAPI
                .columns(tableInfo['columnNames'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                .visible(false);

        });

        // show/hide data columns
        $('#showDataCheck').change(function () {
            let visible = false;
            if (this.checked) {
                visible = true;
            }
            columnsToHidePerTable.forEach(function (tableInfo) {
                const tableAPI = $('#' + tableInfo['tableName']).DataTable();
                if (tableInfo['colData']) {
                    tableAPI
                        .columns(tableInfo['colData'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                        .visible(visible);
                }
            });
        });

        // enable global search box
        $('#global_filter').on('keyup click', function () {
            const val = $('#global_filter').val();
            $.fn.dataTable.tables({api: true}).search(val).draw();
        });

    }

}

export default Linker;