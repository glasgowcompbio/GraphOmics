import {blockUI, CLUSTERGRAMMER_UPDATE_EVENT, FIRDI_UPDATE_EVENT, loadData, unblockUI} from "../common";
import Awesomplete from 'awesomplete-es6';

class GroupManager {

    constructor(rootStore, viewNames) {
        this.rootStore = rootStore;

        // set an initial linker state to be updated later
        this.rootStore.firdiStore.on(FIRDI_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data); // update selected item counter from Firdi
        });
        this.rootStore.cgmStore.on(CLUSTERGRAMMER_UPDATE_EVENT, (data) => {
            this.handleClustergrammerUpdate(data);  // update selected item counter from Clustergrammer
        })

        this.awesomeplete = undefined;
        this.selectedSuggestion = undefined;
        this.groupId = undefined;

        const numSelectedId = 'numSelected';
        this.numSelected = $(`#${numSelectedId}`);

        const saveButtonId = 'saveGroupButton';
        this.saveUrl = viewNames['save_group'];
        this.saveButton = $(`#${saveButtonId}`);
        this.saveButton.on('click', () => { this.showSaveDialog(); })

        const loadButtonId = 'loadGroupButton';
        this.loadUrl = viewNames['load_group'];
        this.loadButton = $(`#${loadButtonId}`);
        this.loadButton.on('click', () => { this.loadLinkerState(); })

        this.selectBoxId = 'group';
        const elem = document.getElementById(this.selectBoxId);
        this.listUrl = viewNames['list_groups'];
        this.updateList();
        this.checkSaveButtonStatus(this.rootStore.firdiStore.totalSelected);
        this.checkLoadButtonStatus(elem);

    }

    updateList() {
        loadData(this.listUrl).then(data => {
            if (this.awesomeplete) {
                this.awesomeplete.destroy();
            }
            const elem = document.getElementById(this.selectBoxId);
            const myList = data.list;
            const selectBox = new Awesomplete(elem, {
                list: myList,
                minChars: 0,
                replace: function(suggestion) {
                    this.input.value = suggestion.label; // https://github.com/LeaVerou/awesomplete/issues/17104
                }
            });
            $(elem).on('focus', () => { // https://github.com/LeaVerou/awesomplete/issues/16754
                elem.value = '';
                selectBox.evaluate();
            });
            $(elem).on('blur', () => {
                this.checkLoadButtonStatus(elem);
            });
            $(elem).on("awesomplete-selectcomplete", (e) => {
                const originalEvent = e.originalEvent;
                this.selectedSuggestion = originalEvent.selectedSuggestion;
                this.checkLoadButtonStatus(elem);
            });
            this.awesomeplete = selectBox;
        })
    }

    showGroupTab() {
        $('#pills-factor-tab').removeClass('d-none');
    }

    loadLinkerState() {
        blockUI();
        const groupId = this.selectedSuggestion.value;
        loadData(this.loadUrl, { 'groupId' : groupId }).then( data => {
            const newState = JSON.parse(data.state);
            this.rootStore.firdiStore.restoreSelection(newState);
            this.rootStore.firdiStore.notifyUpdate();
            this.numSelected.text(newState.totalSelected);
            this.groupId = groupId;
            this.showGroupTab();
            unblockUI();
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
            // copy current state
            const stateCopy = {};
            stateCopy.selections = self.rootStore.firdiStore.selections;
            stateCopy.whereType = self.rootStore.firdiStore.whereType;
            const stateJson = JSON.stringify(stateCopy);

            // create form data and POST it
            const form = $('#saveGroupForm');
            const action = form.attr('action');
            let formData = form.serializeArray();
            formData.push({'name': 'state', 'value': stateJson});
            $.ajax({
                type: 'POST',
                url: action,
                data: formData,
                success: function () {
                    $('#saveGroupDialog').dialog('close');
                    $('#groupSubmit').off();
                    window.setTimeout(function() {
                        alert('Group successfully saved.');
                    }, 1); // add a small delay before showing confirmation
                    self.updateList();
                }
            });
        });
    }

    handleFirdiUpdate(data) {
        console.log('SelectionManager receives update from Firdi');
        console.log(data);
        this.numSelected.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
    }

    handleClustergrammerUpdate(data) {
        console.log('SelectionManager receives update from Clustergrammer');
        console.log(data);
        this.numSelected.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
    }

    checkSaveButtonStatus(totalSelected) {
        if (totalSelected == 0) {
            this.saveButton.prop('disabled', true);
        } else {
            this.saveButton.prop('disabled', false);
            this.showGroupTab();
        }
    }

    checkLoadButtonStatus(elem) {
        if (elem.value === '') {
            this.loadButton.prop('disabled', true);
        } else {
            this.loadButton.prop('disabled', false);
        }
    }

}

export default GroupManager;