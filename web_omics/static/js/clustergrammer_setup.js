import Clustergrammer from './clustergrammer/main';
import filter_network_using_new_nodes from './clustergrammer/network/filter_network_using_new_nodes';
import update_viz_with_network from './clustergrammer/update/update_viz_with_network';

import {deepCopy, FIRDI_UPDATE_EVENT, CLUSTERGRAMMER_UPDATE_EVENT, SELECTION_MANAGER_UPDATE_EVENT} from './common'
import check_setup_enrichr from './enrichrgram';

const seenData = {};

// similar to the filter_viz_using_names function in clustergrammer, but slightly
// modified to always restore all originalCgmNodes upon reset
function filter_viz_using_names(names, cgm, originalCgmNodes) {

    // names is an object with row and column names that will be used to filter
    // the matrix
    const params = cgm.params;
    const new_nodes = {};
    let found_nodes;

    ['row', 'col'].forEach(function (inst_rc) {

        var orig_nodes = params.inst_nodes[inst_rc + '_nodes'];
        if (names.hasOwnProperty(inst_rc)) {

            if (names[inst_rc].length > 0) {
                var inst_names = names[inst_rc];
                found_nodes = $.grep(orig_nodes, function (d) {
                    return $.inArray(d.name, inst_names) > -1;
                });
            } else {
                found_nodes = orig_nodes;
            }

        } else {
            found_nodes = orig_nodes;
        }

        if (found_nodes.length == 0) {
            found_nodes = orig_nodes;
        }
        new_nodes[inst_rc + '_nodes'] = found_nodes;

    });

    const new_network_data = filter_network_using_new_nodes(cgm.config, new_nodes);

    // takes entire cgm object
    // last argument tells it to not preserve categoty colors
    update_viz_with_network(cgm, new_network_data);

    // always restore the original nodes
    cgm.params.inst_nodes = deepCopy(originalCgmNodes);

};

function clustergrammer_setup(elementId, dataType, clusterJson, state) {
    if (clusterJson.hasOwnProperty(dataType) && clusterJson[dataType]) {

        $(elementId).text('');
        $(elementId).addClass('heatmap_container');
        const jsonData = JSON.parse(clusterJson[dataType]);
        const rowTipCallback = {
            'genes': getGeneInfo,
            'proteins': getProteinInfo,
            'compounds': getCompoundInfo
        }
        const about_string = 'Zoom, scroll, and click buttons to interact with the clustergram. <a href="http://amp.pharm.mssm.edu/clustergrammer/help"> <i class="fa fa-question-circle" aria-hidden="true"></i> </a>';
        const args = {
            root: elementId,
            network_data: jsonData,
            about: about_string,
            row_tip_callback: rowTipCallback[dataType],
            col_tip_callback: colTipCallback,
            tile_tip_callback: tileTipCallback,
            dendro_callback: dendroCallback,
            matrix_update_callback: matrixUpdateCallback,
            dendro_filter_callback: dendroFilterCallback,
            sidebar_width: 200
        };
        const cgm = Clustergrammer(args);

        // save the original, complete set of nodes
        state.originalCgmNodes[dataType] = deepCopy(cgm.params.inst_nodes);

        // TODO: setup enrichr. Still broken!!
        if (dataType === 'genes') {
            check_setup_enrichr(cgm);
        }

        // setup observer callback
        const queryResultNames = {
            'genes': ['genes_table', 'gene_id'],
            'proteins': ['proteins_table', 'protein_id'],
            'compounds': ['compounds_table', 'compound_id']
        };
        const [tableName, idName] = queryResultNames[dataType];
        cgm.tableName = tableName;

        // save current state instance to clustergrammer, and also
        // set the callback to handle firdi update
        cgm.state = state;
        cgm.state.on(FIRDI_UPDATE_EVENT, (data) => {
            let names = [];
            if (data.lastQueryResults.hasOwnProperty(tableName)) {
                // populate names based on the last query results for this table
                const queryResult = data.lastQueryResults[tableName];
                names = queryResult.map(x => x[idName]);
            } else { // if no last query result for this table, then use the selections for the table
                const selections = data.selections[tableName];
                names = selections.map(x => x.displayName);
            }
            const originalCgmNodes = data.originalCgmNodes[dataType];
            filter_viz_using_names({'row': names}, cgm, originalCgmNodes);
        })
        cgm.state.on(SELECTION_MANAGER_UPDATE_EVENT, (data) => {
            console.log('clustergrammer receives update from selection manager');
            console.log(data);
        })

    } else {
        $(elementId).text('No data is available.');
    }
}

function getGeneInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'gene');
}

function getProteinInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'protein');
}

function getCompoundInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'compound');
}

function getInfo(rootTip, rowData, dataType) {
    let displayName = rowData.name;
    if (displayName.indexOf(' ') > 0) {
        displayName = displayName.split(' ')[0];
    } else if (displayName.indexOf('_') > 0) {
        displayName = displayName.split('_')[0];
    }
    if (_.has(seenData, displayName)) {
        const cachedData = seenData[displayName];
        setTooltip(cachedData, rootTip, displayName);
    } else {
        setTimeout(getMouseOver, 250, rootTip, displayName, dataType);
    }
}

function setTooltip(data, rootTip, displayName) {
    if (data.name != undefined) {
        d3.selectAll(rootTip + '_row_tip')
            .html(function () {
                var symName = displayName + ': ' + data.name;
                var fullHtml = `<p>${symName}</p><p>${data.description}</p>`;
                return fullHtml;
            });
    }
}

function getMouseOver(rootTip, displayName, dataType) {
    // not sure if this is necessary
    if (d3.select(rootTip + '_row_tip').classed(displayName)) {
        getRequest(rootTip, displayName, dataType);
    }
}

function getRequest(rootTip, displayName, dataType) {
    const params = $.param({
        'data_type': dataType,
        'display_name': displayName
    });
    const url = baseUrl + '?' + params;
    $.get(url, function (data) {
        // save data for repeated use
        seenData[displayName] = {}
        seenData[displayName].name = data.name;
        seenData[displayName].description = data.description;
        setTooltip(data, rootTip, displayName);
        return data;
    });
}

function tileTipCallback(tile_data) {
    var row_name = tile_data.row_name;
    var col_name = tile_data.col_name;
    console.log(`tile_tip_callback ${row_name} ${col_name}`);
}

function colTipCallback(col_data) {
    var col_name = col_data.name;
    console.log(`col_tip_callback ${col_name}`);
}

function dendroCallback(instSelection) {
    var instRc;
    var instData = instSelection.__data__;
    // TODO: buggy modal dialog!!
    // toggle enrichr export section
    // if (instData.instRc === 'row') {
    //     d3.select('.enrichr_export_section')
    //         .style('display', 'block');
    // } else {
    //     d3.select('.enrichr_export_section')
    //         .style('display', 'none');
    // }
}

function matrixUpdateCallback(cgm) {
    console.log('matrix_update_callback');
}

// Note: clustergrammer/dendrogram/run_dendro_filter.js has been modified to call this method
function dendroFilterCallback(cgm) {
    console.log('dendro_filter_callback');

    // get the selections in the clustergrammer for each table type
    const tableName = cgm.tableName;
    const nodeNames = deepCopy(this.network_data.row_nodes_names);

    // save into the global app state, and notify other observers that we've made a clustergrammer selection
    console.log('Notifying clustergrammer update');
    const state = cgm.state;
    state.cgmLastClickedName = tableName;

    // convert node name to constraint key
    state.cgmSelections = nodeNames.map(d => state.displayNameToConstraintKey[tableName][d]);

    // notify other observers
    state.notifyClustergrammerUpdate();
}

export default clustergrammer_setup;