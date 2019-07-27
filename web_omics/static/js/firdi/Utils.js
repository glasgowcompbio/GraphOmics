const isTableVisible = tableInfo => tableInfo["options"]["visible"];

const getPkValue = function (rowObject, tableId) {
    const pkCol = getPkCol(tableId);
    if (pkCol) {
        return rowObject[pkCol];
    } else {
        return null;
    }
};

const getPkCol = function (tableId) {
    if (tableId === 'genes_table') {
        return 'gene_pk';
    } else if (tableId === 'proteins_table') {
        return 'protein_pk';
    } else if (tableId === 'compounds_table') {
        return 'compound_pk';
    } else if (tableId === 'reactions_table') {
        return 'reaction_pk';
    } else if (tableId === 'pathways_table') {
        return 'pathway_pk';
    }
    return null;
}

const getDisplayName = function (rowObject, tableId) {
    const displayNameCol = getDisplayNameCol(tableId);
    if (displayNameCol) {
        return rowObject[displayNameCol];
    } else {
        return null;
    }
};

const getDisplayNameCol = function (tableId) {
    if (tableId === 'genes_table') {
        return 'gene_id';
    } else if (tableId === 'proteins_table') {
        return 'protein_id';
    } else if (tableId === 'compounds_table') {
        return 'compound_id';
    } else if (tableId === 'reactions_table') {
        return 'reaction_id';
    } else if (tableId === 'pathways_table') {
        return 'pathway_id';
    }
    return null;
}

const getRowObj = function (tableName, selectedValue) {
    const tableAPI = $('#' + tableName).DataTable();
    const item = '#' + selectedValue;
    const row = tableAPI.row(item);
    const rowIndex = tableAPI.rows()[0].indexOf(row.index());

    if (rowIndex != -1) {
        const node = $(row.node());
        const data = row.data();
        return {
            tableName: tableName,
            selectedValue: selectedValue,
            rowIndex: rowIndex,
            node: node,
            data: data
        }
    }
    return null;
};

const getIndexToPos = function (tableName) {
    const tableAPI = $('#' + tableName).DataTable();
    const rowPos = tableAPI.rows()[0];
    const result = rowPos.reduce((acc, cur, idx) => {
        acc[cur] = idx;
        return acc
    }, {});
    return result;
}

const goToPage = function (rowObj) {
    const tableName = rowObj.tableName;
    const rowIndex = rowObj.rowIndex;
    const tableAPI = $('#' + tableName).DataTable();
    const pageInfo = tableAPI.page.info();
    const thePage = Math.floor(rowIndex / pageInfo['length']);
    tableAPI.page(thePage).draw('page');
}

export {
    isTableVisible,
    goToPage,
    getIndexToPos,
    getRowObj,
    getDisplayName,
    getDisplayNameCol,
    getPkValue,
    getPkCol
}