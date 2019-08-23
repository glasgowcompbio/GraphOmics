import Observable from './Observable';
import {observable, computed, autorun, action} from 'mobx';
import {HEATMAP_CLICKED_EVENT, LAST_CLICKED_CLUSTERGRAMMER, LAST_CLICKED_FIRDI} from "../common";

class ClustergrammerStore extends Observable {

    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    @observable cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    clustergrammers = {}; // all the clustergrammer objects
    newNetworkData = {}; // updated network data for each clustergrammer

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
                'totalSelected': totalSelected
            }
            console.log('%c ClustergrammerStore autorun ', 'background: #000; color: #c5f9f0', data);
            this.notifyUpdate(data);
        });
    }

    notifyUpdate(data) {
        if (this.rootStore.lastClicked == LAST_CLICKED_CLUSTERGRAMMER) {
            this.fire(HEATMAP_CLICKED_EVENT, data);
        }
    }

}

export default ClustergrammerStore;