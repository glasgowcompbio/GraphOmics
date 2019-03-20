import Linker from './linker.js';
import '../css/linker.css';
import 'webpack-jquery-ui';
import 'webpack-jquery-ui/css';
import '../css/summary.css';
import { showAnnotateDialog, handleAnnotateSubmit } from './annotate';
import { setupCsrfForAjax } from './common';
import renderHeatmap from './clustergrammer_setup';
import GroupManager from './group_manager';

async function loadData(viewUrl) {
    try {
        const result = await $.getJSON(viewUrl);
        return result;
    } catch (e) {
        console.log(e);
    }
}

$(document).ready(function () {

    let state = null;
    window.baseUrl = viewNames['get_short_info']; // TODO: shouldn't put this in global scope

    (async () => {
        // init firdi
        const firdiData = await loadData(viewNames['get_firdi_data']);
        const linker = new Linker(firdiData.tableData, firdiData.tableFields, viewNames);
        const state = linker.state;

        // init heatmap
        const heatmapData = await loadData(viewNames['get_heatmap_data']);
        await renderHeatmap('#summary-vis-gene', 'genes', heatmapData, state);
        await renderHeatmap('#summary-vis-protein', 'proteins', heatmapData, state);
        await renderHeatmap('#summary-vis-compound', 'compounds', heatmapData, state);

        // init group manager
        const groupManager = new GroupManager('saveSelectionButton', 'loadSelectionButton',
            'numSelected', state);

        // TODO: shouldn't put this in global scope
        window.annotate = showAnnotateDialog
        setupCsrfForAjax() // required for annotate submit to work
        $('#annotationSubmit').on('click', handleAnnotateSubmit);

    })().catch(e => {
        console.error(e);
    });

});