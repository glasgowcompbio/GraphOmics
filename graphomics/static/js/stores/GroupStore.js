import Observable from './Observable';
import {action, autorun, computed, observable} from 'mobx';
import {GROUP_UPDATED_EVENT} from "../common";


class GroupStore extends Observable {

    @observable groupId = null;
    @observable groupName = null;
    @observable groupDesc = null;
    @observable timestamp = null;

    constructor(rootStore) {
        super();
        this.rootStore = rootStore;

        autorun(() => {
            const data = {
                groupId: this.groupId,
                groupName: this.groupName,
                groupDesc: this.groupDesc,
                timestamp: this.timestamp,
                observedEntities: this.observedEntities,
                numObservedEntities: this.numObservedEntities,
                totalObservedEntities: this.totalObservedEntities,
            };
            console.log('%c GroupStore autorun ', 'background: #222; color: #FF69B4', data);
            this.notifyUpdate(data);
        });
    }

    @computed get observedEntities() {
        const observedEntities = {};
        const queryResult = this.rootStore.firdiStore.queryResult;
        observedEntities['genes'] = this.getObservedEntities(queryResult.genes_table);
        observedEntities['proteins'] = this.getObservedEntities(queryResult.proteins_table);
        observedEntities['compounds'] = this.getObservedEntities(queryResult.compounds_table);
        observedEntities['reactions'] = this.getObservedEntities(queryResult.reactions_table);
        observedEntities['pathways'] = this.getObservedEntities(queryResult.pathways_table);
        return observedEntities;
    }

    @computed get numObservedEntities() {
        const observedEntities = this.observedEntities;
        const numEntities = {};
        Object.keys(observedEntities).map(function (key, index) {
            numEntities[key] = observedEntities[key].length;
        });
        return numEntities;
    }

    @computed get totalObservedEntities() {
        const values = Object.values(this.numObservedEntities);
        const total = values.reduce((a, b) => a + b, 0);
        return total;
    }

    @action.bound
    restoreState(data) {
        const newState = JSON.parse(data.state);
        this.rootStore.firdiStore.restoreSelection(newState);
        this.rootStore.groupStore.setGroupInfo(data); // should be done only after we restore the state since these are the observable?
    }

    @action.bound
    setGroupInfo(data) {
        this.groupId = data.groupId;
        this.groupName = data.groupName;
        this.groupDesc = data.groupDesc;
        this.timestamp = data.timestamp
    }

    @action.bound
    reset() {
        this.groupId = null;
        this.groupName = null;
        this.groupDesc = null;
        this.timestamp = null;
    }

    getObservedEntities(result) {
        // count rows where obs is either true (for genes, proteins and compounds) or null (for reactions and pathways)
        return (result.filter(x => (x.obs == true) || (x.obs == null)))
    }

    notifyUpdate(data) {
        this.fire(GROUP_UPDATED_EVENT, data);
    }

}

export default GroupStore;