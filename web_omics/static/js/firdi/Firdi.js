import 'datatables.net';
import 'datatables.net-dt/css/jquery.dataTables.css';
import 'datatables.net-buttons';
import 'datatables.net-buttons-dt/css/buttons.dataTables.min.css';
import 'datatables.net-buttons/js/buttons.colVis.js'; // Column visibility
import 'datatables.net-buttons/js/buttons.html5.js';
import 'datatables.net-responsive';
import 'datatables.net-responsive-dt/css/responsive.dataTables.min.css';
import 'datatables.net-scroller';
import 'datatables.net-scroller-dt/css/scroller.dataTables.min.css';
import 'datatables.net-select';
import 'datatables.net-select-dt/css/select.dataTables.min.css';
import 'datatables.net-plugins/sorting/absolute.js';

import "jQuery-QueryBuilder/dist/js/query-builder.js";
import "jQuery-QueryBuilder/dist/css/query-builder.default.css";

import {
    blockFirdiTable,
    GROUP_LOADED_EVENT,
    HEATMAP_CLICKED_EVENT,
    LAST_CLICKED_FIRDI,
    LAST_CLICKED_QUERY_BUILDER,
    QUERY_BUILDER_WIDTH,
    QUERY_FILTER_EVENT,
    SELECT_ALL_EVENT,
    SELECTION_UPDATE_EVENT,
    unblockFirdiTable
} from '../common';
import DataTablesManager from './DataTablesManager';
import {getPkValue, getRowObj} from "./Utils";
import InfoPanesManager from "./InfoPanesManager";


class Firdi {

    constructor(rootStore, viewNames) {
        this.rootStore = rootStore;
        this.state = rootStore.firdiStore;
        this.rootStore.cgmStore.on(HEATMAP_CLICKED_EVENT, (data) => {
            if (data.cgmLastClickedName) {
                console.log('Clustergrammer --> Firdi');
                this.resetFiRDI();
                this.updateFiRDIForMultipleSelect(data.cgmLastClickedName);
            }
        })
        this.rootStore.firdiStore.on(GROUP_LOADED_EVENT, (data) => {
            console.log('GroupManager --> Firdi');
            this.resetFiRDI();
            this.updateFiRDIForLoadSelection();
        })
        this.rootStore.firdiStore.on(SELECTION_UPDATE_EVENT, (data) => {
            console.log('Firdi Row Selection --> Firdi');
            this.updateTablesForClickUpdate();
        })
        this.rootStore.firdiStore.on(QUERY_FILTER_EVENT, (data) => {
            console.log('QueryBuilder --> Firdi');
            this.resetFiRDI();
            this.updateTablesForQueryBuilder();
        })
        this.rootStore.firdiStore.on(SELECT_ALL_EVENT, (data) => {
            console.log('Firdi Select All --> Firdi');
            this.updateTablesForSelectAll();
        })

        this.dataTablesManager = new DataTablesManager(this.state);
        this.infoPanelManager = new InfoPanesManager(this.state, viewNames);

        this.initTableClicks();
        this.initSignificantFilters();
        this.initSearchBox();
    }

    initTableClicks() {
        const dataTablesIds = this.state.dataTablesIds;
        const dataTablesIdsKeys = Object.keys(dataTablesIds);
        dataTablesIdsKeys.forEach(id => $(dataTablesIds[id]).DataTable().on('user-select', this.trClickHandler.bind(this)));
    }

    initSignificantFilters() {
        this.setupQueryBuilder();

        // button handlers
        const self = this;

        function setWhereType(result) {
            blockFirdiTable();
            // set last clicked UI element
            self.rootStore.lastClicked = LAST_CLICKED_QUERY_BUILDER;
            // set filtering value
            window.setTimeout(function () {
                self.state.setWhereType(result);
                unblockFirdiTable();
            }, 1); // we need a small delay to allow blockFirdiTable to be rendered correctly
        }

        $('#builderReset').on('click', function () {
            $('#builder').queryBuilder('reset');
            setWhereType(null);
        });

        $('#builderApply').on('click', function () {
            const result = $('#builder').queryBuilder('getRules');
            if (!$.isEmptyObject(result)) {
                // console.log(JSON.stringify(result, null, 4));
                setWhereType(result);
            }
        });

    }

