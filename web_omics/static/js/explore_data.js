import Linker from './linker.js';
import '../css/linker.css';
import 'webpack-jquery-ui';
import 'webpack-jquery-ui/css';
import '../css/summary.css';
import {loadData, setupCsrfForAjax, blockUI, unblockUI} from './common';
import clustergrammer_setup from './clustergrammer_setup';
import GroupManager from './GroupManager';

$(document).ready(function () {

    let state = null;
    window.baseUrl = viewNames['get_short_info']; // TODO: shouldn't put this in global scope

    (async () => {

        blockUI();

        // required for pop-up submits to work
        setupCsrfForAjax()

        // init firdi
        const firdiData = await loadData(viewNames['get_firdi_data']);
        const linker = new Linker(firdiData.tableData, firdiData.tableFields, viewNames);
        const state = linker.state;

        // init group manager
        const saveUrl = viewNames['save_group'];
        const loadUrl = viewNames['load_group'];
        const listUrl = viewNames['list_groups'];
        const groupManager = new GroupManager('saveGroupButton', 'loadGroupButton', 'numSelected', 'group',
            state, saveUrl, loadUrl, listUrl);

        unblockUI();

        // init heatmap
        const heatmapData = await loadData(viewNames['get_heatmap_data']);
        await clustergrammer_setup('#summary-vis-gene', 'genes', heatmapData, state);
        await clustergrammer_setup('#summary-vis-protein', 'proteins', heatmapData, state);
        await clustergrammer_setup('#summary-vis-compound', 'compounds', heatmapData, state);

    })().catch(e => {
        console.error(e);
    });

});