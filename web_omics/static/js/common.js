import 'block-ui';

const isTableVisible = tableInfo => tableInfo["options"]["visible"];

// https://stackoverflow.com/questions/122102/what-is-the-most-efficient-way-to-deep-clone-an-object-in-javascript/5344074#5344074
const deepCopy = obj => JSON.parse(JSON.stringify(obj));

const getRowObj = function(tableName, selectedValue) {
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

export { isTableVisible, deepCopy, getRowObj, goToPage, blockUI, unblockUI }