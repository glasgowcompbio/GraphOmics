import Observable from './Observable';
import {observable, computed, autorun, action} from 'mobx';
import {HEATMAP_CLICKED_EVENT, LAST_CLICKED_CLUSTERGRAMMER, LAST_CLICKED_FIRDI} from "../common";

class ClustergrammerStore extends Observable {

    // public fields
    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    cgmData = {}; // initialised in explore_data.js
    clustergrammers = {}; // all the clustergrammer objects
    newNodes = {}; // updated new nodes for each clustergrammer
    updated = {}; // flag to tell if we need to redraw heatmap
    seenData = {}; // tooltip data caching during mouseover

    // reactive fields
    @observable cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    constructor(rootStore) {
        super();
        this.rootStore = rootStore;
        autorun(() => {
            let totalSelected = 0;
            if (this.cgmSelections) {
                totalSelected = this.cgmSelections.length;
            }
            const data = {
                'cgmLastClickedName': this.cgmLastClickedName,
                'cgmSelections': this.cgmSelections,
                'totalSelected': totalSelected,
                'queryResult': this.rootStore.firdiStore.queryResult
            }
            console.log('%c ClustergrammerStore autorun ', 'background: #000; color: #c5f9f0', data);
            this.notifyUpdate(data);
        });
    }

    @action.bound
    addCgmSelections(nodeNames, tableName) {
        this.cgmLastClickedName = tableName;
        // convert node name to constraint key
        this.cgmSelections = nodeNames.map(d => this.rootStore.firdiStore.displayNameToConstraintKey[tableName][d]);
        // reset firdi state and create new selections
        this.rootStore.firdiStore.addConstraintsByPkValues(this.cgmLastClickedName, this.cgmSelections);
    }

    notifyUpdate(data) {
        // if (this.rootStore.lastClicked == LAST_CLICKED_CLUSTERGRAMMER) {
            this.fire(HEATMAP_CLICKED_EVENT, data);
        // }
    }

}

export default ClustergrammerStore;