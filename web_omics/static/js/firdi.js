import 'datatables.net';
import 'datatables.net-dt/css/jquery.dataTables.css';
import 'datatables.net-buttons';
import 'datatables.net-buttons-dt/css/buttons.dataTables.min.css';
import 'datatables.net-buttons/js/buttons.colVis.js'; // Column visibility
import 'datatables.net-responsive';
import 'datatables.net-responsive-dt/css/responsive.dataTables.min.css';
import 'datatables.net-scroller';
import 'datatables.net-scroller-dt/css/scroller.dataTables.min.css';
import 'datatables.net-select';
import 'datatables.net-select-dt/css/select.dataTables.min.css';

import alasql from 'alasql';

import { isTableVisible, deepCopy, getRowObj, goToPage, blockUI, unblockUI } from './common'

class DataTablesOptionsManager {

    constructor(tablesInfo) {
        const colNames = this.getDataTablesColumns(tablesInfo);
        const dataTablesColumnsSettings = this.convertColumnNamesToDataTablesSettings(colNames);
        const filteredTableInfo = this.uniqueDataFilter(tablesInfo);
        const dataTablesSettings = this.makeDataTablesSettingsObjects(filteredTableInfo, dataTablesColumnsSettings);
        this.initialiseDataTables(dataTablesSettings);
    }

    initialiseDataTables(dataTablesSettingsObjects) {
        dataTablesSettingsObjects.forEach(function (x) {
            $('#' + x['tableName']).DataTable(x['tableSettings']);
        });
        // change button to arrows
        const buttons = $(".buttons-colvis");
        for (let button of buttons) {
            const btn = $(button);
            btn.text('▼');
        }
        $.fx.off = true;
    }

    uniqueDataFilter(tablesInfo) {
        // Gets the distinct entries for the tableData for datatables initialisation
        return tablesInfo.filter(isTableVisible)
            .map(tableInfo => {
                tableInfo['tableData'] = alasql("SELECT DISTINCT " + Object.keys(tableInfo['tableData'][0]).join(", ") + " FROM ?", [tableInfo['tableData']]);
                return tableInfo;
            });
    }

    convertColumnNamesToDataTablesSettings(columnNamesPerTable) {
        // columnNamesPerTable is an array of arrays.
        // Each inner array contains all the column names for one table
        // This function maps each set of column names into an object for the dataTables settings.
        return columnNamesPerTable
            .map(columnNames => columnNames
                .map(columnName => ({
                    'data': columnName,
                    'title': columnName,
                    'name': columnName
                })));
    }

    getDataTablesColumns(tablesInfo) {
        // Gets the column/field names from the tableData of each table in tablesInfo
        // Use column ordering if provided, else get column names from JSON attributes
        return tablesInfo.filter(isTableVisible)
            .map(tableInfo => tableInfo['options']['columnOrder'] || Object.keys(tableInfo['tableData'][0]));
    }

    makeDataTablesSettingsObjects(tablesInfo, dataTablesColumnsSettings) {
        // Combines the table information and columns settings into a dataTables settings object for each table

        return tablesInfo.filter(isTableVisible)
            .map((tableInfo, idx) => (
                {
                    tableName: tableInfo['tableName'],
                    tableSettings: Object.assign(
                        {
                            data: tableInfo['tableData'],
                            columns: dataTablesColumnsSettings[idx],
                            rowId: tableInfo['options']['pk']
                        },
                        tableInfo['otherSettings'] || {}
                    )
                }
            ));
    }

}

class SqlManager {

    constructor(tablesInfo) {
        this.initialiseAlasqlTables(tablesInfo);
        this.firstTable = this.getFirstTable(tablesInfo);
        this.tableRelationships = this.getTableRelationships(tablesInfo);
        this.constraintTableConstraintKeyNames = this.getConstraintTablesConstraintKeyName(tablesInfo);
    }