    setupQueryBuilder() {
        // create list of filters for each adjusted p-value and fold-change column across all tables
        const builderFilters = [];
        const tableNames = Object.keys(this.state.filterNames)
        for (const tableName of tableNames) {
            const values = this.state.filterNames[tableName];
            const padjColumns = values.padj;
            const fcColumns = values.FC;
            for (const padjCol of padjColumns) {
                const shortTableName = tableName.replace('_table','');
                builderFilters.push(
                    {
                        id: `${tableName}.${padjCol}`,
                        label: `${shortTableName}: ${padjCol}`,
                        type: 'boolean',
                        input: 'select',
                        values: {
                            true: 'Significant'
                        },
                        operators: ['equal']
                    });
            }
            for (const fcCol of fcColumns) {
                const shortTableName = tableName.replace('_table','');
                builderFilters.push(
                    {
                        id: `${tableName}.${fcCol}`,
                        label: `${shortTableName}: ${fcCol}`,
                        type: 'double',
                        validation: {
                            step: 0.1
                        },
                        operators: ['less_or_equal', 'greater_or_equal', 'between', 'not_between']
                    });
            }
        }

        // init query builder
        if (builderFilters.length > 0) {
            $('#builder').queryBuilder({
                filters: builderFilters,
                // rules: loadedRules,
                default_group_flags: {
                    no_add_group: true
                },
                conditions: ['AND']
            });
            $('#builder_group_0').css('width', QUERY_BUILDER_WIDTH);
        } else {
            $('#cardFilter').hide();
        }
    }

    initSearchBox() {
        $('#global_filter').on('keyup click', function () {
            const val = $('#global_filter').val();
            $.fn.dataTable.tables({api: true}).search(val).draw();
        });
        $('#showGeneTable').on('change', () => $('#collapseGene').collapse('toggle'));
        $('#showProteinTable').on('change', () => $('#collapseProtein').collapse('toggle'));
        $('#showCompoundTable').on('change', () => $('#collapseCompound').collapse('toggle'));
        $('#showReactionTable').on('change', () => $('#collapseReaction').collapse('toggle'));
        $('#showPathwayTable').on('change', () => $('#collapsePathway').collapse('toggle'));
    }

    resetFiRDI() {
        // it doesn't seem necesary to clear all SQL tables in alasql when resetting, since they will
        // never change. We only need to clear the data tables data as well as the info panels.

        // TODO: not sure why we need to copy here
        // const tablesInfoCopy = JSON.parse(JSON.stringify(this.state.tablesInfo));
        // this.sqlManager.clearAlasqlTables(tablesInfoCopy);
        // this.sqlManager.addNewData(tablesInfoCopy);

        // clear data tables
        const dataTablesIds = this.state.dataTablesIds;
        this.state.tablesInfo.forEach(t => {
            const tableName = t['tableName'];
            const tableAPI = $(dataTablesIds[tableName]).DataTable();
            tableAPI.clear();
            tableAPI.rows.add(t['tableData']);
            tableAPI.draw();
        });

        // reset state if necessary
        // if (resetState) {
        //     this.state.reset();
        // }

        // reset info panels
        this.infoPanelManager.clearAllInfoPanels();
    }

    updateTables() {
        const fieldNames = this.state.fieldNames;
        const queryResult = this.state.queryResult;
        for (let i = 0; i < fieldNames.length; i++) { // update all the tables
            const tableFieldName = fieldNames[i];
            this.updateSingleTable(tableFieldName, queryResult);
        }
    }

