const FiRDI = (function() {
  const isTableVisible = tableInfo => tableInfo["options"]["visible"];

  // set up datatables
  let dataTablesOptionsManager = {
    init: function(tablesInfo) {
      const colNames = this.getDataTablesColumns(tablesInfo);
      const dataTablesColumnsSettings = this.convertColumnNamesToDataTablesSettings(colNames);
      const filteredTableInfo = this.uniqueDataFilter(tablesInfo);
      const dataTablesSettings = this.makeDataTablesSettingsObjects(filteredTableInfo, dataTablesColumnsSettings);
      this.initialiseDataTables(dataTablesSettings);

      return this;
    },
    initialiseDataTables: function(dataTablesSettingsObjects) {
      dataTablesSettingsObjects.forEach(function(x) {
        $('#' + x['tableName']).DataTable(x['tableSettings']);
      });
    },
    uniqueDataFilter: function(tablesInfo) {
      // Gets the distinct entries for the tableData for datatables initialisation
      return tablesInfo.filter(isTableVisible)
        .map(tableInfo => {
          tableInfo['tableData'] = alasql("SELECT DISTINCT " + Object.keys(tableInfo['tableData'][0]).join(", ") + " FROM ?", [tableInfo['tableData']]);
          return tableInfo;
        });
    },
    convertColumnNamesToDataTablesSettings: function(columnNamesPerTable) {
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
    },
    getDataTablesColumns: function(tablesInfo) {
      // Gets the column/field names from the tableData of each table in tablesInfo
      // Use column ordering if provided, else get column names from JSON attributes
      return tablesInfo.filter(isTableVisible)
        .map(tableInfo => tableInfo['options']['columnOrder'] || Object.keys(tableInfo['tableData'][0]));
    },
    makeDataTablesSettingsObjects: function(tablesInfo, dataTablesColumnsSettings) {
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
  };

  let sqlManager = {
    init: function(tablesInfo) {
      this.initialiseAlasqlTables(tablesInfo);
      this.firstTable = this.getFirstTable(tablesInfo);
      this.tableRelationships = this.getTableRelationships(tablesInfo);
      this.constraintTableConstraintKeyNames = this.getConstraintTablesConstraintKeyName(tablesInfo);

      this.sqlQuery = this.makeSQLquery(tablesInfo);

      this.compiledSQLQuery = alasql.compile(this.sqlQuery);
      return this;
    },
    initialiseAlasqlTables: function(tablesInfo) {
      tablesInfo.forEach(function(t) {
        // Create table
        alasql("CREATE TABLE " + t['tableName']);
        // Add data
        alasql.tables[t['tableName']].data = t['tableData'];
      });
    },
    clearAlasqlTables: function(tablesInfo) {
      tablesInfo.forEach(function(t) {
        alasql('DELETE FROM ' + t['tableName']);
      });
    },
    addNewData: function(tablesInfo) {
      tablesInfo.forEach(t => alasql.tables[t['tableName']].data = t['tableData']);
    },
    getConstraintTablesConstraintKeyName: function(tablesInfo) {
      return tablesInfo
        .filter(isTableVisible)
        .map(t => ({'tableName': t['tableName'], 'constraintKeyName': t['options']['pk']}));
    },
    getFieldNames: function(tablesInfo) {
      return tablesInfo
        .filter(isTableVisible)
        .map(tableInfo => ({'tableName': tableInfo['tableName'], 'firstDataRow': tableInfo['tableData'][0]}))
        .map(tableData => Object.keys(tableData['firstDataRow'])
        .map(e => tableData['tableName'] + "." + e))
        .reduce((fieldNamesArray, fieldNames) => fieldNamesArray.concat(fieldNames), [])
        .join(", ");
    },
    assembleInnerJoinStatementFromRelationship: function(relationship) {
      let innerJoinStatement;
      if (relationship['with']) {
        innerJoinStatement = "INNER JOIN " + relationship['with'] + " ON " + relationship['tableName'] + "." + relationship['using'] + " = " + relationship['with'] + "." + relationship['using'];
      } else {
        innerJoinStatement = "";
      }

      return innerJoinStatement;
    },
    makeSelectClause: function(tablesInfo) {
      // Join each field into a select clause
      const fieldNames = this.getFieldNames(tablesInfo);
      // put the first table in the from clause
      const selectClause = "SELECT " + fieldNames + " FROM " + this.firstTable;
      return selectClause;
    },
    makeInnerJoinClause: function() {
      return this.tableRelationships
        .map(this.assembleInnerJoinStatementFromRelationship.bind(this))
        .join(" ");
    },
    getFirstTable: function(tablesInfo) {
      return tablesInfo[0]['tableName'];
    },
    getRelationship: function(tableInfo) {
      if (tableInfo['relationship']) {
        return {'tableName': tableInfo['tableName'], 'with': tableInfo['relationship']['with'], 'using': tableInfo['relationship']['using']};
      } else {
        return {'tableName': tableInfo['tableName']};
      };
    },
    getTableRelationships: function(tablesInfo) {
      return tablesInfo
        .map(this.getRelationship);
    },
    getTableKeys: function() {
      // Returns the table name and the name of the key used in the where clause
      return this.tableRelationships
        .map(t => JSON.stringify({'tableName': t['tableName'], 'tableKey': t['using']}))
        .filter((tk, idx, tka) => tka.indexOf(tk) === idx)
        .map(t => JSON.parse(t));
    },
    makeWhereSubClauses: function() {
      return this.constraintTableConstraintKeyNames
        .map(t => t['tableName'] + "." + t['constraintKeyName'])
    },
    makeWhereClause: function(tablesInfo) {
      const whereSubClauses = this.makeWhereSubClauses();
      const first = "WHERE " + whereSubClauses[0] + " IN @(?)";
      const rest = whereSubClauses
        .slice(1)
        .map(whereSubClause => "AND " + whereSubClause + " IN @(?)")
        .join(" ");
      return first + " " + rest;
    },
    makeSQLquery: function(tablesInfo) {
      const selectClause = this.makeSelectClause(tablesInfo);
      const innerJoinClause = this.makeInnerJoinClause();
      const whereClause = this.makeWhereClause();

      return [selectClause, innerJoinClause, whereClause].join(" ");
    },
    queryDatabase: function(constraints) {
      const constraintTableNames = this.constraintTableConstraintKeyNames.map(t => t['tableName']);
      const unpackedConstraints = constraintTableNames.map(n => constraints[n]);
      return this.compiledSQLQuery(unpackedConstraints);
    }
  };

  let stackManager = {
    init: function() {
      this.stack = [];
      return this;
    },
    addToStack: function(name) {
      let nameIdx;
      // Find if name is in the stack
      this.stack.forEach(function(d, i) {
        if (d === name) {
          nameIdx = i;
        }
      })
      // If the name is in the stack, remove it
      if (nameIdx) {
        this.stack.splice(nameIdx, 1);
      }
      // Add name to the stack
      this.stack.push(name);
    },
    removeFromStack: function(name) {
      let nameIdx;
      this.stack.forEach(function(d, i) {
        if (d == name) {
          nameIdx = i;
        }
      })
      this.stack.splice(nameIdx, 1);
    },
    emptyStack: function() {
      this.stack = [];
    },
    peek: function() {
      return this.stack[this.stack.length - 1];
    }
  };

  let constraintsManager = {
    init: function(tablesInfo) {
      this.tableKeys = sqlManager.getTableKeys(tablesInfo);
      this.defaultConstraints = this.getDefaultConstraints(tablesInfo);
      this.constraints = this.initConstraints();

      this.constraintTablesConstraintKeyNames = sqlManager.getConstraintTablesConstraintKeyName(tablesInfo)
      this.tableIdToIdColumnMap = this.getTableKeysAsSingleObject(tablesInfo);

      return this;
    },
    getKeys: function(tablesInfo, tableName, k) {
      // Gets the values of the key used in the table relationship for the SQL IN clause
      const data = tablesInfo
        .filter(isTableVisible)
        .filter(t => t['tableName'] === tableName)
        .map(t => t['tableData'])[0];

      const keys = data
        .map(d => d[k])
        .filter((k, idx, arr) => arr.indexOf(k) === idx);

      return keys;
    },
    getDefaultConstraints: function(tablesInfo) {
      return sqlManager.getConstraintTablesConstraintKeyName(tablesInfo)
        .reduce((constraints, tableInfo) => {
          constraints[tableInfo['tableName']] = this.getKeys(tablesInfo, tableInfo['tableName'], tableInfo['constraintKeyName']);
          return constraints;
        }, {});
    },
    makeEmptyConstraint: function(tablesInfo) {
      return sqlManager.getConstraintTablesConstraintKeyName(tablesInfo)
        .reduce((constraints, tableInfo) => {
          constraints[tableInfo['tableName']] = [];
          return constraints;
        }, {});
    },
    initConstraints: function() {
      // hack for deep copy
      return JSON.parse(JSON.stringify(this.defaultConstraints));
    },
    getFocusConstraints: function(focus, tablesInfo) {
      return sqlManager.getConstraintTablesConstraintKeyName(tablesInfo)
        .reduce((constraints, tableInfo) => {
          constraints[tableInfo['tableName']] = (focus === tableInfo['tableName']) ? this.defaultConstraints[tableInfo['tableName']] : this.constraints[tableInfo['tableName']];
          return constraints;
        }, {});
    },
    getTableKeysAsSingleObject: function(tablesInfo) {
      // Get the table name and key used in the WHERE clause in the form tableName: key
      return sqlManager.getConstraintTablesConstraintKeyName(tablesInfo)
        .map(t => ({[t['tableName']]: t['constraintKeyName']}))
        .reduce((o, v) => Object.assign(o, v), {});
    },
    addConstraint: function(tableName, rowObject) {
      stackManager.addToStack(tableName);
      this.constraints[tableName] = [rowObject[this.tableIdToIdColumnMap[tableName]]];
    },
    updateConstraint: function(tableName, rowObject) {
      stackManager.removeFromStack(tableName);
      stackManager.addToStack(tableName);
      this.constraints[tableName] = [rowObject[this.tableIdToIdColumnMap[tableName]]];
    },
    removeConstraint: function(tableName) {
      stackManager.removeFromStack(tableName);
      this.constraints[tableName] = this.defaultConstraints[tableName];
    }
  };

  let tablesManager = {
    init: function(tablesInfo, defaultDataTablesSettings) {
      this.tablesInfo = tablesInfo;

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

      this.dataTablesOptionsManager = dataTablesOptionsManager.init(this.tablesInfo);
      this.sqlManager = sqlManager.init(this.tablesInfo);
      this.constraintsManager = constraintsManager.init(this.tablesInfo);
      this.stackManager = stackManager.init();

      this.tableFieldNames = this.getFieldNames();
      this.dataTablesIds = tablesInfo.filter(isTableVisible).reduce((apis, t) => {apis[t['tableName']] = "#" + t['tableName']; return apis}, {});

      this.initTableClicks();

      return this;
    },
    resetFiRDI: function(newTablesInfo) {
      // copy tablesInfo into newTablesInfo
      // replace the data with the newData

      this.tablesInfo = this.tablesInfo.map(t => {t['tableData'] = newTablesInfo[t['tableName']]; return t;});
      this.sqlManager.clearAlasqlTables(this.tablesInfo);
      this.sqlManager.addNewData(this.tablesInfo);
      this.stackManager.emptyStack();
      this.constraintsManager.defaultConstraints = this.constraintsManager.getDefaultConstraints(this.tablesInfo);
      this.constraintsManager.constraints = this.constraintsManager.initConstraints()

      this.tablesInfo.forEach(t => {
        const tableAPI = $(this.dataTablesIds[t['tableName']]).DataTable();
        tableAPI.clear();
        tableAPI.rows.add(t['tableData']);
        tableAPI.draw();
      });

    },
    initTableClicks: function() {
      const dataTablesIdsKeys = Object.keys(this.dataTablesIds);
      dataTablesIdsKeys.forEach(id => $(this.dataTablesIds[id]).DataTable().on('user-select',  this.trClickHandler.bind(this)));
    },
    getFieldNames: function() {
      // Gets the field names for each visible table
      return this.tablesInfo
        .filter(isTableVisible)
        .map(tableInfo => ({'tableName': tableInfo['tableName'], 'fieldNames': Object.keys(tableInfo['tableData'][0])}));
    },
    getFocusData: function(dataForTables, focusResult, queryResult, tableFieldNames, focus) {
      // Function to get the default constraints for the focus table
      const tableName = tableFieldNames['tableName'];
      const fieldNames = tableFieldNames['fieldNames'];
      const sqlStatement = "SELECT DISTINCT " + fieldNames.join(", ") + " FROM ?";

      if (focus !== tableName) {
        dataForTables[tableName] = alasql(sqlStatement, [queryResult]);
      } else {
        dataForTables[tableName] = alasql(sqlStatement, [focusResult]);
      }

      $(this.dataTablesIds[tableName]).DataTable().clear();
      $(this.dataTablesIds[tableName]).DataTable().rows.add(dataForTables[tableName]);
      $(this.dataTablesIds[tableName]).DataTable().draw();
      this.addSelectionStyle(tableName);

    },
    updateTables: function() {
      if (this.stackManager.stack.length > 0) {
        let dataForTables = this.constraintsManager.makeEmptyConstraint(this.tablesInfo);
        const queryResult = this.sqlManager.queryDatabase(this.constraintsManager.constraints);
        const focus = this.stackManager.peek();

        const focusConstraints = this.constraintsManager.getFocusConstraints(focus, this.tablesInfo);
        const focusResult = this.sqlManager.queryDatabase(focusConstraints);

        this.tableFieldNames.forEach(tableFieldNames => this.getFocusData(dataForTables, focusResult, queryResult, tableFieldNames, focus));
      } else {
        this.resetTables();
      }
    },
    addSelectionStyle: function(tableName) {
      const tableAPI = $(this.dataTablesIds[tableName]).DataTable(),
        idNum = this.constraintsManager.constraints[tableName];

      // idNum has a single element when a constraint (different from the initial constraint) is
      // applied.
      if (idNum.length === 1) {
        // Find page that contains the row of interest
        // Go to it
        // add selection to that row.

        const pageInfo = tableAPI.page.info();
        const rowIndex = tableAPI.rows()[0].indexOf(tableAPI.row('#' + idNum).index());
        const thePage = Math.floor(rowIndex / pageInfo['length']);

        tableAPI.page(thePage).draw('page');

        $(tableAPI.row('#' + idNum).node()).addClass('selected');

      }
    },
    resetTable: function(tableFieldNames, dataForTables) {
      const tableName = tableFieldNames['tableName'];
      const fieldNames = tableFieldNames['fieldNames'];
      const sqlStatement = "SELECT DISTINCT " + fieldNames.join(", ") + " FROM ?";
      const queryResult = this.sqlManager.queryDatabase(this.constraintsManager.constraints);
      const tableAPI = $(this.dataTablesIds[tableName]).DataTable();

      dataForTables[tableFieldNames['tableName']] = alasql(sqlStatement, [queryResult]);

      const oldPageInfo = tableAPI.page.info();
      const oldRowIndex = oldPageInfo['start'];
      const rowID = tableAPI.row(oldRowIndex).id();

      tableAPI.clear();
      tableAPI.rows.add(dataForTables[tableName]);

      tableAPI.draw();
      const newRowIndex = tableAPI.row('#' + rowID).index();
      const thePage = Math.floor(newRowIndex / tableAPI.page.info()['length']);
      tableAPI.page(thePage).draw('page');
    },
    resetTables: function() {
      let dataForTables = this.constraintsManager.makeEmptyConstraint(this.tablesInfo);

      this.tableFieldNames.forEach(tableFieldNames => this.resetTable(tableFieldNames, dataForTables));
    },
    trClickHandler: function(e, dt, type, cell, originalEvent) {
      // Calls the appropriate constraint function depending on the state of the bound table
      e.preventDefault();
      const tableName = e.currentTarget.id;
      const tableAPI = $(this.dataTablesIds[tableName]).DataTable()
            targetTr = $(originalEvent.target).closest('tr'),
            rowObject = tableAPI.row(targetTr).data();

      // console.log("before", this.stackManager.stack, this.constraintsManager.constraints);
      if (tableAPI.rows( '.selected' ).any()) {
        if (!targetTr.hasClass('selected')) {
          $('#' + tableName + ' .selected').removeClass('selected');
          this.constraintsManager.updateConstraint(tableName, rowObject);
          this.updateTables();
        } else {
          this.constraintsManager.removeConstraint(tableName);
          this.updateTables();
        }
      } else {
        this.constraintsManager.addConstraint(tableName, rowObject);
        this.updateTables();
      }
      // console.log("after", this.stackManager.stack, this.constraintsManager.constraints);
    }
  };

  return {
    init: tablesManager.init.bind(tablesManager)
  };

})();
