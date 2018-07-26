// https://stackoverflow.com/questions/1199352/smart-way-to-shorten-long-strings-with-javascript
String.prototype.trunc = String.prototype.trunc ||
      function(n){
          return (this.length > n) ? this.substr(0, n-1) + '&hellip;' : this;
      };

const myLinker = (function () {

    let linkerResultsManager = {
        init: function (data) {

            const defaultDataTablesSettings = {
                // "dom": "Brftip",
                "dom": "Brpit",
                "pageLength": 10,
                // "scrollY": "400px",
                // "scrollCollapse": true,
                "searching": true,
                "columnDefs": [{
                    targets: 2,
                    createdCell: function(td, cellData, rowData, row, col) {
                        if (rowData.obs === '-' || rowData.obs === null) {
                            // do nothing
                        } else if (rowData.obs) {
                            $(td).addClass('observed');
                        } else {
                            $(td).addClass('inferred');
                        }
                    }
                    // render: $.fn.dataTable.render.ellipsis(50, false)
                }, {
                    "targets": '_all',
                    render: function(data, type, row) {
                        if (typeof(data) == 'number') {
                            return data.toFixed(2);
                        } else if (typeof(data) == 'string') {
                            return data.trunc(50);
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
                    const colNames = Object.keys(data);
                    const filtered = colNames.filter(x => x.indexOf('FC') > -1);
                    const filteredIdx = filtered.map(x => {
                        return colNames.indexOf(x);
                    });
                    const filtered_logfc = filtered.map(x => data[x]);
                    var colorScale = d3.scaleLinear()
                        .range(["red", "green"])
                        .domain([-2, 2]);
                    const filteredColours = filtered_logfc.map(x => colorScale(x));
                    for (let i = 0; i < filteredIdx.length; i++) {
                        const idx = filteredIdx[i];
                        const colour = filteredColours[i];
                        // $(row).find(`td:eq(${idx})`).css({
                        //     'background-color': colour,
                        //     'color': 'white'
                        // });
                        x = $(row).find(`td`).filter(function() {
                            // TODO: round to the specified decimal places and compare the string representation. Might not always work.
                            const dp = 2;
                            const val1 = parseFloat(this.textContent).toFixed(dp);
                            let val2 = filtered_logfc[i].toFixed(dp);
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
                // 'responsive': true
            };

            const tables = [ // the ordering in this list is important! do not change it.

                {
                    "tableName": "genes_table",
                    "tableData": data.genes,
                    "options": {
                        "visible": true,
                        "pk": "gene_pk",
                        "order_by": "gene_id"
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
                        "pk": "protein_pk",
                        "order_by": "protein_id"
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
                    "tableData": data.compounds,
                    "options": {
                        "visible": true,
                        "pk": "compound_pk",
                        "order_by": "compound_id"
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
                        "pk": "pathway_pk",
                        "order_by": "pathway_id"
                    }
                }

            ];

            // https://stackoverflow.com/questions/24383805/datatables-change-number-of-pagination-buttons
            // $.fn.DataTable.ext.pager.numbers_length = 3;

            FiRDI.init(tables, defaultDataTablesSettings);

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
                const colData = data_fields[tableInfo['tableName']];
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


            // set event handler when rows in the visible tables are clicked
            this.visibleTableNames = ['genes_table', 'proteins_table',
                'compounds_table', 'reactions_table', 'pathways_table'];
            this.visibleTableNames.forEach(tableName => $('#' + tableName)
                .DataTable()
                .on('user-select', this.dataTablesDrawFunction));

            // enable global search box
            $('#global_filter').on('keyup click', function () {
                const val = $('#global_filter').val();
                $.fn.dataTable.tables({api: true}).search(val).draw();
            });

        }, // end init

        dataTablesDrawFunction: function (e, dt, type, cell, originalEvent) {
            // calls the appropriate info pane functions
            e.preventDefault();

            // update table
            const tableId = e.currentTarget.id;
            const tables = $('.dataTable').DataTable();
            const tableAPI = tables.table('#' + tableId);
            const selectedData = tableAPI.row('.selected').data();

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
                    'gene_id', 'Gene Information');
            } else if (tableId === 'proteins_table') {
                this.getInfoPanel(rowObject, get_uniprot_protein_info,
                    'protein-row-info', 'protein_pk',
                    'protein_id', 'Protein Information');
            } else if (tableId === 'compounds_table') {
                this.getInfoPanel(rowObject, get_kegg_metabolite_info,
                    'compound-row-info', 'compound_pk',
                    'compound_id', 'Compound Information');
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
            if (rowObject[displayNameCol] != '-') {

                const tableData = {
                    'id': rowObject[pkCol]
                };
                const displayName = rowObject[displayNameCol];
                let infoDiv = $('<div/>');
                let infoTitle = $('<h6/>', {
                    'text': displayName
                });
                infoDiv.append(infoTitle);

                let dataDiv = $('<div\>', {
                    'html': '<p>Loading data...</p>'
                });
                $.getJSON(dataUrl, tableData, data => {
                    const annotation = data['annotation'];
                    const annotationUrl = data['annotation_url'];
                    const annotationId = data['annotation_id'];
                    const annotationLink = '<button type="button" class="btn btn-default btn-sm"' +
                        `onclick="annotate('${annotationId}', '${annotationUrl}', '${displayName}')"><i class="fas fa-edit"></i></button>`;
                    infoTitle.append(annotationLink);

                    let annotationHtml = '';
                    if (annotation.length > 0) {
                        annotationHtml = `<p><strong>Annotation</strong>: ${annotation}</p>`
                    }
                    const annotationDiv = $('<div\>', {
                        id: `annotation-${annotationId}`,
                        html: annotationHtml,
                        class: 'annotation'
                    });
                    infoDiv.append(annotationDiv);

                    // loop over additional information
                    let infos = data['infos'];
                    for (let item of infos) {
                        const key = item.key;
                        const val = item.value + ''; // ensure that val is always a string
                        const url = item.url;
                        if (val.includes((';'))) {
                            let html = `<p><strong>${key}</strong>:</p><ul>`;
                            const tokens = val.split(';').map(x => x.trim());
                            if (url) {
                                const links = url.split(';').map(x => x.trim());
                                for (let i = 0; i < tokens.length; i++) {
                                    html += `<li><a href="${links[i]}" target="_blank">${tokens[i]}</a></li>`;
                                }
                            } else { // no url
                                for (let w of tokens) {
                                    html += `<li>${w}</li>`;
                                }
                            }
                            html += '</ul>';
                            infoDiv.append(html);
                        } else {
                            infoDiv.append(`<p><strong>${key}</strong>: ${val}</p>`);
                        }
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
                        return (url.match(/\.(jpeg|jpg|gif|png)$/) != null) || url.includes('chebi');
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
                                'href': item + "&quality=7",
                                'target': '_blank'
                            }).append(
                                $('<img/>', {
                                    'src': item + "&quality=3",
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
                                pv.io.fetchPdb(pdbUrl, function (structure) {
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
                            window.onresize = function (event) {
                                viewer.fitParent();
                            };

                        });

                    }

                });

                const selector = '#' + rowId;
                $(selector).empty();
                $(selector).append(infoDiv);
                $(selector).append(dataDiv);
            } else {
                $(selector).text('Select an entry below.');
            }
        },
        clearInfoPanel: function (rowId, title) {
            let content = $('<p/>', {
                'text': 'Select an entry below.'
            });
            const selector = '#' + rowId;
            $(selector).empty().append(content);
        },
    } // end infoPanesManager

    return {
        init: linkerResultsManager.init.bind(linkerResultsManager)
    };

})();

function annotate(annotationId, annotationUrl, displayName) {
    $('#annotationId').val(`annotation-${annotationId}`);
    let annotation = $(`#annotation-${annotationId}`).text();
    if (annotation.length > 0) {
        annotation = annotation.split(':')[1].trim();
    }
    $('#displayName').val(displayName);
    $('#annotationValue').val(annotation);
    $('#annotationForm').attr('action', annotationUrl);
    $('#annotationDialog').dialog({
        modal: true,
        width: 460,
    });
}

$(document).ready(function () {

    let pqr = myLinker.init(data);

    // see https://docs.djangoproject.com/en/dev/ref/csrf/#ajax
    // using jQuery
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var csrftoken = getCookie('csrftoken');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    $('#annotationSubmit').on('click', function (e) {
        const form = $('#annotationForm');
        const action = form.attr('action');
        const data = form.serialize();
        $.ajax({
            type: 'POST',
            url: action,
            data: data,
            success: function () {
                const annotId = $('#annotationId').val();
                const annotValue = $('#annotationValue').val();
                const annotHtml = `<p><strong>Annotation:</strong> ${annotValue}</p>`;
                $(`#${annotId}`).html(annotHtml);
                $('#annotationDialog').dialog('close');
            }
        });
    });

});