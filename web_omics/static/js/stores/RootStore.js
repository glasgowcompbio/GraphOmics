import FirdiStore from "./FirdiStore";
import ClustergrammerStore from "./ClustergrammerStore";

class RootStore {

    firdiStore = undefined;
    cgmStore = undefined;

    lastClicked = undefined;
    groupId = undefined;
    groupName = undefined;
    observedEntities = {};

    constructor(tablesInfo, tableFields) {
        this.firdiStore = new FirdiStore(this, tablesInfo, tableFields);
        this.cgmStore = new ClustergrammerStore(this);
    }
}

export default RootStore;