import alasql from "alasql";
import {isTableVisible} from "./Utils";
import {LAST_CLICKED_FIRDI_SELECT_ALL} from "../common";

class DataTablesManager {

    constructor(state) {
        this.state = state;
        const tablesInfo = state.tablesInfo;
        const tableFields = state.tableFields;

        // Some minimum DataTables settings are required
        // set defaults across all tables
        const minDataTablesSettings = this.getMinTablesSettings();
        const defaultDataTablesSettings = this.getDefaultTablesSettings()
        const minTablesSettings = Object.assign(minDataTablesSettings, defaultDataTablesSettings || {});
        $.extend(true, $.fn.dataTable.defaults, minTablesSettings);

        // https://stackoverflow.com/questions/24383805/datatables-change-number-of-pagination-buttons
        // $.fn.DataTable.ext.pager.numbers_length = 3;

        const colNames = this.getDataTablesColumns(tablesInfo);
        const dataTablesColumnsSettings = this.convertColumnNamesToDataTablesSettings(colNames);
        const filteredTableInfo = this.uniqueDataFilter(tablesInfo);
        const dataTablesSettings = this.makeDataTablesSettingsObjects(filteredTableInfo, dataTablesColumnsSettings);
        this.initialiseDataTables(dataTablesSettings);

        // Hide certain columns
        const columnsToHidePerTable = [
            {"tableName": "genes_table", "columnNames": ["obs", "gene_pk"]},
            {"tableName": "proteins_table", "columnNames": ["obs", "protein_pk"]},
            {
                "tableName": "compounds_table",
                "columnNames": ["obs", "compound_pk"]
            },
            {
                "tableName": "reactions_table",
                "columnNames": ["obs", "reaction_pk"]
            },
            {"tableName": "pathways_table", "columnNames": ["obs", "pathway_pk"]}
        ];
        this.initHideColumnClicks(columnsToHidePerTable);
        this.hideColumns(columnsToHidePerTable, tableFields);
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

    getDefaultTablesSettings() {
        const self = this;
        const MAX_STRING_LEN = 50;

        const dashType = $.fn.dataTable.absoluteOrderNumber({
            value: '-', position: 'bottom'
        });

        const defaultDataTablesSettings = {
            // 'dom': 'Brftip',
            'dom': 'Brtip',
            'pageLength': 10,
            // 'scrollY': '800px',
            // 'scrollCollapse': true,
            'pagingType': 'simple',
            'searching': true,
            'select': true,
            'columnDefs': [
                {
                    'targets': 2,
                    'createdCell': function (td, cellData, rowData, row, col) {
                        if (rowData.obs === '-' || rowData.obs === null) {
                            // do nothing
                        } else if (rowData['significant_' + $('input[type=radio][name=inlineRadioOptions]:checked').val()]) {
                            $(td).addClass('significant');
                        } else if (rowData.obs) {
                            $(td).addClass('observed');
                        } else {
                            $(td).addClass('inferred');
                        }
                    },
                    'type': 'html'
                    // render: $.fn.dataTable.render.ellipsis(50, false)
                },
                {
                    'targets': '_all',
                    'defaultContent': '-',
                    'type': dashType,
                    'render': function (data, type, row) {
                        if (typeof (data) == 'number') {
                            return data.toFixed(2);
                        } else if (typeof (data) == 'string') {
                            return self.truncateString(data, MAX_STRING_LEN);
                            // } else if (data === null) {
                            //     return '-'
                        } else {
                            return data;
                        }
                    }
                }
            ],
            'order': [[2, 'asc']],
            'buttons': [
                {
                    extend: 'colvis',
                    columns: ':gt(1)',
                    titleAttr: 'Column Visibility',
                },
                {
                    text: '☑️ Select All',
                    action: function (e, dt, node, config) {
                        // toggle button text
                        const tableName = dt.settings()[0].sTableId;
                        self.state.rootStore.selectAllToggles[tableName] = !self.state.rootStore.selectAllToggles[tableName];
                        const selectAllToggle = self.state.rootStore.selectAllToggles[tableName];
                        const newText = selectAllToggle ? '☒ Unselect All' : '☑️ Select All';
                        this.text(newText);

                        self.state.rootStore.lastClicked = LAST_CLICKED_FIRDI_SELECT_ALL;
                        self.state.rootStore.lastClickedTableName = tableName;

                        if (selectAllToggle === true) {
                            // get all observed row data and indices
                            const allRowData = [];
                            const allRowIndices = [];
                            dt.rows().every(function (rowIdx, tableLoop, rowLoop) {
                                const rowData = this.data();
                                if (rowData.obs === true) {
                                    allRowData.push(rowData);
                                    allRowIndices.push(rowIdx);
                                }
                            });

                            // add all the selections at once
                            self.state.addConstraints(tableName, allRowData, allRowIndices);
                        } else {
                            self.state.removeConstraints(tableName);
                        }
                    }
                },
            ],
            'rowCallback': function (row, data, index) {
                // set tooltip
                function objToString(obj) {
                    let str = '';
                    for (let p in obj) {
                        if (obj.hasOwnProperty(p) && obj[p] !== null && p.startsWith('padj')) {
                            str += p + ': ' + obj[p].toFixed(4) + '\n';
                        }
                    }
                    return str;
                }

                const tooltip = objToString(data);
                if (tooltip.length > 0) {
                    $(row).attr({
                        'title': objToString(data)
                    })
                }

                // set cell colours
                const colNames = Object.keys(data);
                if (colNames.includes('pathway_id') && colNames.includes('padj_fdr')) {
                    // // colour pathway table
                    // const idx = colNames.indexOf('pathway_id');
                    // const pathway_id = data['pathway_id'];
                    // const padj = data['padj_fdr'];
                    // if (pathway_id !== '-' && padj !== null) {
                    //     const colorScale = d3.scaleLinear()
                    //         .range(["red", "green"])
                    //         .domain([1, 0]);
                    //     const colour = colorScale(padj);
                    //     const idx = 2;
                    //     $(row).find(`td:eq(${idx})`).css({
                    //         'background-color': colour,
                    //         'color': 'white'
                    //     });
                    // }
                } else {
                    // colour other tables that have t-tests done
                    const filtered = colNames.filter(x => x.indexOf('FC') > -1);
                    const filteredIdx = filtered.map(x => {
                        return colNames.indexOf(x);
                    });
                    const filtered_logfc = filtered.map(x => data[x]);
                    const colorScale = d3.scale.linear()
                        .range(["red", "green"])
                        .domain([-2, 2]);
                    const filteredColours = filtered_logfc.map(x => colorScale(x));
                    for (let i = 0; i < filteredIdx.length; i++) {
                        const idx = filteredIdx[i];
                        const colour = filteredColours[i];
                        const x = $(row).find(`td`).filter(function () {
                            // TODO: round to the specified decimal places and compare the string representation. Might not always work.
                            const dp = 2;
                            const val1 = parseFloat(this.textContent).toFixed(dp);
                            let val2 = filtered_logfc[i];
                            if (val2 === null) {
                                return false;
                            } else {
                                val2 = val2.toFixed(dp);
                            }
                            if (val2 === '-0.00') {
                                val2 = '0.00'
                            }
                            return val1 === val2;
                        });
                        if (x) {
                            x.css({
                                'background-color': colour,
                                'color': 'white'
                            });
                        }
                    }
                }
            }
            // 'responsive': true
        };
        return defaultDataTablesSettings;
    }

    // https://stackoverflow.com/questions/1199352/smart-way-to-shorten-long-strings-with-javascript
    truncateString(s, n) {
        return (s.length > n) ? s.substr(0, n - 1) + '&hellip;' : s;
    }


    initialiseDataTables(dataTablesSettingsObjects) {
        const self = this;
        dataTablesSettingsObjects.forEach(function (settings) {
            const tableName = settings['tableName'];
            const tableAPI = $('#' + tableName).DataTable(settings['tableSettings']);
            // TODO: quick hack to hide the Select All buttons from reactions and pathways tables
            if (tableName.includes('reactions') || tableName.includes('pathways')) {
                tableAPI.buttons(1).remove();
            } else { // set toggle button state for tables that have the Select ALl buttons
                self.state.rootStore.selectAllToggles[tableName] = false;
            }
        });
        // change button to arrows
        const buttons = $(".buttons-colvis");
        for (let button of buttons) {
            const btn = $(button);
            btn.text('▼');
        }
        // disable animation
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

}

export default DataTablesManager;