import Linker from './linker.js';
import '../css/linker.css';
import 'webpack-jquery-ui';
import 'webpack-jquery-ui/css';
import '../css/summary.css';
import { setupCsrfForAjax, showAnnotateDialog, handleAnnotateSubmit } from './annotate';
import renderHeatmap from './clustergrammer_setup';

async function loadData(viewUrl) {
    try {
        const result = await $.getJSON(viewUrl);
        return result;
    } catch (e) {
        console.log(e);
    }
}

$(document).ready(function () {

    // load tables data
    loadData(viewNames['get_firdi_data']).then(function(data) {
        new Linker(data.tableData, data.tableFields, viewNames);
    })

    // load heatmap data
    window.baseUrl = viewNames['get_short_info']; // TODO: shouldn't put this in global scope
    loadData(viewNames['get_heatmap_data']).then(function(data) {
        renderHeatmap('#summary-vis-gene', 'genes', data);
        renderHeatmap('#summary-vis-protein', 'proteins', data);
        renderHeatmap('#summary-vis-compound', 'compounds', data);
    })

    // TODO: shouldn't put this in global scope
    window.annotate = showAnnotateDialog
    setupCsrfForAjax() // required for annotate submit to work
    $('#annotationSubmit').on('click', handleAnnotateSubmit);

});