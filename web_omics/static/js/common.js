import 'block-ui';

const isTableVisible = tableInfo => tableInfo["options"]["visible"];

// https://stackoverflow.com/questions/122102/what-is-the-most-efficient-way-to-deep-clone-an-object-in-javascript/5344074#5344074
const deepCopy = obj => JSON.parse(JSON.stringify(obj));

const getPkValue = function(rowObject, tableId) {
    if (tableId === 'genes_table') {
        return rowObject['gene_pk'];
    } else if (tableId === 'proteins_table') {
        return rowObject['protein_pk'];
    } else if (tableId === 'compounds_table') {
        return rowObject['compound_pk'];
    } else if (tableId === 'reactions_table') {
        return rowObject['reaction_pk'];
    } else if (tableId === 'pathways_table') {
        return rowObject['pathway_pk'];
    }
    return null;
};

const getDisplayName = function(rowObject, tableId) {
    const displayNameCol = getDisplayNameCol(tableId);
    if (displayNameCol) {
        return rowObject[displayNameCol];
    } else {
        return null;
    }
};

const getDisplayNameCol = function(tableId) {
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

const getRowObj = function(tableName, selectedValue, indexToPos, selectionRowIndex) {
    const tableAPI = $('#' + tableName).DataTable();
    const item = '#' + selectedValue;
    const row = tableAPI.row(item);
    let rowIndex = null;
    if (typeof indexToPos !== 'undefined') {
        rowIndex = indexToPos[selectionRowIndex];
    } else {
        rowIndex = tableAPI.rows()[0].indexOf(row.index());
    }

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

const getIndexToPos = function(tableName) {
    const tableAPI = $('#' + tableName).DataTable();
    const rowPos = tableAPI.rows()[0];
    const result = rowPos.reduce((acc, cur, idx) => {
        acc[cur] = idx;
        return acc
    }, {});
    return result;
}

const goToPage = function(rowObj) {
    const tableName = rowObj.tableName;
    const rowIndex = rowObj.rowIndex;
    const tableAPI = $('#' + tableName).DataTable();
    const pageInfo = tableAPI.page.info();
    const thePage = Math.floor(rowIndex / pageInfo['length']);
    tableAPI.page(thePage).draw('page');
}

const blockUI = function() {
    $('#all_tables').block({
        centerY: 0,
        message: '<h5>Please wait ...</h5>',
        css: {
            top: '10px',
            left: '',
            right: '10px',
            border: 'none',
            padding: '15px',
            backgroundColor: '#000',
            '-webkit-border-radius': '10px',
            '-moz-border-radius': '10px',
            opacity: .5,
            color: '#fff'
        }
    });
};

const unblockUI = function() {
    $('#all_tables').unblock();
};

const FIRDI_UPDATE_EVENT = 0;
const CLUSTERGRAMMER_UPDATE_EVENT = 1;

export {
    isTableVisible,
    deepCopy,
    getPkValue,
    getDisplayName,
    getDisplayNameCol,
    getRowObj,
    getIndexToPos,
    goToPage,
    blockUI,
    unblockUI,
    FIRDI_UPDATE_EVENT,
    CLUSTERGRAMMER_UPDATE_EVENT
}