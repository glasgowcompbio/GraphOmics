import Linker from './Linker.js';
import '../css/linker.css';
import 'webpack-jquery-ui';
import 'webpack-jquery-ui/css';
import '../css/summary.css';
import {setupCsrfForAjax} from './common';
import clustergrammer_setup from './clustergrammer_setup';
import GroupManager from './GroupManager';

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

        // required for pop-up submits to work
        setupCsrfForAjax()

        // init firdi
        const firdiData = await loadData(viewNames['get_firdi_data']);
        const linker = new Linker(firdiData.tableData, firdiData.tableFields, viewNames);
        const state = linker.state;

        // init heatmap
        const heatmapData = await loadData(viewNames['get_heatmap_data']);
        await clustergrammer_setup('#summary-vis-gene', 'genes', heatmapData, state);
        await clustergrammer_setup('#summary-vis-protein', 'proteins', heatmapData, state);
        await clustergrammer_setup('#summary-vis-compound', 'compounds', heatmapData, state);

        // init group manager
        const groupManager = new GroupManager('saveSelectionButton', 'loadSelectionButton',
            'numSelected', state);

    })().catch(e => {
        console.error(e);
    });

});