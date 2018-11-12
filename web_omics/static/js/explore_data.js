import Linker from './linker.js';
require('../css/linker.css');
require('webpack-jquery-ui');
require('webpack-jquery-ui/css');
require('../css/summary.css');
import { setupCsrfForAjax, showAnnotateDialog, handleAnnotateSubmit } from './annotate';
import renderHeatmap from './clustergrammer_setup';

const baseUrl = 'http://localhost:8000/linker/get_short_info/';
const seenData = {};

$(document).ready(function () {

    // set up firdi tables
    let pqr = Linker.init(data);

    // TODO: shouldn't put this in global scope
    window.annotate = showAnnotateDialog
    setupCsrfForAjax() // required for annotate submit to work
    $('#annotationSubmit').on('click', handleAnnotateSubmit);

    // show heatmap
    renderHeatmap('#summary-vis-gene', 'genes', clusterJson);
    renderHeatmap('#summary-vis-protein', 'proteins', clusterJson);
    renderHeatmap('#summary-vis-compound', 'compounds', clusterJson);

});