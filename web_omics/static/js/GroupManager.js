import {FIRDI_UPDATE_EVENT, CLUSTERGRAMMER_UPDATE_EVENT, loadData, blockUI, unblockUI} from "./common";
import Awesomplete from 'awesomplete-es6';

class GroupManager {

    constructor(saveButtonId, loadButtonId, numSelectedId, selectBoxId,
                linkerState, saveUrl, loadUrl, listUrl) {

        // set an initial linker state to be updated later
        this.linkerState = linkerState;
        this.linkerState.on(FIRDI_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data); // update selected item counter from Firdi
        });
        this.linkerState.on(CLUSTERGRAMMER_UPDATE_EVENT, (data) => {
            this.handleClustergrammerUpdate(data);  // update selected item counter from Clustergrammer
        })

        this.saveUrl = saveUrl;
        this.loadUrl = loadUrl;
        this.listUrl = listUrl;

        this.numSelected = $(`#${numSelectedId}`);
        this.selectBoxId = selectBoxId;
        this.updateList();

        this.saveButton = $(`#${saveButtonId}`);
        this.saveButton.on('click', () => { this.showSaveDialog(); })

        this.loadButton = $(`#${loadButtonId}`);
        this.loadButton.on('click', () => { this.loadLinkerState(); })

    }

    updateList() {
        loadData(this.listUrl).then(data => {
            const elem = document.getElementById(this.selectBoxId);
            const myList = data.list;
            const selectBox = new Awesomplete(elem, {
                list: myList,
                minChars: 0,
            });
            $(elem).on('focus', () => { // https://github.com/LeaVerou/awesomplete/issues/16754
                selectBox.evaluate();
            });
        })
    }

    loadLinkerState() {
        const groupId = document.getElementById(this.selectBoxId).value;
        loadData(this.loadUrl, { 'groupId' : groupId }).then( data => {
            const newState = data.linkerState;
            this.linkerState.restore(newState);
        })
    }

    showSaveDialog() {
        // show dialog
        $('#groupName').val('');
        $('#groupDesc').val('');
        $('#saveGroupForm').attr('action', this.saveUrl);
        $('#saveGroupDialog').dialog({
            modal: true,
            width: 460,
        });
        const self = this;
        $('#groupSubmit').on('click', () => {
            const form = $('#saveGroupForm');
            const action = form.attr('action');
            let formData = form.serializeArray();
            formData.push({'name': 'linkerState', 'value': self.linkerState});
            const data = JSON.stringify(formData);
            $.ajax({
                type: 'POST',
                url: action,
                data: data,
                success: function () {
                    $('#saveGroupDialog').dialog('close');
                    $('#groupSubmit').off();
                    window.setTimeout(function() {
                        alert('Group successfully saved.');
                    }, 1); // add a small delay before showing confirmation
                }
            });
        });
    }

    handleFirdiUpdate(data) {
        console.log('SelectionManager receives update from Firdi');
        console.log(data);
        this.numSelected.text(data.totalSelected);
    }

    handleClustergrammerUpdate(data) {
        console.log('SelectionManager receives update from Clustergrammer');
        console.log(data);
        this.numSelected.text(data.totalSelected);
    }

}

export default GroupManager;