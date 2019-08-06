import Observable from './Observable';
import {observable, computed, autorun, action} from 'mobx';
import {HEATMAP_CLICKED_EVENT} from "../common";

class ClustergrammerStore extends Observable {

    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    @observable cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    constructor(rootStore) {
        super();
        this.rootStore = rootStore;
        autorun(() => {
            const data = {
                'cgmLastClickedName': this.cgmLastClickedName,
                'cgmSelections': this.cgmSelections
            }
            console.log('%c ClustergrammerStore autorun ', 'background: #000; color: #c5f9f0', data);
            this.notifyUpdate(data);
        });
    }

    notifyUpdate(data) {
        this.fire(HEATMAP_CLICKED_EVENT, data)
    }

}

export default ClustergrammerStore;