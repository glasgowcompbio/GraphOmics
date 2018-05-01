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
                }],
                "order": [[ 1, "asc" ]],
                // 'responsive': true
            };

            const tables = [ // the ordering in this list is important! do not change it.

                {
                    "tableName": "genes_table",
                    "tableData": data.genes,
                    "options": {
                        "visible": true,
                        "pk": "gene_pk"
                    },
                    "relationship": {"with": "gene_proteins", "using": "gene_pk"}
                },

                {
                    "tableName": "gene_proteins",
                    "tableData": data.gene_proteins,
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
                {"tableName": "genes_table", "columnNames": ["gene_pk"]},
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
            this.visibleTableNames = ['genes_table', 'proteins_table',
                'compounds_table', 'reactions_table', 'pathways_table'];
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
            if (tableId === 'genes_table') {
                this.clearInfoPanel('gene-row-info', 'Gene Information');
            } else if (tableId === 'proteins_table') {
                this.clearInfoPanel('protein-row-info', 'Protein Information');
            } else if (tableId === 'compounds_table') {
                this.clearInfoPanel('compound-row-info', 'Compound Information');
            } else if (tableId === 'reactions_table') {
                this.clearInfoPanel('reaction-row-info', 'Reaction Information');
            } else if (tableId === 'pathways_table') {
                this.clearInfoPanel('pathway-row-info', 'Pathway Information');
            }
        },
        getEntityInfo: function (tableId, rowObject) {
            // Wrapper function to call the appropriate info function for the given table/entity
            if (tableId === 'genes_table') {
                this.getInfoPanel(rowObject, get_ensembl_gene_info,
                    'gene-row-info', 'gene_pk',
                    'ensembl_id', 'Gene Information');
            } else if (tableId === 'proteins_table') {
                this.getInfoPanel(rowObject, get_uniprot_protein_info,
                    'protein-row-info', 'protein_pk',
                    'uniprot_id', 'Protein Information');
            } else if (tableId === 'compounds_table') {
                this.getInfoPanel(rowObject, get_kegg_metabolite_info,
                    'compound-row-info', 'compound_pk',
                    'kegg_id', 'Compound Information');
            } else if (tableId === 'reactions_table') {
                this.getInfoPanel(rowObject, get_reactome_reaction_info,
                    'reaction-row-info', 'reaction_pk',
                    'reaction_id', 'Reaction Information');
            } else if (tableId === 'pathways_table') {
                this.getInfoPanel(rowObject, get_reactome_pathway_info,
                    'pathway-row-info', 'pathway_pk',
                    'pathway_id', 'Pathway Information');
            }
        },
        getInfoPanel: function (rowObject, dataUrl,
                                rowId, pkCol,
                                displayNameCol, title) {
            this.clearInfoPanel(rowId, title);
            if (rowObject[displayNameCol] != '---') {

                const tableData = {
                    'id': rowObject[pkCol],
                    'species': SPECIES
                };
                let infoDiv = $('<div/>');
                let infoTitle = $('<h6/>', {
                    'text': rowObject[displayNameCol]
                });
                infoDiv.append(infoTitle);

                let dataDiv = $('<div\>', {
                    'html': '<p>Loading data...</p>'
                });
                $.getJSON(dataUrl, tableData, data => {

                    // loop over additional information
                    let infos = data['infos'];
                    for (let item of infos) {
                        infoDiv.append(`<p><strong>${item.key}</strong>: ${item.value}</p>`);
                    }

                    // loop over external links
                    dataDiv.empty();
                    let links = data['links']
                    for (let link of links) {
                        let newLink = $('<p/>').append($('<a/>', {
                            'href': link.href,
                            'text': link.text,
                            'target': '_blank'
                        }));
                        dataDiv.append(newLink);
                    }

                    // loop over images
                    function isImageUrl(url) {
                        return(url.match(/\.(jpeg|jpg|gif|png)$/) != null);
                    }
                    let images = data['images'];
                    let pdbs = [];
                    for (let item of images) {
                        if (isImageUrl(item)) {
                            let newImage = $('<img/>', {
                                'src': item,
                                'class': 'img-fluid'
                            });
                            dataDiv.append(newImage);
                        } else if (item.includes('reactome')) { // handle reactome images
                            let newLink = $('<a/>', {
                                'href': item + "&quality=10",
                                'target': '_blank'
                            }).append(
                                $('<img/>', {
                                    'src': item + "&quality=5",
                                    'class': 'img-fluid'
                                })
                            );
                            dataDiv.append(newLink);
                        } else { // assume it's pdb
                            pdbs.push(item);
                        }
                    }

                    if (pdbs.length > 0) {

                        // draw first pdb
                        let first = pdbs[0];
                        let pvDiv = $('<div/>', {'id': 'pvViewer'});
                        dataDiv.append(pvDiv);

                        require([biopv_url], function (pv) {

                            let viewer = pv.Viewer(document.getElementById('pvViewer'), {
                              quality: 'medium',
                              width: '200',
                              height: '200',
                              antialias: true,
                              outline: true,
                              slabMode: 'auto'
                            });

                            function load(pdbUrl) {
                              pv.io.fetchPdb(pdbUrl, function(structure) {
                                // render everything as helix/sheet/coil cartoon, coloring by secondary
                                // structure succession
                                let go = viewer.cartoon('structure', structure, {
                                  color: pv.color.ssSuccession(),
                                  showRelated: '1',
                                });

                                // find camera orientation such that the molecules biggest extents are
                                // aligned to the screen plane.
                                let rotation = pv.viewpoint.principalAxes(go);
                                viewer.setRotation(rotation)

                                // adapt zoom level to contain the whole structure
                                viewer.autoZoom();
                              });
                            }

                            // load default
                            let queryUrl = get_swissmodel_protein_pdb + "?pdb_url=" + encodeURIComponent(first);
                            load(queryUrl);

                            // tell viewer to resize when window size changes.
                            window.onresize = function(event) {
                              viewer.fitParent();
                            };

                        });

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
            let infoPanel = $('<div/>', {'class': 'panel panel-default'});
            let infoTitle = $('<div/>', {'class': 'panel-heading'});
            let infoTitleContent = $('<h6/>', {
                'class': 'panel-title',
                'text': title
            });
            let bodyBlank = $('<div/>', {
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