    initialiseAlasqlTables(tablesInfo) {
        tablesInfo.forEach(function (t) {
            // Create table
            let sql = "CREATE TABLE " + t['tableName'];
            console.log(sql);
            alasql(sql);
            // Create index
            if (t['options']['pk'] !== undefined) {
                sql = "CREATE UNIQUE INDEX tmp ON " + t['tableName'] + "(" + t['options']['pk'] + ")";
                console.log(sql);
                alasql(sql);
            }
            // Add data
            alasql.tables[t['tableName']].data = t['tableData'];
        });
    }

    clearAlasqlTables(tablesInfo) {
        tablesInfo.forEach(function (t) {
            alasql('DELETE FROM ' + t['tableName']);
        });
    }

    addNewData(tablesInfo) {
        tablesInfo.forEach(t => alasql.tables[t['tableName']].data = t['tableData']);
    }

    getConstraintTablesConstraintKeyName(tablesInfo) {
        return tablesInfo
            .filter(isTableVisible)
            .map(t => ({'tableName': t['tableName'], 'constraintKeyName': t['options']['pk']}));
    }

    getFieldNames(tablesInfo) {
        return tablesInfo
            .filter(isTableVisible)
            .map(tableInfo => ({'tableName': tableInfo['tableName'], 'firstDataRow': tableInfo['tableData'][0]}))
            .map(tableData => Object.keys(tableData['firstDataRow'])
                .map(e => tableData['tableName'] + "." + e + " AS " + tableData['tableName'] + "_" + e))
            .reduce((fieldNamesArray, fieldNames) => fieldNamesArray.concat(fieldNames), [])
            .join(", ");
    }

    assembleInnerJoinStatementFromRelationship(relationship) {
        // debugger;
        function parseRelationship(r) {
            if (r['with']) {
                return "INNER JOIN " + r['with'] + " ON " + r['tableName'] + "." + r['using'] + " = " + r['with'] + "." + r['using'] + " ";
            } else {
                return "";
            }
        }

        let rs = undefined;
        if (relationship.constructor === Array) {
            rs = relationship; // an array of multiple relationships
        } else {
            rs = [relationship] // create an array of just one relationship
        }

        // process each relationship to make the final statement
        let innerJoinStatement = "";
        rs.forEach(function (r, i) {
            innerJoinStatement += parseRelationship(r);
        });
        return innerJoinStatement;
    }

    makeSelectClause(tablesInfo) {
        // Join each field into a select clause
        const fieldNames = this.getFieldNames(tablesInfo);
        // put the first table in the from clause
        const selectClause = "SELECT " + fieldNames + " FROM " + this.firstTable;
        return selectClause;
    }

    makeInnerJoinClause() {
        return this.tableRelationships
            .map(this.assembleInnerJoinStatementFromRelationship.bind(this))
            .join(" ");
    }

    getFirstTable(tablesInfo) {
        return tablesInfo[0]['tableName'];
    }

    getRelationship(tableInfo) {
        // debugger;
        function parseRelationship(r) {
            let parsed = {'tableName': tableInfo['tableName'], 'with': r['with'], 'using': r['using']};
            return parsed;
        }

        if (tableInfo['relationship']) {
            if (tableInfo['relationship'].constructor == Array) {
                // relationship is a list of dicts
                return tableInfo['relationship'].map(r => parseRelationship(r));
            } else {
                // relationship is a single dict
                return {
                    'tableName': tableInfo['tableName'],
                    'with': tableInfo['relationship']['with'],
                    'using': tableInfo['relationship']['using']
                }
            }
        } else {
            return {'tableName': tableInfo['tableName']};
        }
        ;
    }

    getTableRelationships(tablesInfo) {
        return tablesInfo
            .map(this.getRelationship);
    }

    getTableKeys() {
        // Returns the table name and the name of the key used in the where clause
        return this.tableRelationships
            .map(t => JSON.stringify({'tableName': t['tableName'], 'tableKey': t['using']}))
            .filter((tk, idx, tka) => tka.indexOf(tk) === idx)
            .map(t => JSON.parse(t));
    }

