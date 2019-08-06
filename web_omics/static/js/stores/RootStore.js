import FirdiStore from "./FirdiStore";
import ClustergrammerStore from "./ClustergrammerStore";

class RootStore {

    firdiStore = undefined;
    cgmStore = undefined;

    constructor(tablesInfo, tableFields) {
        this.firdiStore = new FirdiStore(this, tablesInfo, tableFields);
        this.cgmStore = new ClustergrammerStore(this);
    }
}

export default RootStore;