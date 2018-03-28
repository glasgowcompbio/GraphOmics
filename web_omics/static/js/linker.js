const myLinker = (function () {

    let linkerResultsManager = {
        init: function (data) {

            const defaultDataTablesSettings = {
                "dom": "prt",
                "pageLength": 10,
                // "scrollY": "400px",
                // "scrollCollapse": true,
                "searching": true,
                // see https://datatables.net/plug-ins/dataRender/ellipsis
                "columnDefs": [{
                    targets: 1,
                    render: $.fn.dataTable.render.ellipsis(50, false)
                }]
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

            columnsToHidePerTable.forEach(function (tableInfo) {
                $('#' + tableInfo['tableName']).DataTable()
                    .columns(tableInfo['columnNames'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                    .visible(false);
            });

            // set event handler when rows in the visible tables are clicked
            this.visibleTableNames = ["compounds_table"];
            this.visibleTableNames.forEach(tableName => $('#' + tableName)
                .DataTable()
                .on('user-select', this.dataTablesDrawFunction));

            // enable global search box
            $('#global_filter').on('keyup click', function () {
                let val = $('#global_filter').val();
                $.fn.dataTable.tables({api: true}).search(val).draw();
            });

        }, // end init

        dataTablesDrawFunction: function (e, dt, type, cell, originalEvent) {
            // calls the appropriate info pane functions
            e.preventDefault();
            const tableId = e.currentTarget.id,
                tables = $('.dataTable').DataTable(),
                tableAPI = tables.table('#' + tableId),
                selectedData = tableAPI.row('.selected').data();

            if (selectedData) {
                infoPanesManager.getEntityInfo(tableId, selectedData);
            } else {
                infoPanesManager.clearInfoPane(tableId);
            }

        },

    } // end linkerResultsManager

    const infoPanesManager = {
        clearInfoPane: function (tableId) {
            // Wrapper function to call the appropriate info function for the given table/entity
            if (tableId === 'peaks_table') {
                this.clearPeakInfo();
            } else if (tableId === 'compounds_table') {
                this.clearInfoPanel('compound-row-info', 'Compound Information');
            } else if (tableId === 'pathways_table') {
                this.clearPathwayInfo();
            }
        },
        getEntityInfo: function (tableId, rowObject) {
            // Wrapper function to call the appropriate info function for the given table/entity
            if (tableId === 'peaks_table') {
                // this.getPeakInfo(rowObject)
            } else if (tableId === 'compounds_table') {
                this.getInfoPanel(rowObject, get_kegg_metabolite_info,
                    'compound-row-info', 'compound_pk', 'kegg_id');
            } else if (tableId === 'pathways_table') {
                // this.getPathwayInfo(rowObject);
            }
        },
        getInfoPanel: function (rowObject, dataUrl, rowId, pkCol, displayNameCol) {
            this.clearInfoPanel(rowId);
            if (rowObject[displayNameCol] != '---') {

                const tableData = {'id': rowObject[pkCol]};
                let infoDiv = $('<div/>');
                let infoTitle = $('<h5/>', {
                    'text': rowObject[displayNameCol]
                });
                let dataDiv = $('<div\>', {
                    'html': '<p>Loading data...</p>'
                });
                infoDiv.append(infoTitle);

                $.getJSON(dataUrl, tableData, data => {

                    // loop over additional information
                    let infos = data['infos'];
                    for (let item of infos) {
                        infoDiv.append(`<p>${item.key}: ${item.value}</p>`);
                    }

                    // loop over images
                    let images = data['images']
                    for (let item of images) {
                        let newImage = $('<img/>', {
                            'src': item,
                            'class': 'img-responsive'
                        });
                        dataDiv.empty().append(newImage);
                    }

                    // loop over external links
                    let links = data['links']
                    for (let link of links) {
                        dataDiv.append($('<p/>').append($('<a/>', {
                            'href': link.href,
                            'text': link.text,
                            'target': '_blank'
                        })));
                    }

                });

                const selector = '#' + rowId + ' .panel-body';
                $(selector).empty();
                $(selector).append(infoDiv);
                $(selector).append(dataDiv);
            } else {
                $(selector).text('Click an entry above for more information');
            }
        },
        clearInfoPanel: function (rowId, title) {
            // Create the divs that make up the 'blank' metabolite info panel
            var infoPanel = $('<div/>', {'class': 'panel panel-default'});
            var infoTitle = $('<div/>', {'class': 'panel-heading'});
            var infoTitleContent = $('<h1/>', {
                'class': 'panel-title',
                'text': title
            });
            var bodyBlank = $('<div/>', {
                'text': 'Click an entry above for more information',
                'class': 'panel-body'
            });

            // Combine them
            // Put the title content into the panel title
            infoTitle.append(infoTitleContent)
            // Put the title into the parent panel
            infoPanel.append(infoTitle)
            // Put the body content into the parent panel
            infoPanel.append(bodyBlank);

            const selector = '#' + rowId;
            $(selector).empty().append(infoPanel);
        },
    } // end infoPanesManager


    return {
        init: linkerResultsManager.init.bind(linkerResultsManager)
    };

})();


$(document).ready(function () {

    let pqr = myLinker.init(data);

});