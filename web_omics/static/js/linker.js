$(document).ready(function() {

  const people = [
    {"peoplePK": 1, "personName": "Roger"},
    {"peoplePK": 2, "personName": "Bonnie"},
    {"peoplePK": 3, "personName": "Andy"},
    {"peoplePK": 4, "personName": "Michaela"}
  ];

  const drinks = [
    {"drinkPK": 1, "drinkName": "English breakfast"},
    {"drinkPK": 2, "drinkName": "Coffee"},
    {"drinkPK": 3, "drinkName": "Cola"},
    {"drinkPK": 4, "drinkName": "Mineral water"},
    {"drinkPK": 5, "drinkName": "Green tea"},
    {"drinkPK": 6, "drinkName": "Fanta"},
    {"drinkPK": 7, "drinkName": "Chocolate milkshake"},
    {"drinkPK": 8, "drinkName": "Martini"}
  ];

  const additives = [
    {"additivePK": 1, "additive": "Milk"},
    {"additivePK": 2, "additive": "Ice"},
    {"additivePK": 3, "additive": "Lemon juice"},
    {"additivePK": 4, "additive": "Nothing"},
    {"additivePK": 5, "additive": "Olive"},
    {"additivePK": 6, "additive": "Strawberry"}
  ];

  const storage = [
    {"storagePK": 1, "storage": "fridge"},
    {"storagePK": 2, "storage": "freezer"},
    {"storagePK": 3, "storage": "cupboard"},
    {"storagePK": 4, "storage": "garden"}
  ];

  const pathways = [
    {"pathwayPK": 1, "pathway": "pathway1"},
    {"pathwayPK": 2, "pathway": "pathway2"},
    {"pathwayPK": 3, "pathway": "pathway3"},
    {"pathwayPK": 4, "pathway": "pathway4"}
  ];

  const peopleDrinks = [
    {"peoplePK": 1, "drinkPK": 2},
    {"peoplePK": 1, "drinkPK": 2},
    {"peoplePK": 2, "drinkPK": 3},
    {"peoplePK": 1, "drinkPK": 4},
    {"peoplePK": 1, "drinkPK": 1},
    {"peoplePK": 1, "drinkPK": 6},
    {"peoplePK": 4, "drinkPK": 2},
    {"peoplePK": 3, "drinkPK": 8},
    {"peoplePK": 3, "drinkPK": 4},
    {"peoplePK": 3, "drinkPK": 5},
    {"peoplePK": 2, "drinkPK": 7}
  ];

  const drinksAdditives = [
    {"drinkPK": 1, "additivePK": 1},
    {"drinkPK": 1, "additivePK": 4},
    {"drinkPK": 1, "additivePK": 3},
    {"drinkPK": 2, "additivePK": 1},
    {"drinkPK": 2, "additivePK": 2},
    {"drinkPK": 2, "additivePK": 4},
    {"drinkPK": 3, "additivePK": 2},
    {"drinkPK": 3, "additivePK": 4},
    {"drinkPK": 4, "additivePK": 2},
    {"drinkPK": 4, "additivePK": 4},
    {"drinkPK": 4, "additivePK": 5},
    {"drinkPK": 5, "additivePK": 3},
    {"drinkPK": 5, "additivePK": 4},
    {"drinkPK": 6, "additivePK": 2},
    {"drinkPK": 6, "additivePK": 4},
    {"drinkPK": 7, "additivePK": 6},
    {"drinkPK": 7, "additivePK": 4},
    {"drinkPK": 8, "additivePK": 5},
  ];

  const additiveStorage = [
    {"additivePK": 1, "storagePK": 1},
    {"additivePK": 2, "storagePK": 2},
    {"additivePK": 3, "storagePK": 3},
    {"additivePK": 3, "storagePK": 1},
    {"additivePK": 3, "storagePK": 4},
    {"additivePK": 4, "storagePK": 3},
    {"additivePK": 5, "storagePK": 3},
    {"additivePK": 5, "storagePK": 5},
    {"additivePK": 6, "storagePK": 2},
    {"additivePK": 6, "storagePK": 4},
  ];

  const storagePathway = [
    {"storagePK": 1, "pathwayPK": 1},
    {"storagePK": 2, "pathwayPK": 2},
    {"storagePK": 3, "pathwayPK": 3},
    {"storagePK": 3, "pathwayPK": 1},
    {"storagePK": 3, "pathwayPK": 4},
    {"storagePK": 4, "pathwayPK": 3},
  ];

  const defaultDataTablesSettings = {
    "dom": "rtp",
    "pageLength": 5
  };

  const tables = [
    {
      "tableName": "people_table",
      "tableData": people,
      "options": {
        "visible": true,
        "pk": "peoplePK"
      },
      "relationship": {"with": "peopleDrinks", "using": "peoplePK"}
    },
    {
      "tableName": "peopleDrinks",
      "tableData": peopleDrinks,
      "options": {
        "visible": false
      },
      "relationship": {"with": "drinks_table", "using": "drinkPK"}
    },
    {
      "tableName": "drinks_table",
      "tableData": drinks,
      "options": {
        "visible": true,
        "pk": "drinkPK"
      },
      "relationship": {"with": "drinksAdditives", "using": "drinkPK"}
    },
    {
      "tableName": "drinksAdditives",
      "tableData": drinksAdditives,
      "options": {
        "visible": false
      },
      "relationship": {"with": "additives_table", "using": "additivePK"}
    },
    {
      "tableName": "additives_table",
      "tableData": additives,
      "options": {
        "visible": true,
        "pk": "additivePK"
      },
      "relationship": {"with": "additiveStorage", "using": "additivePK"}
    },
    {
      "tableName": "additiveStorage",
      "tableData": additiveStorage,
      "options": {
        "visible": false
      },
      "relationship": {"with": "storage_table", "using": "storagePK"}
    },
    {
      "tableName": "storage_table",
      "tableData": storage,
      "options": {
        "visible": true,
        "pk": "storagePK"
        },
        "relationship": {"with": "storagePathway", "using": "storagePK"}    
    },
    {
      "tableName": "storagePathway",
      "tableData": storagePathway,
      "options": {
        "visible": false
      },
      "relationship": {"with": "pathway_table", "using": "pathwayPK"}
    },
    {
      "tableName": "pathway_table",
      "tableData": pathways,
      "options": {
        "visible": true,
        "pk": "pathwayPK"
      }
    }
  ];

  FiRDI.init(tables, defaultDataTablesSettings);

  // Hide certain columns
  const columnsToHidePerTable = [
    {"tableName": "people_table", "columnNames": ["peoplePK"]},
    {"tableName": "drinks_table", "columnNames": ["drinkPK"]},
    {"tableName": "storage_table", "columnNames": ["storagePK"]},
    {"tableName": "additives_table", "columnNames": ["additivePK"]},
    {"tableName": "pathway_table", "columnNames": ["pathwayPK"]}
  ];

  columnsToHidePerTable.forEach(function(tableInfo) {
    $('#' + tableInfo['tableName']).DataTable()
      .columns(tableInfo['columnNames'].map(columnName => columnName + ":name")) // append ":name" to each columnName for the selector
      .visible(false);
  });
});