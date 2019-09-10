import {
    deepCopy,
    GROUP_LOADED_EVENT,
    LAST_CLICKED_CLUSTERGRAMMER,
    QUERY_CHANGED_EVENT,
    SELECTION_UPDATE_EVENT
} from "./common";
import Clustergrammer from "./clustergrammer/main";
import check_setup_enrichr from "./enrichrgram";
import filter_network_using_new_nodes from "./clustergrammer/network/filter_network_using_new_nodes";
import update_viz_with_network from "./clustergrammer/update/update_viz_with_network";

class ClustergrammerManager {

    constructor(rootStore, cgmData) {

        this.rootStore = rootStore;
        this.store = rootStore.cgmStore;
        this.store.cgmData = cgmData;
        this.initCgm();

        this.rootStore.firdiStore.on(SELECTION_UPDATE_EVENT, (data) => {
            console.log('Firdi --> Clustergrammer');
            this.handleUpdate(data);
        })
        this.rootStore.firdiStore.on(GROUP_LOADED_EVENT, (data) => {
            console.log('GroupManager --> Clustergrammer');
            this.handleUpdate(data);
        })
        this.rootStore.firdiStore.on(QUERY_CHANGED_EVENT, (data) => {
            console.log('QueryBuilder --> Clustergrammer');
            this.handleUpdate(data);
        })

        // only when the tab is clicked, we refresh the clustergrammers
        const cgmTabId = '#' + cgmData.clustergrammerTab;
        $(cgmTabId).click(this.drawHeatmap.bind(this));

    }

    initCgm() {
        Object.keys(this.store.cgmData).forEach((dataType) => {
            const data = this.store.cgmData[dataType].data;
            const elementId = this.store.cgmData[dataType].elementId;

            if (data == null) { // no data has been returned by the view
                $(elementId).text('No data is available.');
            } else {

                // initialise clustergrammer for each dataType
                $(elementId).text('');
                $(elementId).addClass('heatmap_container');
                const jsonData = JSON.parse(data);
                const rowTipCallback = {
                    'genes': this.getGeneInfo.bind(this),
                    'proteins': this.getProteinInfo.bind(this),
                    'compounds': this.getCompoundInfo.bind(this)
                }
                const about_string = 'Zoom, scroll, and click buttons to interact with the clustergram. <a href="http://amp.pharm.mssm.edu/clustergrammer/help"> <i class="fa fa-question-circle" aria-hidden="true"></i> </a>';
                const args = {
                    root: elementId,
                    network_data: jsonData,
                    about: about_string,
                    row_tip_callback: rowTipCallback[dataType],
                    col_tip_callback: this.colTipCallback.bind(this),
                    tile_tip_callback: this.tileTipCallback.bind(this),
                    dendro_callback: this.dendroCallback.bind(this),
                    matrix_update_callback: this.matrixUpdateCallback.bind(this),
                    dendro_filter_callback: this.dendroFilterCallback.bind(this),
                    sidebar_width: 200
                };
                const cgm = Clustergrammer(args);
                cgm.tableName = this.store.cgmData[dataType].tableName;
                ;

                // save the original, complete set of nodes
                this.store.originalCgmNodes[dataType] = deepCopy(cgm.params.inst_nodes);
                this.store.clustergrammers[dataType] = cgm;
                this.store.updated[dataType] = true;

                // TODO: setup enrichr. Still broken!!
                if (dataType === 'genes') {
                    check_setup_enrichr(cgm);
                }

            }

        });
    }

    handleUpdate(data) {
        Object.keys(this.store.cgmData).forEach((dataType) => {
            const cgm = this.store.clustergrammers[dataType];
            if (cgm) { // loop over all clustergrammers and update it
                const tableName = this.store.cgmData[dataType].tableName;
                const idName = this.store.cgmData[dataType].idName;

                let names = [];
                if (data.queryResult.hasOwnProperty(tableName)) {
                    // populate names based on the last query results for this table
                    const queryResult = data.queryResult[tableName];
                    names = queryResult.map(x => x[idName]);
                } else { // if no last query result for this table, then use the selections for the table
                    const selections = data.selections[tableName];
                    names = selections.map(x => x.displayName);
                }

                const newNodes = this.filterVizUsingNames({'row': names}, cgm);
                this.store.newNodes[dataType] = newNodes;
                this.store.updated[dataType] = false;
            }
        });
        // if last clicked was a clustergrammer, then immediately we want to redraw the heatmap
        if (this.store.rootStore.lastClicked === LAST_CLICKED_CLUSTERGRAMMER) {
            this.drawHeatmap(this.store.cgmLastClickedName); // except for the currently clicked clustergrammer
        }
    }

