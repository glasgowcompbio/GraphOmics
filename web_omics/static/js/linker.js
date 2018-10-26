const FiRDI = require('./firdi.js');
const d3 = require("d3");

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
                "dom": "Brtip",
                "pageLength": 10,
                // "scrollY": "800px",
                // "scrollCollapse": true,
                "pagingType": "simple",
                "searching": true,
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
                        const colorScale = d3.scaleLinear()
                            .range(["red", "green"])
                            .domain([-2, 2]);
                        const filteredColours = filtered_logfc.map(x => colorScale(x));
                        for (let i = 0; i < filteredIdx.length; i++) {
                            const idx = filteredIdx[i];
                            const colour = filteredColours[i];
                            x = $(row).find(`td`).filter(function() {
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
                    const annotationLink = '<button type="button" class="btn btn-outline-primary btn-sm" style="margin-left: 5px"' +
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
                        }
                    }

                    // plot intensities here
                    const plotData = data['plot_data']
                    if (data.hasOwnProperty('plot_data')) {
                        let plotDiv = document.createElement('div');
                        let d3_intensity_chart_load_btn = $('<button/>', {
                            'class': 'btn btn-sm btn-outline-primary',
                            'text': 'Show measurements',
                            'css': {
                                'margin-top': '10px'
                            }
                        });
                        dataDiv.append(d3_intensity_chart_load_btn);
                        dataDiv.append(plotDiv);
                        this.plotPeakIntensitySamples(plotDiv, plotData);

                        let $_plotDiv = $(plotDiv);
                        $_plotDiv.hide();
                        d3_intensity_chart_load_btn.click(function() {
                            $_plotDiv.toggle('fast');
                        });
                    }

                });

                const selector = '#' + rowId;
                $(selector).empty();
                $(selector).append(infoDiv);
                $(selector).append(dataDiv);
            } else {
                $(selector).text('Select an entry above.');
            }
        },
        clearInfoPanel: function (rowId, title) {
            let content = $('<p/>', {
                'text': 'Select an entry above.'
            });
            const selector = '#' + rowId;
            $(selector).empty().append(content);
        },
        plotPeakIntensitySamples: function(plotDiv, data) { // slightly modified from ross' pimp_quick_results_firdi.js
          var dataStore = [];
            // console.log(data);
            var maxOverallIntensity = 0,
                attributes = Object.keys(data);

            attributes.forEach(function(attribute, i) {
              var attributeSamples = data[attribute],
                  intensities = d3.values(attributeSamples),
                  sampleNames = Object.keys(attributeSamples),
                  maxAttributeIntensity = d3.max(intensities),
                  sortedIntensities = d3.values(attributeSamples).sort(d3.ascending),
                  boxPlotStatistics = {
                    lowerquantile: d3.quantile(sortedIntensities, 0.25),
                    median: d3.quantile(sortedIntensities, 0.5),
                    upperquantile: d3.quantile(sortedIntensities, 0.75),
                    mini: d3.min(sortedIntensities),
                    maxi: d3.max(sortedIntensities)
                  },
                  points = [];

              maxOverallIntensity = (maxOverallIntensity > maxAttributeIntensity ? maxOverallIntensity : maxAttributeIntensity);

              // Make x y coordinates
              intensities.forEach(function(d, i) {
                points.push({
                  x: attribute,
                  y: d,
                  z: sampleNames[i],
                });
              });

              dataStore.push({
                attributeName: attribute,
                boxPlotStatistics: boxPlotStatistics,
                points: points
              });
            });

            console.log('d3 munged data', dataStore);

            // d3 margin convention. Make the width and height relative to page components
            var margin = {top: 20, bottom: 75, right: 20, left: 60},
                width = $('#gene-row-info').width() - margin.right - margin.left,
                height = $('#genes_table_wrapper').height() - margin.top - margin.bottom - 50;

            // Initialise the svg
            var svg = d3.select(plotDiv)
              .append('svg')
              .attr('width', width + margin.left + margin.right)
              .attr('height', height + margin.top + margin.bottom)
              .classed("d3-intensity-chart", true);

            // Make the graphing area
            var graph = svg.append('g')
              .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

            // set the x and y scale functions
            var yScale = d3.scaleLinear()
              .domain([0, maxOverallIntensity*1.1]) // add some extra space at the top of the y axis with *1.1
              .range([height, 0]);
            var xScale = d3.scalePoint()
              .domain(attributes)
              .range([0, width])
              .round(true)
              .padding(0.5);

            // x axis
            graph.append('g')
              .attr('transform', 'translate(0,' + height + ')')
              .call(d3.axisBottom(xScale))
              .selectAll("text")
              .attr('y', -5) // rotate and adjust tick positions
              .attr('x', -30)
              .attr('transform', 'rotate(270)');

            // y axis
            graph.append('g')
              .call(d3.axisLeft(yScale)
              .ticks(5, 'e')); // scientific notation

            // y axis label
            svg.append("text")
              .text('Relative intensity')
              .attr('transform', 'translate(' + margin.left/6 +  ',' + (height*0.75) + ') rotate(270)');

            // make a group for each
            var pointStep = xScale.step(),
                horizontalLineWidth = pointStep/4;

            // Functions for mouseover
            function displaySampleName(d, i) {
              var circle = d3.select(this);
              d3.select(this)
                .attr('fill', 'blue')
                .attr('r', 10);

              svg.append('text')
                .attr('id', function() { return 'sample-name-text-' + d.z.split('.')[0]; })
                .attr('x', (width + margin.top + margin.bottom) / 2)
                .attr('y', margin.top)
                .text(function() { return d.z.split('.')[0]; });
            }

            function hideSampleName(d, i) {
              d3.select(this)
                .attr('fill', 'black')
                .attr('r', 3);

              d3.select('#sample-name-text-' + d.z.split('.')[0]).remove();
            }

            var dataSeriesGroups = graph.selectAll('g .data-series-group')
              .data(dataStore)
              .enter()
              .append('g')
              .attr('class', 'data-series-group')
              .attr('id', function(d) { return 'data-series-' + d.attribute; });

            dataSeriesGroups.each(function(attribute, i) {
              var coordinates = attribute.points;
              var boxPlotStatistics = [attribute.boxPlotStatistics],
                g = d3.select(this);

              // Add circles for each data point
              g.selectAll('circle')
                .data(coordinates)
                .enter()
                .append('circle')
                .attr('cx', function(d) { return xScale(d.x); })
                .attr('cy', function(d) { return yScale(d.y); })
                .attr('r', 3)
                .attr('sample-name', function(d) { return d.z; })
                .on('mouseover', displaySampleName)
                .on('mouseout', hideSampleName);

              // Median line
              g.selectAll('line .median-line')
                .data(boxPlotStatistics)
                .enter()
                .append('line')
                .attr('class', 'median-line')
                .attr('x1', xScale(attribute.attributeName) -  horizontalLineWidth)
                .attr('x2', xScale(attribute.attributeName) +  horizontalLineWidth)
                .attr('y1', function(d) { return yScale(d.median); })
                .attr('y2', function(d) { return yScale(d.median); })
                .attr('stroke', 'black');

              // Quantile box
              g.selectAll('rect .quantile-box')
                .data(boxPlotStatistics)
                .enter()
                .append('rect')
                .attr('class', 'quantile-box')
                .attr('x', xScale(attribute.attributeName) - horizontalLineWidth)
                .attr('y', function(d) { return yScale(d.upperquantile); })
                .attr('width', horizontalLineWidth*2)
                .attr('height', function(d) { return (yScale(d.lowerquantile) - yScale(d.upperquantile)); })
                .attr('stroke', 'black')
                .style('fill', 'none');

              // horizontal line for upper whisker
              g.selectAll('line .upper-whisker-horizontal-line')
                .data(boxPlotStatistics)
                .enter()
                .append('line')
                .attr('class', 'upper-whisker-line')
                .attr('x1', function(d) { return xScale(attribute.attributeName) -  horizontalLineWidth; })
                .attr('x2', function(d) { return xScale(attribute.attributeName) +  horizontalLineWidth; })
                .attr('y1', function(d) { return yScale(d.maxi); })
                .attr('y2', function(d) { return yScale(d.maxi); })
                .attr('stroke', 'black');

              // vertical line for upper whisker
              g.selectAll('line .upper-whisker-vertical-line')
                .data(boxPlotStatistics)
                .enter()
                .append('line')
                .attr('class', '.upper-whisker-vertical-line')
                .attr('x1', function(d) { return xScale(attribute.attributeName); })
                .attr('x2', function(d) { return xScale(attribute.attributeName); })
                .attr('y1', function(d) { return yScale(d.lowerquantile); })
                .attr('y2', function(d) { return yScale(d.mini); })
                .attr('stroke', 'black');


              // horizontal line for lower whisker
              g.selectAll('line .lower-whisker-horizonal-line')
                .data(boxPlotStatistics)
                .enter()
                .append('line')
                .attr('class', 'upper-lower-line')
                .attr('x1', function(d) { return xScale(attribute.attributeName) -  horizontalLineWidth; })
                .attr('x2', function(d) { return xScale(attribute.attributeName) +  horizontalLineWidth; })
                .attr('y1', function(d) { return yScale(d.mini); })
                .attr('y2', function(d) { return yScale(d.mini); })
                .attr('stroke', 'black');

              // vertical line for lower whisker
              g.selectAll('line .lower-whisker-vertical-line')
                .data(boxPlotStatistics)
                .enter()
                .append('line')
                .attr('class', '.lower-whisker-vertical-line')
                .attr('x1', function(d) { return xScale(attribute.attributeName); })
                .attr('x2', function(d) { return xScale(attribute.attributeName); })
                .attr('y1', function(d) { return yScale(d.upperquantile); })
                .attr('y2', function(d) { return yScale(d.maxi); })
                .attr('stroke', 'black');
            }); // end dataSeriesGroups.each

        }, // end plotPeakIntensitySamples

    } // end infoPanesManager

    return {
        init: linkerResultsManager.init.bind(linkerResultsManager)
    };

})();

module.exports = exports = myLinker;