    makeWhereSubClauses() {
        return this.constraintTableConstraintKeyNames
            .map(t => t['tableName'] + "." + t['constraintKeyName'])
    }

    makeWhereClause(tablesInfo, skipConstraints, whereType) {
        const whereSubClauses = this.makeWhereSubClauses();
        let selectedWhereSubClauses = [];
        whereSubClauses.forEach(function (value, i) {
            if (!skipConstraints[i]) {
                selectedWhereSubClauses.push(whereSubClauses[i] + " IN @(?)");
            }
        });
        const whereSubClauses2 = this.constraintTableConstraintKeyNames
         .map(t => t['tableName'] + "." + whereType + "=TRUE").join(" OR ");

        if (selectedWhereSubClauses.length > 0) {
            const whereSubClauses1 = selectedWhereSubClauses.join(" AND ");
            if (whereType) {
                return "WHERE (" + whereSubClauses1 + ") AND (" + whereSubClauses2 + ")";
            } else {
                return "WHERE " + whereSubClauses1;
            }
        } else {
            if (whereType) {
                return "WHERE " + whereSubClauses2;
            } else {
                return "";
            }
        }
    }

    makeSQLquery(tablesInfo, skipConstraints, whereType) {
        const selectClause = this.makeSelectClause(tablesInfo);
        const innerJoinClause = this.makeInnerJoinClause();
        const whereClause = this.makeWhereClause(tablesInfo, skipConstraints, whereType);

        return [selectClause, innerJoinClause, whereClause].join(" ");
    }

    makeSignificantWhereClause(tablesInfo, whereType) {
        if (whereType) {
            const whereSubClauses = this.constraintTableConstraintKeyNames
                .map(t => t['tableName'] + "." + whereType + "=TRUE");
            const whereClauses = "WHERE " + whereSubClauses.join(" OR ");
            return whereClauses;
        } else {
            return "";
        }
    }

    makeSignificantFilterSQLquery(tablesInfo, whereType) {
        const selectClause = this.makeSelectClause(tablesInfo);
        const innerJoinClause = this.makeInnerJoinClause();
        const whereClause = this.makeSignificantWhereClause(tablesInfo, whereType);

        return [selectClause, innerJoinClause, whereClause].join(" ");
    }

    queryDatabase(tablesInfo, constraints, whereType) {

        const constraintTableNames = this.constraintTableConstraintKeyNames.map(t => t['tableName']);
        const unpackedConstraints = constraintTableNames.map(n => constraints[n]);
        // console.log("unpackedConstraints.length = " + unpackedConstraints.length);
        let skipConstraints = [];
        let selectedConstraints = []
        unpackedConstraints.forEach(function (uc, i) {
            // find myTable matching by name
            let tableName = constraintTableNames[i];
            let myTable = tablesInfo.filter(t => t['tableName'] === tableName)[0];

            // if the where subClause includes ALL the data of that table, then skip it
            let sc = false
            if (uc.length == myTable['tableData'].length) {
                sc = true;
            }
            if (!sc) {
                selectedConstraints.push(uc);
            }
            skipConstraints.push(sc);
            // console.log('%d. skip %s (%s)', i, sc, uc);
        });

        // debugger;
        const sqlQuery = this.makeSQLquery(tablesInfo, skipConstraints, whereType);
        console.log(sqlQuery);
        const compiledSQLQuery = alasql.compile(sqlQuery);

        return compiledSQLQuery(selectedConstraints);
    }

}

