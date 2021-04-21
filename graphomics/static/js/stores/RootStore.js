import FirdiStore from './FirdiStore';
import ClustergrammerStore from './ClustergrammerStore';
import GroupStore from './GroupStore';

class RootStore {

    firdiStore = undefined;
    cgmStore = undefined;
    groupStore = undefined;

    // last clicked UI element
    lastClicked = undefined;

    // last clicked Firdi table name
    lastClickedTableName = undefined;

    selectAllToggles = {};

    constructor(tablesInfo, tableFields) {
        this.firdiStore = new FirdiStore(this, tablesInfo, tableFields);
        this.cgmStore = new ClustergrammerStore(this);
        this.groupStore = new GroupStore(this);
    }
}

export default RootStore;