    updateTablesForClickUpdate() {
        if (this.state.totalSelected > 0) {
            const fieldNames = this.state.fieldNames;
            const queryResult = this.state.queryResult;
            for (let i = 0; i < fieldNames.length; i++) { // update all the tables
                const tableFieldName = fieldNames[i];
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
        // this.state.notifyUpdate();
    }

    updateTablesForQueryBuilder() {
        const fieldNames = this.state.fieldNames;
        const queryResult = this.state.queryResult;
        for (let i = 0; i < fieldNames.length; i++) { // update all the tables
            const tableFieldName = fieldNames[i];
            const tableName = tableFieldName['tableName'];
            this.updateSingleTable(tableFieldName, queryResult);
        }
    }

    updateTablesForSelectAll() {
        // update all tables
        this.updateTablesForClickUpdate();

        // update bottom panel for the current table
        const tableName = this.state.rootStore.lastClickedTableName;
        if (this.state.numSelected[tableName] > 0) {
            this.state.selectedIndex[tableName] = 0;
            const selections = this.state.selections[tableName];
            const selectedIndex = 0;
            const updatePage = true;
            this.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);
        } else {
            this.infoPanelManager.clearInfoPanel(tableName);
        }
    }

    updateSingleTable(tableFieldName, queryResult) {
        const dataTablesIds = this.state.dataTablesIds;
        const tableName = tableFieldName['tableName'];
        const data = queryResult[tableName];
        $(dataTablesIds[tableName]).DataTable().clear();
        $(dataTablesIds[tableName]).DataTable().rows.add(data);
        $(dataTablesIds[tableName]).DataTable().draw();
    }

    addSelectionStyle(tableName) {
        const dataTablesIds = this.state.dataTablesIds;
        const tableAPI = $(dataTablesIds[tableName]).DataTable();
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

    resetTable(tableName, tableData) {
        const dataTablesIds = this.state.dataTablesIds;
        const tableAPI = $(dataTablesIds[tableName]).DataTable();
        tableAPI.clear();
        tableAPI.rows.add(tableData);
        tableAPI.draw();
        tableAPI.page(0).draw('page');
    }

    resetTables() {
        const fieldNames = this.state.fieldNames;
        const queryResult = this.state.queryResult;
        for (let i = 0; i < fieldNames.length; i++) { // update all the tables
            const tableFieldName = fieldNames[i];
            const tableName = tableFieldName['tableName'];
            this.resetTable(tableName, queryResult[tableName]);
        }
    }

    trClickHandler(e, dt, type, cell, originalEvent) {
        e.preventDefault();
        blockFirdiTable();
        const self = this;
        window.setTimeout(function () {

            // set last clicked UI element
            self.rootStore.lastClicked = LAST_CLICKED_FIRDI;

            // clear search result
            $('#global_filter').val('');
            $.fn.dataTable.tables({api: true}).search('');

            // find the selected row
            const tableName = e.currentTarget.id;
            const dataTablesIds = self.state.dataTablesIds;
            const tableAPI = $(dataTablesIds[tableName]).DataTable();
            const targetTr = $(originalEvent.target).closest('tr');
            const row = tableAPI.row(targetTr);
            const rowData = row.data();
            const rowIndex = tableAPI.rows()[0].indexOf(row.index());
            const anyRowSelected = tableAPI.rows('.selected').any();

            self.trClickHandlerUpdate(tableName, targetTr, rowData, rowIndex, anyRowSelected);
            unblockFirdiTable();
            // update the related info panel for this table, if any
            if (self.state.numSelected[tableName] > 0) {

                // assume that entries in the array is always in sorted order by their row index
                // (the sorting is done upon insertion in addConstraint)
                const selections = self.state.selections[tableName];

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
                self.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);

                // store for use in buttons etc later
                self.state.selectedIndex[tableName] = selectedIndex;

            } else {
                self.infoPanelManager.clearInfoPanel(tableName);
            }
        }, 1); // we need a small delay to allow blockFirdiTable to be rendered correctly
    }

    trClickHandlerUpdate(tableName, targetTr, rowData, rowIndex, anyRowSelected) {
        // if some rows are already selected in the table
        this.state.rootStore.lastClickedTableName = tableName;
        if (anyRowSelected) {
            // if the current row is already selected then unselect it
            if (targetTr.hasClass('selected')) {
                this.state.removeConstraint(tableName, rowData);
                this.removeSelectionStyle(targetTr);
                // this.updateTablesForClickUpdate();
            } else { // otherwise select the current row
                this.state.addConstraint(tableName, rowData, rowIndex);
                // this.updateTablesForClickUpdate();
            }
        } else { // otherwise just select this row
            this.state.addConstraint(tableName, rowData, rowIndex);
            // this.updateTablesForClickUpdate();
        }
    }

    updateFiRDIForMultipleSelect(tableName) {
        // add selected class to the rows in selection
        this.addSelectionStyle(tableName);

        // update table content and selection style
        const fieldNames = this.state.fieldNames;
        const queryResult = this.state.queryResult;
        for (let i = 0; i < fieldNames.length; i++) { // update all the tables
            const tableFieldName = fieldNames[i];
            const tName = tableFieldName['tableName'];
            if (tName !== tableName) { // if table name is not the one with multiple selections
                // update table content
                this.updateSingleTable(tableFieldName, queryResult);
            }
        }

        // update bottom panel
        if (this.state.numSelected[tableName] > 0) {
            this.state.selectedIndex[tableName] = 0;
            const selections = this.state.selections[tableName];
            const selectedIndex = 0;
            const updatePage = true;
            this.infoPanelManager.updateEntityInfo(tableName, selections, selectedIndex, updatePage);
        }
    }

    updateFiRDIForLoadSelection() {
        // update table content and selection style
        // at this point, tables have been reset and we see the default initial values
        const fieldNames = this.state.fieldNames;
        const queryResult = this.state.queryResult;
        for (let i = 0; i < fieldNames.length; i++) { // update all the tables
            const tableFieldName = fieldNames[i];
            const tableName = tableFieldName['tableName'];

            // if the current table has some selections, then we only need to add selected class
            // to the selected rows, and also update the bottom panels
            // otherwise we update the table contents to show the query results
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
            } else { // if no selection, then update the table values based on query result
                this.updateSingleTable(tableFieldName, queryResult);
            }
        }

    }

}

export default Firdi;