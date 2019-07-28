import Observable from './Observable';
import {CLUSTERGRAMMER_UPDATE_EVENT, deepCopy, FIRDI_UPDATE_EVENT, SELECTION_MANAGER_UPDATE_EVENT} from "../common";
import {getConstraintTablesConstraintKeyName, getDisplayName, isTableVisible} from "./Utils";
import {observable, computed, autorun, action} from 'mobx';


class FirdiState extends Observable {

    // public fields
    @observable tablesInfo = undefined;
    @observable tableFields = undefined;
    @observable selections = undefined;
    @observable whereType = null;
    @observable selectedIndex = {};

    // computed properties
    lastQueryResults = {}  // to store last table results in firdi

    // Cgm fields
    originalCgmNodes = {}; // to restore original cgm nodes when we reset the view in clustergrammer
    cgmLastClickedName = null; // to store the table name for the last-clicked clustergrammer
    cgmSelections = null; // to store the selections for the last-clicked clustergrammer

    constructor(tablesInfo, tableFields) {
        super();
        this.tablesInfo = tablesInfo;
        this.tableFields = tableFields;
        this.selections = this.emptySelections();
    }

    // computed properties

    @computed get defaultConstraints() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = this.getKeys(
                    this.tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
                return constraints;
            }, {});
    }

    @computed get dataTablesIds() {
        return this.tablesInfo.filter(isTableVisible).reduce((apis, t) => {
            apis[t['tableName']] = "#" + t['tableName'];
            return apis
        }, {});
    }

    @computed get fieldNames() {
        // Gets the field names for each visible table
        return this.tablesInfo
            .filter(isTableVisible)
            .map(tableInfo => ({
                'tableName': tableInfo['tableName'],
                'fieldNames': Object.keys(tableInfo['tableData'][0])
            }));
    }

    @computed get displayNameToConstraintKey() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = this.getDisplayNameToPk(
                    this.tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
                return constraints;
            }, {});
    }

    @computed get tableIdToIdColumnMap() {
        // Get the table name and key used in the WHERE clause in the form tableName: key
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .map(t => ({[t['tableName']]: t['constraintKeyName']}))
            .reduce((o, v) => Object.assign(o, v), {});
    }

    @computed get numSelected() {
        return this.countNumSelected();
    }

    @computed get totalSelected() {
        const values = Object.values(this.numSelected);
        const total = values.reduce((a, b) => a + b, 0);
        return total;
    }

    @computed get constraints() {
        return this.makeConstraints();
    }

    // actions

    @action.bound
    addConstraint(tableName, rowData, rowIndex) {
        const idVal = this.getId(tableName, rowData);
        const displayName = getDisplayName(rowData, tableName);
        this.selections[tableName].push({
            idVal: idVal,
            rowIndex: rowIndex,
            displayName: displayName
        });

        // ensure that entries are sorted by rowIndex asc
        // this.selections[tableName].sort((a, b) => a.rowIndex - b.rowIndex);

        // same as above, but using a special syntax for mobx
        const observableArray = this.selections[tableName];
        observableArray.replace(observableArray.slice().sort((a, b) => a.rowIndex - b.rowIndex));
    }

    @action.bound
    removeConstraint(tableName, rowData) {
        const idVal = this.getId(tableName, rowData);
        this.selections[tableName] = this.selections[tableName].filter(x => x.idVal !== idVal);
    }

    @action.bound
    restoreSelection(newState) {
        this.selections = newState.selections;
        this.whereType = newState.whereType;
    }

    @action.bound
    reset() {
        this.selections = this.makeEmptyConstraint();
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

    getId(tableName, rowObject) {
        const idColumn = this.tableIdToIdColumnMap[tableName];
        return rowObject[idColumn];
    }

    countNumSelected() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((results, tableInfo) => {
                const tname = tableInfo['tableName'];
                results[tname] = this.selections[tname].length;
                return results;
            }, {});
    }

    emptySelections() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((results, tableInfo) => {
                const tname = tableInfo['tableName'];
                results[tname] = [];
                return results;
            }, {});
    }

    makeConstraints() {
        return getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((results, tableInfo) => {
                const tname = tableInfo['tableName'];
                results[tname] = this.selectionToConstraint(tname);
                return results;
            }, {});
    }

    selectionToConstraint(tableName) {
        if (this.numSelected[tableName] == 0) {
            return this.defaultConstraints[tableName];
        } else {
            return this.selections[tableName].map(x => x.idVal);
        }
    }

}

export default FirdiState;