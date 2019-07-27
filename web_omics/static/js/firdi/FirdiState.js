import Observable from './Observable';
import {CLUSTERGRAMMER_UPDATE_EVENT, deepCopy, FIRDI_UPDATE_EVENT, SELECTION_MANAGER_UPDATE_EVENT} from "../common";
import {getConstraintTablesConstraintKeyName, getDisplayName, isTableVisible} from "./Utils";

class FirdiState extends Observable {

    // public fields
    constraints = undefined;
    selections = undefined;
    numSelected = undefined;
    totalSelected = 0;
    whereType = null;
    selectedIndex = {};
    lastQueryResults = {}  // to store last table results in firdi

    // Cgm fields
    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    // private fields
    #defaultConstraints = undefined;
    #tablesInfo = undefined;
    #tableFields = undefined;
    #displayNameToConstraintKey = undefined;

    constructor(tablesInfo, tableFields) {
        super();

        this.#tablesInfo = tablesInfo;
        this.#tableFields = tableFields;
        this.#defaultConstraints = this.createDefaultConstraints();
        this.#displayNameToConstraintKey = this.getDisplayNameToConstraintKey();

        // Firdi fields
        this.constraints = deepCopy(this.defaultConstraints);
        this.selections = this.makeEmptyConstraint();
        this.numSelected = this.makeEmptyCount();

    }

    // getters

    get defaultConstraints() {
        return this.#defaultConstraints;
    }

    get tablesInfo() {
        return this.#tablesInfo;
    }

    get tableFields() {
        return this.#tableFields;
    }

    get displayNameToConstraintKey() {
        return this.#displayNameToConstraintKey;
    }

    // public methods

    getDataTablesIds() {
        return this.tablesInfo.filter(isTableVisible).reduce((apis, t) => {
            apis[t['tableName']] = "#" + t['tableName'];
            return apis
        }, {});
    }

    getFieldNames() {
        // Gets the field names for each visible table
        return this.tablesInfo
            .filter(isTableVisible)
            .map(tableInfo => ({
                'tableName': tableInfo['tableName'],
                'fieldNames': Object.keys(tableInfo['tableData'][0])
            }));
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

    // TODO: should be made private methods

    createDefaultConstraints() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
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
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
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
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = [];
                return constraints;
            }, {});
    }

    makeEmptyCount() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = 0;
                return constraints;
            }, {});
    }

}

export default FirdiState;