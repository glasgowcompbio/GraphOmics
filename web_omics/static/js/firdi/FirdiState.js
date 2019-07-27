import Observable from "./Observable";
import {CLUSTERGRAMMER_UPDATE_EVENT, deepCopy, FIRDI_UPDATE_EVENT, SELECTION_MANAGER_UPDATE_EVENT} from "../common";
import {getDisplayName, isTableVisible} from "./Utils";

class FirdiState extends Observable {

    constructor(sqlManager, tablesInfo) {
        super();

        this.sqlManager = sqlManager;
        this.tablesInfo = tablesInfo;

        // initialisation
        this.defaultConstraints = this.getDefaultConstraints();
        this.constraints = deepCopy(this.defaultConstraints);
        this.displayNameToConstraintKey = this.getDisplayNameToConstraintKey();
        const emptySelections = this.makeEmptyConstraint();
        const emptyCounts = this.makeEmptyCount();

        // Firdi fields
        this.selections = emptySelections;
        this.numSelected = emptyCounts;
        this.totalSelected = 0;
        this.whereType = null;
        this.selectedIndex = {};
        this.lastQueryResults = {}; // to store last table results in firdi

        // Cgm fields
        this.originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
        this.cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
        this.cgmSelections = null; // to store the selections for the last-clicked clustergrammer
    }

    getDefaultConstraints() {
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = this.getKeys(
                    this.tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
                return constraints;
            }, {});
    }

    getKeys(tablesInfo, tableName, k) {
        // Gets the values of the key used in the table relationship for the SQL IN clause
        const data = tablesInfo
            .filter(isTableVisible)
            .filter(t => t['tableName'] === tableName)
            .map(t => t['tableData'])[0];

        const keys = data
            .map(d => d[k])
            .filter((k, idx, arr) => arr.indexOf(k) === idx);

        return keys;
    }

    getDisplayNameToConstraintKey() {
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = this.getDisplayNameToPk(
                    this.tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
                return constraints;
            }, {});
    }

    getDisplayNameToPk(tablesInfo, tableName, k) {
        // Gets the values of the key used in the table relationship for the SQL IN clause
        const data = tablesInfo
            .filter(isTableVisible)
            .filter(t => t['tableName'] === tableName)
            .map(t => t['tableData'])[0];

        const displayNameToPk = {}
        data.map(d => {
            const displayName = getDisplayName(d, tableName);
            displayNameToPk[displayName] = d[k];
        })
        return displayNameToPk;
    }

    makeEmptyConstraint() {
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = [];
                return constraints;
            }, {});
    }

    makeEmptyCount() {
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = 0;
                return constraints;
            }, {});
    }

    restoreSelection(newState) {
        this.constraints = newState.constraints;
        this.selections = newState.selections;
        this.numSelected = newState.numSelected;
        this.totalSelected = newState.totalSelected;
        this.whereType = newState.whereType;
    }

    reset() {
        this.constraints = deepCopy(this.defaultConstraints);
        this.selections = this.makeEmptyConstraint();
        this.numSelected = this.makeEmptyCount();
        this.totalSelected = 0;
        this.whereType = null;
    }

    notifyFirdiUpdate() {
        this.fire(FIRDI_UPDATE_EVENT, this);
    }

    notifyClustergrammerUpdate() {
        this.fire(CLUSTERGRAMMER_UPDATE_EVENT, this)
    }

    notifySelectionManagerUpdate() {
        this.fire(SELECTION_MANAGER_UPDATE_EVENT, this);
    }

}

export default FirdiState;