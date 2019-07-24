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

import { isTableVisible, deepCopy, getPkValue, getPkCol, getDisplayName, getDisplayNameCol, getRowObj, getIndexToPos, goToPage, blockUI,
    unblockUI, FIRDI_UPDATE_EVENT, CLUSTERGRAMMER_UPDATE_EVENT, SELECTION_MANAGER_UPDATE_EVENT } from './common'
import InfoPanesManager from './InfoPanesManager';
import Observable from './Observable'

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

    makeSQLquery(tablesInfo, skipConstraints, whereType) {
        const selectClause = this.makeSelectClause(tablesInfo);
        const innerJoinClause = this.makeInnerJoinClause();
        const whereClause = this.makeWhereClause(tablesInfo, skipConstraints, whereType);
        return [selectClause, innerJoinClause, whereClause].join(" ");
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

    makeWhereSubClauses() {
        return this.constraintTableConstraintKeyNames
            .map(t => t['tableName'] + "." + t['constraintKeyName'])
    }

    makeSignificantFilterSQLquery(tablesInfo, whereType) {
        const selectClause = this.makeSelectClause(tablesInfo);
        const innerJoinClause = this.makeInnerJoinClause();
        const whereClause = this.makeSignificantWhereClause(tablesInfo, whereType);
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
            if (uc.length == 0 || uc.length == myTable['tableData'].length) {
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
    constructor(tablesInfo, sqlManager, state) {
        this.tablesInfo = tablesInfo;
        this.tableKeys = sqlManager.getTableKeys();
        this.sqlManager = sqlManager;
        this.tableIdToIdColumnMap = this.getTableKeysAsSingleObject();
        this.state = state;
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

class FiRDIState extends Observable {

    constructor(defaultConstraints, displayNameToConstraintKey, initConstraints, emptySelections, emptyCounts) {
        super();

        // Firdi fields
        this.defaultConstraints = defaultConstraints;
        this.displayNameToConstraintKey = displayNameToConstraintKey;
        this.constraints = initConstraints;
        this.selections = emptySelections;
        this.numSelected = emptyCounts;
        this.totalSelected = 0;
        this.whereType = null;
        this.selectedIndex = {};

        // observer pattern
        this.lastQueryResults = {}; // to store firdi updates
        this.originalCgmNodes = {}; // to restore original cgm nodes when we reset the view
        this.cgmLastClickedName = null; // to store the table name linked to a last-clicked clustergrammer
        this.cgmSelections = null; // to store the selections linked to a last-clicked clustergrammer
    }

    restoreSelection(newState) {
        this.constraints = newState.constraints;
        this.selections = newState.selections;
        this.numSelected = newState.numSelected;
        this.totalSelected = newState.totalSelected;
        this.whereType = newState.whereType;
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

class FiRDI {

    constructor(tablesInfo, defaultDataTablesSettings, columnsToHidePerTable, tableFields, viewNames) {
        this.tablesInfo = tablesInfo;
        this.originalTablesInfo = deepCopy(tablesInfo);

        // Some minimum DataTables settings are required
        // set defaults across all tables
        const minDataTablesSettings = this.getMinTablesSettings();
        const dataTablesSettings = Object.assign(minDataTablesSettings, defaultDataTablesSettings || {});
        $.extend(true, $.fn.dataTable.defaults, dataTablesSettings);

        this.dataTablesOptionsManager = new DataTablesOptionsManager(this.tablesInfo);
        this.sqlManager = new SqlManager(this.tablesInfo);
        this.state = this.getFirdiState();
        this.state.on(CLUSTERGRAMMER_UPDATE_EVENT, (data) => {
            console.log('firdi receives update from clustergrammer');
            console.log(data);
            const tableName = data.cgmLastClickedName;
            const selectedPkValues = data.selections[tableName];
            this.resetFiRDI(true);
            this.multipleTrClickHandlerUpdate(tableName, selectedPkValues);
        })
        this.state.on(SELECTION_MANAGER_UPDATE_EVENT, (data) => {
            console.log('firdi receives update from selection manager');
            console.log(data);
            this.resetFiRDI(false);
            this.updateFiRDIForLoadSelection();
        })

        this.constraintsManager = new ConstraintsManager(this.tablesInfo, this.sqlManager, this.state);
        this.infoPanelManager = new InfoPanesManager(viewNames, this.state);
        this.tableFieldNames = this.getFieldNames();
        this.dataTablesIds = this.getDataTableIds(tablesInfo);

        this.initTableClicks();
        this.initHideColumnClicks(columnsToHidePerTable);
        this.initSignificantFilters();
        this.initSearchBox();
        this.hideColumns(columnsToHidePerTable, tableFields);
    }

    getFirdiState() {
        const defaultConstraints = this.getDefaultConstraints();
        const displayNameToConstraintKey = this.getDisplayNameToConstraintKey()
        const initConstraints = deepCopy(defaultConstraints);
        const emptySelections = this.makeEmptyConstraint();
        const emptyCounts = this.makeEmptyCount();
        const state = new FiRDIState(defaultConstraints, displayNameToConstraintKey, initConstraints,
            emptySelections, emptyCounts);
        return state;
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

    initConstraints() {
        return deepCopy(this.defaultConstraints);
    }

    getMinTablesSettings() {
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
        return minDataTablesSettings;
    }

    getDataTableIds(tablesInfo) {
        return tablesInfo.filter(isTableVisible).reduce((apis, t) => {
            apis[t['tableName']] = "#" + t['tableName'];
            return apis
        }, {});
    }

    initTableClicks() {
        const dataTablesIdsKeys = Object.keys(this.dataTablesIds);
        dataTablesIdsKeys.forEach(id => $(this.dataTablesIds[id]).DataTable().on('user-select', this.trClickHandler.bind(this)));
    }

    initHideColumnClicks(columnsToHidePerTable) {
        $('#showDataCheck').change(function () {
            let visible = false;
            if (this.checked) {
                visible = true;
            }
            columnsToHidePerTable.forEach(function (tableInfo) {
                const tableAPI = $('#' + tableInfo['tableName']).DataTable();
                if (tableInfo['colData']) {
                    tableAPI
                        .columns(tableInfo['colData'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                        .visible(visible);
                }
            });
        });
    }

    initSignificantFilters() {
        const currObj = this;
        const filterTableFunc = function() {
            blockUI();
            const selectedValue = this.value;
            window.setTimeout(function() {
                currObj.resetFiRDI(true);
                let filterColumnName = selectedValue.length > 0 ? selectedValue : null;
                currObj.state.whereType = filterColumnName;
                currObj.updateTables();
                currObj.state.notifyFirdiUpdate();
                unblockUI();
            }, 1); // we need a small delay to allow blockUI to be rendered correctly
        };
        $('input[type=radio][name=inlineRadioOptions]').change(filterTableFunc);
    }

    initSearchBox() {
        $('#global_filter').on('keyup click', function () {
            const val = $('#global_filter').val();
            $.fn.dataTable.tables({api: true}).search(val).draw();
        });
    }

    hideColumns(columnsToHidePerTable, tableFields) {
        columnsToHidePerTable.forEach(function (tableInfo) {
            const tableAPI = $('#' + tableInfo['tableName']).DataTable();
            // get all column names containing the word 'padj' or 'species' to hide as well
            const colNames = tableAPI.settings()[0].aoColumns.map(x => x.sName);
            const filtered = colNames.filter(x => x.indexOf('padj') > -1 || x.indexOf('species') > -1);
            tableInfo['columnNames'] = tableInfo['columnNames'].concat(filtered);
            // get all columns names for the raw data and hide them as well
            const colData = tableFields[tableInfo['tableName']];
            if (colData) {
                tableInfo['colData'] = colData;
                tableAPI
                    .columns(tableInfo['colData'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                    .visible(false);
            }
            // do the hiding here
            tableAPI
                .columns(tableInfo['columnNames'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
                .visible(false);

        });
    }

    resetFiRDI(resetState) {
        // restore originalTablesInfo
        this.tablesInfo = JSON.parse(JSON.stringify(this.originalTablesInfo));
        this.sqlManager.clearAlasqlTables(this.tablesInfo);
        this.sqlManager.addNewData(this.tablesInfo);
        this.tablesInfo.forEach(t => {
            const tableName = t['tableName'];
            const tableAPI = $(this.dataTablesIds[tableName]).DataTable();
            tableAPI.clear();
            tableAPI.rows.add(t['tableData']);
            tableAPI.draw();
        });
        // reset state
        if (resetState) {
            this.state.defaultConstraints = this.getDefaultConstraints();
            this.state.constraints = deepCopy(this.state.defaultConstraints);
            this.state.selections = this.makeEmptyConstraint();
            this.state.numSelected = this.makeEmptyCount();
            this.state.totalSelected = 0;
            this.state.whereType = null;
        }
        // reset info panels
        this.infoPanelManager.clearAllInfoPanels();
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
        console.log('queryResult');
        const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.state.constraints,
            this.state.whereType);

        for (let i = 0; i < this.tableFieldNames.length; i++) { // update all the tables
            const tableFieldName = this.tableFieldNames[i];
            const tableName = tableFieldName['tableName'];
            this.updateSingleTable(tableFieldName, queryResult);
        }
    }

    updateTablesForClickUpdate() {
        if (this.state.totalSelected > 0) {

            console.log('queryResult');
            const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.state.constraints,
                this.state.whereType);

            for (let i = 0; i < this.tableFieldNames.length; i++) { // update all the tables
                const tableFieldName = this.tableFieldNames[i];
                const tableName = tableFieldName['tableName'];
                if (this.state.numSelected[tableName] > 0) { // if table already has some selection
                    // don't change table content, just change the selection style
                    this.addSelectionStyle(tableName);
                } else {
                    // otherwise update table content and selection style
                    this.updateSingleTable(tableFieldName, queryResult);
                    this.addSelectionStyle(tableName);
                }
            }

        } else {
            this.resetTables();
        }
        this.state.notifyFirdiUpdate();
    }

    updateSingleTable(tableFieldName, queryResult) {
        const tableName = tableFieldName['tableName'];
        const data = this.prefixQuery(tableFieldName, queryResult);
        $(this.dataTablesIds[tableName]).DataTable().clear();
        $(this.dataTablesIds[tableName]).DataTable().rows.add(data);
        $(this.dataTablesIds[tableName]).DataTable().draw();
        // store the last query results for updates in other views later
        this.state.lastQueryResults[tableName] = data;
    }

    addSelectionStyle(tableName) {
        const tableAPI = $(this.dataTablesIds[tableName]).DataTable();
        const tableSelections = this.state.selections[tableName];

        if (tableSelections.length > 0) {

            // redraw all pages .. slow!!
            // for (let i = 0; i < tableAPI.page.info().pages; i++) {
            //     tableAPI.page(i).draw('page');
            // }

            // Find page that contains the row of interest
            // Go to it
            // add selection to that row.
            const pages = [];
            for (let i = 0; i < tableSelections.length; i++) {
                const selection = tableSelections[i];
                // const found = getRowObj(tableName, selection.idVal, indexToPos, selection.rowIndex);
                const found = getRowObj(tableName, selection.idVal);
                const rowIndex = found.rowIndex;
                const pageInfo = tableAPI.page.info();
                const thePage = Math.floor(rowIndex / pageInfo['length']);
                pages.push(thePage);
            }

            // draw the page once because of defer_render
            // https://datatables.net/examples/ajax/defer_render.html
            this.drawPages(tableAPI, tableName, pages);

            // add selection styles
            for (let i = 0; i < tableSelections.length; i++) {
                const selection = tableSelections[i];
                // const found = getRowObj(tableName, selection.idVal, indexToPos, selection.rowIndex);
                const found = getRowObj(tableName, selection.idVal);
                const node = found.node;
                if (node.length > 0) {
                    if (!node.hasClass('selected')) {
                        node.addClass('selected');
                    }
                }
            }

            // draw pages again to show the selection styles
            this.drawPages(tableAPI, tableName, pages);
        }
    }

    drawPages(tableAPI, tableName, pages) {
        var uniquePages = Array.from(new Set(pages));
        // console.trace('uniquePages', tableName, uniquePages);
        for (let i = 0; i < uniquePages.length; i++) {
            const thePage = uniquePages[i];
            tableAPI.page(thePage).draw('page');
        }
    }

    removeSelectionStyle(targetTr) {
        if (targetTr.hasClass('selected')) {
            targetTr.removeClass('selected');
        }
    }

    resetTable(tableFieldNames, queryResult) {
        const tableName = tableFieldNames['tableName'];
        const data = this.prefixQuery(tableFieldNames, queryResult);
        const tableAPI = $(this.dataTablesIds[tableName]).DataTable();
        tableAPI.clear();
        tableAPI.rows.add(data);
        tableAPI.draw();
        tableAPI.page(0).draw('page');
        this.state.lastQueryResults[tableName] = data;
    }

    resetTables() {
        console.log('resetTable');
        const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.state.constraints,
            this.state.whereType);
        this.tableFieldNames.forEach(tableFieldNames => this.resetTable(tableFieldNames, queryResult));
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
            // update the related info panel for this table, if any
            if (obj.state.numSelected[tableName] > 0) {

                // assume that entries in the array is always in sorted order by their row index
                // (the sorting is done upon insertion in addConstraint)
                const selections = obj.state.selections[tableName];

                // find the pk value that has been clicked and its index in selections
                const selectedValue = getPkValue(rowData, tableName);
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
                obj.state.selectedIndex[tableName] = selectedIndex;

            } else {
                obj.infoPanelManager.clearInfoPanel(tableName);
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
                this.updateTablesForClickUpdate();
            } else { // otherwise select the current row
                this.constraintsManager.addConstraint(tableName, rowData, rowIndex);
                this.updateTablesForClickUpdate();
            }
        } else { // otherwise just select this row
            this.constraintsManager.addConstraint(tableName, rowData, rowIndex);
            this.updateTablesForClickUpdate();
        }
    }

    multipleTrClickHandlerUpdate(tableName, selectedPkValues) {
        // we need to repopulate the constraints based on selectedPkValues
        // first find rows in the datatable based on selectedPkValues
        const tableAPI = $('#' + tableName).DataTable();
        const pkCol = getPkCol(tableName);
        const rows = tableAPI.rows((idx, data, node) => {
            const pk = data[pkCol];
            return selectedPkValues.includes(pk) ? true : false;
        });
        const allRowData = rows.data();
        const allRowIndices = rows.indexes();

        // add rows as multiple selections
        // here we assume that state has been reset (resetFiRDI was called)
        for (let i = 0; i < selectedPkValues.length; i++) {
            const rowData = allRowData[i];
            const rowIndex = allRowIndices[i];
            this.constraintsManager.addConstraint(tableName, rowData, rowIndex);
        }

        // refresh UI based on multiple selections
        this.updateFiRDIForMultipleSelect(tableName);
    }

    updateFiRDIForMultipleSelect(tableName) {
        // query db based on multiple selections
        console.log('queryResult');
        const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.state.constraints,
            this.state.whereType);

        // add selected class to the rows in selection
        this.addSelectionStyle(tableName);

        // update table content and selection style
        for (let i = 0; i < this.tableFieldNames.length; i++) { // update all the tables
            const tableFieldName = this.tableFieldNames[i];
            const tName = tableFieldName['tableName'];
            if (tName !== tableName) { // if table name is not the one with multiple selections
                // update table content
                this.updateSingleTable(tableFieldName, queryResult);
            }
        }

        // update bottom panel
        this.state.selectedIndex[tableName] = 0;
        const selections = this.state.selections[tableName];
        const selectedIndex = 0;
        const updatePage = true;
        this.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);
    }

    updateFiRDIForLoadSelection() {
        // query db based on multiple selections
        console.log('queryResult');
        const queryResult = this.sqlManager.queryDatabase(this.tablesInfo, this.state.constraints,
            this.state.whereType);

        // update table content and selection style
        for (let i = 0; i < this.tableFieldNames.length; i++) { // update all the tables
            const tableFieldName = this.tableFieldNames[i];
            const tableName = tableFieldName['tableName'];

            const selectedPkValues = this.state.selections[tableName];
            if (selectedPkValues.length > 0) {
                // add selected class to the rows in selection
                this.addSelectionStyle(tableName);

                // update bottom panel
                this.state.selectedIndex[tableName] = 0;
                const selections = this.state.selections[tableName];
                const selectedIndex = 0;
                const updatePage = true;
                this.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);
            } else { // if no selection, then just update the table values based on query result
                this.updateSingleTable(tableFieldName, queryResult);
            }
        }

    }

}

export default FiRDI;