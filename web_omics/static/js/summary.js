const Clustergrammer = require('clustergrammer');
require('../css/summary.css');

$(document).ready(function () {

    window.gene_data = {};

    function get_mouseover(root_tip, gene_symbol) {

        // not sure if this is necessary
        if (d3.select(root_tip + '_row_tip').classed(gene_symbol)) {
            get_request(root_tip, gene_symbol);
        }

    }

    function get_request(root_tip, ini_gene_symbol) {

        var gene_symbol;
        if (ini_gene_symbol.indexOf(' ') > 0) {
            gene_symbol = ini_gene_symbol.split(' ')[0];
        } else if (ini_gene_symbol.indexOf('_') > 0) {
            gene_symbol = ini_gene_symbol.split('_')[0];
        }
        else {
            gene_symbol = ini_gene_symbol;
        }

        var base_url = 'https://amp.pharm.mssm.edu/Harmonizome/api/1.0/gene/';
        var url = base_url + gene_symbol;

        $.get(url, function (data) {

            data = JSON.parse(data);

            // save data for repeated use
            window.gene_data[gene_symbol] = {}
            window.gene_data[gene_symbol].name = data.name;
            window.gene_data[gene_symbol].description = data.description;

            set_tooltip(data, root_tip, ini_gene_symbol);

            return data;

        });
    }

    function set_tooltip(data, root_tip, gene_symbol) {

        if (data.name != undefined) {

            d3.selectAll(root_tip + '_row_tip')
                .html(function () {
                    var sym_name = gene_symbol + ': ' + data.name;
                    var full_html = '<p>' + sym_name + '</p>' + '<p>' +
                        data.description + '</p>';
                    return full_html;
                });
        }
    }


    function gene_info(root_tip, gene_info) {

        var gene_symbol = gene_info.name;

        if (_.has(window.gene_data, gene_symbol)) {
            var inst_data = window.gene_data[gene_symbol];
            set_tooltip(inst_data, root_tip, gene_symbol);
        } else {
            setTimeout(get_mouseover, 250, root_tip, gene_symbol);
        }

    }

    function renderHeatmap(elementId, dataType, clusterJson) {
        if (clusterJson.hasOwnProperty(dataType)) {
            $(elementId).text('');
            $(elementId).addClass('heatmap_container');
            const jsonData = JSON.parse(clusterJson[dataType]);
            const args = {
                root: elementId,
                network_data: jsonData,
                // opacity_scale: 'linear',
                row_tip_callback: gene_info,
            };
            const cgm = Clustergrammer(args);
        } else {
            $(elementId).text('No data is available.');
        }
    }

    const clusterJson = window.props.cluster_json;
    renderHeatmap('#summary-vis-gene', 'gene', clusterJson);
    renderHeatmap('#summary-vis-protein', 'protein', clusterJson);
    renderHeatmap('#summary-vis-compound', 'compound', clusterJson);
});