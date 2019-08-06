import Observable from './Observable';
import {observable, computed, autorun, action} from 'mobx';
import {CLUSTERGRAMMER_UPDATE_EVENT} from "../common";

class ClustergrammerStore extends Observable {

    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    constructor(rootStore) {
        super();
        this.rootStore = rootStore;
    }

    notifyUpdate() {
        this.fire(CLUSTERGRAMMER_UPDATE_EVENT, this)
    }

}

export default ClustergrammerStore;