import {getDisplayName, getConstraintTablesConstraintKeyName} from "./Utils";

class ConstraintsManager {
    constructor(state) {
        this.state = state;
        this.tableIdToIdColumnMap = this.getTableKeysAsSingleObject();
    }

    getTableKeysAsSingleObject() {
        // Get the table name and key used in the WHERE clause in the form tableName: key
        return getConstraintTablesConstraintKeyName(this.state.tablesInfo)
            .map(t => ({[t['tableName']]: t['constraintKeyName']}))
            .reduce((o, v) => Object.assign(o, v), {});
    }

    getId(tableName, rowObject) {
        const idColumn = this.tableIdToIdColumnMap[tableName];
        return rowObject[idColumn];
    }

    addConstraint(tableName, rowData, rowIndex) {
        this.state.numSelected[tableName]++;
        this.state.totalSelected++;
        const idVal = this.getId(tableName, rowData);
        const displayName = getDisplayName(rowData, tableName);
        this.state.selections[tableName].push({
            idVal: idVal,
            rowIndex: rowIndex,
            displayName: displayName
        });
        // ensure that entries are sorted by rowIndex asc
        this.state.selections[tableName].sort((a, b) => a.rowIndex - b.rowIndex);
        this.state.constraints[tableName] = this.selectionToConstraint(tableName);
    }

    removeConstraint(tableName, rowData) {
        this.state.numSelected[tableName]--;
        this.state.totalSelected--;
        const idVal = this.getId(tableName, rowData);
        this.state.selections[tableName] = this.state.selections[tableName].filter(x => x.idVal !== idVal);
        this.state.constraints[tableName] = this.selectionToConstraint(tableName);
    }

    selectionToConstraint(tableName) {
        if (this.state.numSelected[tableName] == 0) {
            return this.state.defaultConstraints[tableName];
        } else {
            return this.state.selections[tableName].map(x => x.idVal);
        }
    }

}

export default ConstraintsManager;