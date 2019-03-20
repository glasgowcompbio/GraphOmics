import {FIRDI_UPDATE_EVENT, CLUSTERGRAMMER_UPDATE_EVENT} from "./common";

class GroupManager {

    constructor(saveButtonId, numSelectedId, linkerState, saveUrl) {
        // register observables
        this.linkerState = linkerState;
        this.linkerState.on(FIRDI_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data);
        });
        this.linkerState.on(CLUSTERGRAMMER_UPDATE_EVENT, (data) => {
            this.handleClustergrammerUpdate(data);
        })
        // register click handler
        this.numSelected = $(`#${numSelectedId}`);
        this.saveButton = $(`#${saveButtonId}`);
        this.saveButton.on('click', () => { this.showSaveDialog(); })
        this.saveUrl = saveUrl;
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
        $('#groupSubmit').on('click', () => {
            const form = $('#saveGroupForm');
            const action = form.attr('action');
            const data = form.serialize();
            $.ajax({
                type: 'POST',
                url: action,
                data: data,
                success: function () {
                    $('#saveGroupDialog').dialog('close');
                    $('#groupSubmit').off();
                    alert('Group successfully saved.');
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