class ConstraintsManager {
    constructor(tablesInfo, sqlManager) {
        this.tablesInfo = tablesInfo;
        this.tableKeys = sqlManager.getTableKeys();
        this.sqlManager = sqlManager;
        this.constraintTablesConstraintKeyNames = sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
        this.tableIdToIdColumnMap = this.getTableKeysAsSingleObject();
        this.defaultConstraints = this.getDefaultConstraints();
        this.constraints = this.initConstraints();
        this.selections = this.makeEmptyConstraint();
        this.numSelected = this.makeEmptyCount();
        this.totalSelected = 0;
        this.whereType = null;
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

    getDefaultConstraints() {
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .reduce((constraints, tableInfo) => {
                constraints[tableInfo['tableName']] = this.getKeys(
                    this.tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
                return constraints;
            }, {});
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

    initConstraints() {
        return deepCopy(this.defaultConstraints);
    }

    getTableKeysAsSingleObject() {
        // Get the table name and key used in the WHERE clause in the form tableName: key
        return this.sqlManager.getConstraintTablesConstraintKeyName(this.tablesInfo)
            .map(t => ({[t['tableName']]: t['constraintKeyName']}))
            .reduce((o, v) => Object.assign(o, v), {});
    }

    getId(tableName, rowObject) {
        const idColumn = this.tableIdToIdColumnMap[tableName];
        return rowObject[idColumn];
    }

    addConstraint(tableName, rowData, rowIndex) {
        this.numSelected[tableName]++;
        this.totalSelected++;
        const idVal = this.getId(tableName, rowData);
        this.selections[tableName].push({
            idVal: idVal,
            rowIndex: rowIndex
        });
        // ensure that entries are sorted by rowIndex asc
        this.selections[tableName].sort((a, b) => a.rowIndex - b.rowIndex);
        this.constraints[tableName] = this.selectionToConstraint(tableName);
    }

    removeConstraint(tableName, rowData) {
        this.numSelected[tableName]--;
        this.totalSelected--;
        const idVal = this.getId(tableName, rowData);
        this.selections[tableName] = this.selections[tableName].filter(x => x.idVal !== idVal);
        this.constraints[tableName] = this.selectionToConstraint(tableName);
    }

    selectionToConstraint(tableName) {
        if (this.numSelected[tableName] == 0) {
            return this.defaultConstraints[tableName];
        } else {
            return this.selections[tableName].map(x => x.idVal);
        }
    }

}

class FiRDI {

    constructor(tablesInfo, defaultDataTablesSettings, infoPanelManager) {
        this.tablesInfo = tablesInfo;
        this.originalTablesInfo = deepCopy(tablesInfo);
        this.infoPanelManager = infoPanelManager;

        // Some minimum DataTables settings are required
        const minDataTablesSettings = {
            "dom": "rpt",
            "select": { // Needed for row selection i.e. the user-select event and limiting to selecting one row at a time. Don't change the select settings.
                "items": "row",
                "style": "single"
            },
            "deferRender": true, // needed for speed with large datasets
            "orderClasses": false, // needed for speed with large datasets
            "paging": true // used with deferRender for speed. Paginiation is used explicitly in code elsewhere: it must be left on!
        };


        // set defaults across all tables
        this.defaultDataTablesSettings = Object.assign(minDataTablesSettings, defaultDataTablesSettings || {});
        $.extend(true, $.fn.dataTable.defaults, this.defaultDataTablesSettings);

        this.dataTablesOptionsManager = new DataTablesOptionsManager(this.tablesInfo);
        this.sqlManager = new SqlManager(this.tablesInfo);
        // this.stackManager = new StackManager();
        this.constraintsManager = new ConstraintsManager(this.tablesInfo, this.sqlManager);

        this.tableFieldNames = this.getFieldNames();

        this.dataTablesIds = tablesInfo.filter(isTableVisible).reduce((apis, t) => {
            apis[t['tableName']] = "#" + t['tableName'];
            return apis
        }, {});

        this.initTableClicks();
        this.initTableFilters();
    }

    resetFiRDI() {
        // restore originalTablesInfo
        this.tablesInfo = JSON.parse(JSON.stringify(this.originalTablesInfo));
        this.sqlManager.clearAlasqlTables(this.tablesInfo);
        this.sqlManager.addNewData(this.tablesInfo);
        this.constraintsManager.defaultConstraints = this.constraintsManager.getDefaultConstraints(this.tablesInfo);
        this.constraintsManager.constraints = this.constraintsManager.initConstraints()
        this.constraintsManager.selections = this.constraintsManager.makeEmptyConstraint(this.tablesInfo);
        this.constraintsManager.numSelected = this.constraintsManager.makeEmptyCount(this.tablesInfo);
        this.constraintsManager.totalSelected = 0;

        this.tablesInfo.forEach(t => {
            const tableAPI = $(this.dataTablesIds[t['tableName']]).DataTable();
            tableAPI.clear();
            tableAPI.rows.add(t['tableData']);
            tableAPI.draw();
        });

    }

    initTableClicks() {
        const dataTablesIdsKeys = Object.keys(this.dataTablesIds);
        dataTablesIdsKeys.forEach(id => $(this.dataTablesIds[id]).DataTable().on('user-select', this.trClickHandler.bind(this)));
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

    prefixQuery(tableFieldNames, dataSource) {
        const tableName = tableFieldNames['tableName'];
        const prefix = tableName + '_';
        const fieldNames = tableFieldNames['fieldNames'].map(x => prefix + x);

        const sqlStatement = "SELECT DISTINCT " + fieldNames.join(", ") + " FROM ?";
        const temp = alasql(sqlStatement, [dataSource]);

        temp.map(x => { // for each row in the sql results
            Object.keys(x).map(key => { // rename the properties to remove the table name in front
                const newkey = key.replace(prefix, '');
                x[newkey] = x[key];
                delete(x[key]);
            });
        });

        return temp;
    }

    updateTables() {
        if (this.constraintsManager.totalSelected > 0) {

            console.log('queryResult');
            const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.constraintsManager.constraints,
                this.constraintsManager.whereType);

            for (let i = 0; i < this.tableFieldNames.length; i++) { // update all the tables
                const tableFieldName = this.tableFieldNames[i];
                const tableName = tableFieldName['tableName'];
                if (this.constraintsManager.numSelected[tableName] > 0) { // if table already has some selection
                    // don't change table content, just change the selection style
                    this.addSelectionStyle(tableName);
                } else {
                    // otherwise update table content and selection style
                    this.updateTable(tableFieldName, queryResult);
                    this.addSelectionStyle(tableName);
                }
            }

        } else {
            this.resetTables();
        }
    }

    updateTable(tableFieldName, queryResult) {
        const tableName = tableFieldName['tableName'];
        const data = this.prefixQuery(tableFieldName, queryResult);
        $(this.dataTablesIds[tableName]).DataTable().clear();
        $(this.dataTablesIds[tableName]).DataTable().rows.add(data);
        $(this.dataTablesIds[tableName]).DataTable().draw();
    }

    addSelectionStyle(tableName) {
        const tableAPI = $(this.dataTablesIds[tableName]).DataTable();
        const tableSelections = this.constraintsManager.selections[tableName];

        if (tableSelections.length > 0) {
            // Find page that contains the row of interest
            // Go to it
            // add selection to that row.
            for (let i = 0; i < tableSelections.length; i++) {
                const selection = tableSelections[i];
                const found = getRowObj(tableName, selection.idVal);
                if (found) {
                    goToPage(found);
                    const node = found.node;
                    if (!node.hasClass('selected')) {
                        node.addClass('selected');
                    }
                }
            }
        }
    }

    removeSelectionStyle(targetTr) {
        if (targetTr.hasClass('selected')) {
            targetTr.removeClass('selected');
        }
    }

    resetTable(tableFieldNames, dataForTables, queryResult) {
        const tableName = tableFieldNames['tableName'];
        dataForTables[tableName] = this.prefixQuery(tableFieldNames, queryResult);

        const tableAPI = $(this.dataTablesIds[tableName]).DataTable();
        tableAPI.clear();
        tableAPI.rows.add(dataForTables[tableName]);
        tableAPI.draw();
        tableAPI.page(0).draw('page');
    }

    resetTables() {
        let dataForTables = this.constraintsManager.makeEmptyConstraint(this.tablesInfo);
        console.log('resetTable');
        const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.constraintsManager.constraints,
            this.constraintsManager.whereType);
        this.tableFieldNames.forEach(tableFieldNames => this.resetTable(tableFieldNames, dataForTables, queryResult));
    }

    trClickHandler(e, dt, type, cell, originalEvent) {
        e.preventDefault();
        blockUI();
        const obj = this;
        window.setTimeout(function() {

            // clear search result
            $('#global_filter').val('');
            $.fn.dataTable.tables({api: true}).search('');

            // find the selected row
            const tableName = e.currentTarget.id;
            const tableAPI = $(obj.dataTablesIds[tableName]).DataTable();
            const targetTr = $(originalEvent.target).closest('tr');
            const row = tableAPI.row(targetTr);
            const rowData = row.data();
            const rowIndex = tableAPI.rows()[0].indexOf(row.index());
            const anyRowSelected = tableAPI.rows('.selected').any();

            obj.trClickHandlerUpdate(tableName, targetTr, rowData, rowIndex, anyRowSelected);
            unblockUI();
            if (obj.infoPanelManager) { // update the related info panel for this table, if any
                if (obj.constraintsManager.numSelected[tableName] > 0) {

                    // assume that entries in the array is always in sorted order by their row index
                    // (the sorting is done upon insertion in addConstraint)
                    const selections = deepCopy(obj.constraintsManager.selections[tableName]);

                    // find the pk value that has been clicked and its index in selections
                    const selectedValue = obj.infoPanelManager.getPkValue(rowData, tableName);
                    let selectedIndex = selections.map(x => x.idVal).indexOf(selectedValue);
                    let updatePage = true;
                    if (selectedIndex == -1 && selections.length > 0) { // if the current row has been unclicked
                        // update the bottom panel to show the first item in selections,
                        // but don't change the current page in the datatable
                        selectedIndex = 0;
                        updatePage = false;
                    }
                    obj.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);

                    // store for use in buttons etc later
                    obj.infoPanelManager.selections[tableName] = selections;
                    obj.infoPanelManager.selectedIndex[tableName] = selectedIndex;

                } else {
                    obj.infoPanelManager.clearInfoPane(tableName);
                }
            }
        }, 1); // we need a small delay to allow blockUI to be rendered correctly
    }

    trClickHandlerUpdate(tableName, targetTr, rowData, rowIndex, anyRowSelected) {
        // if some rows are already selected in the table
        if (anyRowSelected) {
            // if the current row is already selected then unselect it
            if (targetTr.hasClass('selected')) {
                this.constraintsManager.removeConstraint(tableName, rowData);
                this.removeSelectionStyle(targetTr);
                this.updateTables();
            } else { // otherwise select the current row
                this.constraintsManager.addConstraint(tableName, rowData, rowIndex);
                this.updateTables();
            }
        } else { // otherwise just select this row
            this.constraintsManager.addConstraint(tableName, rowData, rowIndex);
            this.updateTables();
        }
    }

    initTableFilters() {
        const currObj = this;
        const filterTableFunc = function() {
            let filterColumnName = undefined;
            if (this.value == 'all') {
                filterColumnName = 'significant_all';
            } else if (this.value == 'any') {
                filterColumnName = 'significant_any';
            }
            Object.keys(currObj.constraintsManager.constraints).forEach(x => {
                currObj.constraintsManager.constraints[x] = []
            });
            currObj.resetTables();
            const sqlQuery = currObj.sqlManager.makeSignificantFilterSQLquery(currObj.tablesInfo, filterColumnName);
            const queryResult = alasql(sqlQuery);
            currObj.tableFieldNames.forEach(tableFieldName => currObj.updateTable(tableFieldName, queryResult));
            currObj.constraintsManager.constraints = currObj.constraintsManager.initConstraints();
            currObj.constraintsManager.whereType = filterColumnName;
            currObj.selections = currObj.constraintsManager.makeEmptyConstraint();
            currObj.numSelected = currObj.constraintsManager.makeEmptyCount();
            currObj.totalSelected = 0;
        };
        $('input[type=radio][name=inlineRadioOptions]').change(filterTableFunc);
    }

}

export default FiRDI;