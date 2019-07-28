import '../css/linker.css';
import 'webpack-jquery-ui';
import 'webpack-jquery-ui/css';
import '../css/summary.css';
import {blockUI, loadData, setupCsrfForAjax, unblockUI} from './common';
import clustergrammer_setup from './clustergrammer_setup';

import FirdiState from "./firdi/FirdiState";
import Firdi from "./firdi/Firdi";
import SqlManager from "./firdi/SqlManager";
import InfoPanesManager from "./firdi/InfoPanesManager";
import GroupManager from './firdi/GroupManager';
import ObservableTodoStore from "./firdi/ObservableTodoStore";

$(document).ready(function () {

    let state = null;
    window.baseUrl = viewNames['get_short_info']; // TODO: shouldn't put this in global scope

    (async () => {

        blockUI();

        // required for pop-up submits to work
        setupCsrfForAjax()

        // load data and create a shared state
        const firdiData = await loadData(viewNames['get_firdi_data']);
        const tablesInfo = getTablesInfo(firdiData.tableData);
        const tableFields = firdiData.tableFields;
        const state = new FirdiState(tablesInfo, tableFields);

        // init firdi
        const firdi = new Firdi(state, viewNames);

        // init group manager
        const groupManager = new GroupManager(state, viewNames);

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

function getTablesInfo(tableData) {
    const tablesInfo = [ // the ordering in this list is important! do not change it.

        {
            "tableName": "genes_table",
            "tableData": tableData.genes,
            "options": {
                "visible": true,
                "pk": "gene_pk",
                "order_by": "gene_id"
            },
            "relationship": {"with": "gene_proteins", "using": "gene_pk"}
        },

        {
            "tableName": "gene_proteins",
            "tableData": tableData.gene_proteins,
            "options": {
                "visible": false
            },
            "relationship": {"with": "proteins_table", "using": "protein_pk"}
        },

        {
            "tableName": "proteins_table",
            "tableData": tableData.proteins,
            "options": {
                "visible": true,
                "pk": "protein_pk",
                "order_by": "protein_id"
            },
            "relationship": {"with": "protein_reactions", "using": "protein_pk"}
        },

        {
            "tableName": "protein_reactions",
            "tableData": tableData.protein_reactions,
            "options": {
                "visible": false
            },
            "relationship": {"with": "reactions_table", "using": "reaction_pk"}
        },

        {
            "tableName": "reactions_table",
            "tableData": tableData.reactions,
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
            "tableData": tableData.compounds,
            "options": {
                "visible": true,
                "pk": "compound_pk",
                "order_by": "compound_id"
            }
        },

        {
            "tableName": "compound_reactions",
            "tableData": tableData.compound_reactions,
            "options": {
                "visible": false
            },
            "relationship": {"with": "compounds_table", "using": "compound_pk"}
        },

        {
            "tableName": "reaction_pathways",
            "tableData": tableData.reaction_pathways,
            "options": {
                "visible": false
            },
            "relationship": {"with": "pathways_table", "using": "pathway_pk"}
        },

        {
            "tableName": "pathways_table",
            "tableData": tableData.pathways,
            "options": {
                "visible": true,
                "pk": "pathway_pk",
                "order_by": "pathway_id"
            }
        }

    ];
    return tablesInfo;
}