    drawHeatmap(excludeTableName) {
        Object.keys(this.store.cgmData).forEach((dataType) => {
            if (this.store.clustergrammers.hasOwnProperty(dataType) && !this.store.updated[dataType]) {

                const currentTableName = this.store.cgmData[dataType].tableName;
                if (currentTableName == excludeTableName) {
                    console.log('Not updating clustergrammer ' + dataType);
                } else {
                    console.log('Updating clustergrammer ' + dataType);
                    const cgm = this.store.clustergrammers[dataType];
                    const newNodes = this.store.newNodes[dataType];
                    const newNetworkData = filter_network_using_new_nodes(cgm.config, newNodes);
                    update_viz_with_network(cgm, newNetworkData);

                    // always restore the original nodes
                    // this is needed for selection to work again next time
                    // TODO: feels like this could be better
                    cgm.params.inst_nodes = this.store.originalCgmNodes[dataType];
                    this.store.updated[dataType] = true;
                }

            }
        });
    }

    // similar to the filter_viz_using_names function in clustergrammer, but slightly
    // modified to always restore all originalCgmNodes upon reset
    filterVizUsingNames(names, cgm) {

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

        return new_nodes;
    };

    getGeneInfo(rootTip, rowData) {
        this.getInfo(rootTip, rowData, 'gene');
    }

    getProteinInfo(rootTip, rowData) {
        this.getInfo(rootTip, rowData, 'protein');
    }

    getCompoundInfo(rootTip, rowData) {
        this.getInfo(rootTip, rowData, 'compound');
    }

    getInfo(rootTip, rowData, dataType) {
        let displayName = rowData.name;
        if (displayName.indexOf(' ') > 0) {
            displayName = displayName.split(' ')[0];
        } else if (displayName.indexOf('_') > 0) {
            displayName = displayName.split('_')[0];
        }
        if (_.has(this.store.seenData, displayName)) {
            const cachedData = this.store.seenData[displayName];
            this.setTooltip(cachedData, rootTip, displayName);
        } else {
            setTimeout(this.getMouseOver.bind(this), 250, rootTip, displayName, dataType);
        }
    }

    setTooltip(data, rootTip, displayName) {
        if (data.name != undefined) {
            d3.selectAll(rootTip + '_row_tip')
                .html(function () {
                    var symName = displayName + ': ' + data.name;
                    var fullHtml = `<p>${symName}</p><p>${data.description}</p>`;
                    return fullHtml;
                });
        }
    }

    getMouseOver(rootTip, displayName, dataType) {
        // not sure if this is necessary
        if (d3.select(rootTip + '_row_tip').classed(displayName)) {
            this.getRequest(rootTip, displayName, dataType);
        }
    }

    getRequest(rootTip, displayName, dataType) {
        const params = $.param({
            'data_type': dataType,
            'display_name': displayName
        });
        const url = baseUrl + '?' + params;
        const self = this;
        $.get(url, function (data) {
            // save data for repeated use
            self.store.seenData[displayName] = {}
            self.store.seenData[displayName].name = data.name;
            self.store.seenData[displayName].description = data.description;
            self.setTooltip(data, rootTip, displayName);
            return data;
        });
    }

    tileTipCallback(tile_data) {
        var row_name = tile_data.row_name;
        var col_name = tile_data.col_name;
        // console.log(`tile_tip_callback ${row_name} ${col_name}`);
    }

    colTipCallback(col_data) {
        var col_name = col_data.name;
        // console.log(`col_tip_callback ${col_name}`);
    }

    dendroCallback(instSelection) {
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

    matrixUpdateCallback(cgm) {
        // console.log('matrix_update_callback');
    }

    // Note: clustergrammer/dendrogram/run_dendro_filter.js has been modified to call this method
    dendroFilterCallback(cgm) {
        console.log('dendro_filter_callback');

        // set last clicked UI element
        this.rootStore.lastClicked = LAST_CLICKED_CLUSTERGRAMMER;

        // get the selections in the clustergrammer for each table type
        const tableName = cgm.tableName;
        const nodeNames = cgm.params.network_data.row_nodes_names;

        // save into the global app state, and notify other observers that we've made a clustergrammer selection
        this.store.addCgmSelections(nodeNames, tableName);

        // notify other observers
        // cgmStore.notifyUpdate();
    }

}

export default ClustergrammerManager;