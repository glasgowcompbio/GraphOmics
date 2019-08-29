import {
    blockFirdiTable,
    blockUI,
    GROUP_LOADED_EVENT,
    GROUP_UPDATED_EVENT,
    LAST_CLICKED_GROUP_MANAGER,
    loadData,
    postData,
    setupCsrfForAjax,
    SELECTION_UPDATE_EVENT,
    unblockFirdiTable,
    unblockUI
} from "../common";
import Awesomplete from 'awesomplete-es6';

class GroupManager {

    constructor(rootStore, viewNames) {
        this.rootStore = rootStore;

        // set an initial linker state to be updated later
        this.rootStore.firdiStore.on(SELECTION_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data); // update selected item counter from Firdi
        });
        this.rootStore.firdiStore.on(GROUP_LOADED_EVENT, (data) => {
            this.handleFirdiUpdate(data); // update selected item counter from Firdi
        });
        this.rootStore.groupStore.on(GROUP_UPDATED_EVENT, (data) => {
            this.handleGroupUpdate(data); // update group id and name
        });

        this.awesomeplete = undefined;
        this.selectedSuggestion = undefined;

        const numSelectedId = 'numSelected';
        this.numSelectedElem = $(`#${numSelectedId}`);

        const groupTab = 'pills-factor-tab';
        const groupId = 'groupId';
        const groupName = 'groupName';
        const groupDesc = 'groupDesc';
        const timestamp = 'timestamp';
        this.groupTabElem = $(`#${groupTab}`);
        this.groupIdElem = $(`#${groupId}`);
        this.groupNameElem = $(`#${groupName}`);
        this.groupDescElem = $(`#${groupDesc}`);
        this.timestampElem = $(`#${timestamp}`);

        const numGenesId = 'numGenes';
        const numProteinsId = 'numProteins';
        const numCompoundsId = 'numCompounds';
        const numReactionsId = 'numReactions';
        const numPathwaysId = 'numPathways';
        this.numGenesElem = $(`#${numGenesId}`);
        this.numProteinsElem = $(`#${numProteinsId}`);
        this.numCompoundsElem = $(`#${numCompoundsId}`);
        this.numReactionsElem = $(`#${numReactionsId}`);
        this.numPathwaysElem = $(`#${numPathwaysId}`);

        const saveButtonId = 'saveGroupButton';
        this.saveUrl = viewNames['save_group'];
        this.saveButtonElem = $(`#${saveButtonId}`);
        this.saveButtonElem.on('click', () => {
            this.showSaveDialog();
        })

        const loadButtonId = 'loadGroupButton';
        this.loadUrl = viewNames['load_group'];
        this.loadButtonElem = $(`#${loadButtonId}`);
        this.loadButtonElem.on('click', () => {
            this.loadLinkerState();
        })

        this.selectBoxId = 'group';
        const selectBoxElem = document.getElementById(this.selectBoxId);
        this.listUrl = viewNames['list_groups'];
        this.updateList();
        this.checkSaveButtonStatus(this.rootStore.firdiStore.totalSelected);
        this.checkLoadButtonStatus(selectBoxElem);

        const boxplotButtonId = 'getBoxplotButton';
        this.boxplotUrl = viewNames['get_boxplot'];
        this.boxplotButtonElem = $(`#${boxplotButtonId}`);
        this.boxplotButtonElem.on('click', () => {
            this.getBoxplot();
        })

        const boxplotResultId = 'boxplotResult';
        this.boxplotResultElem = $(`#${boxplotResultId}`);
        this.boxplotCardId = 'groupAnalysis';

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
                replace: function (suggestion) {
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

    loadLinkerState() {
        blockFirdiTable();
        const groupId = this.selectedSuggestion.value;
        const self = this;
        loadData(this.loadUrl, {'groupId': groupId}).then(data => {
            self.rootStore.lastClicked = LAST_CLICKED_GROUP_MANAGER;
            self.rootStore.groupStore.restoreState(data);
            unblockFirdiTable();
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
            stateCopy.lastQueryResult = self.rootStore.firdiStore.queryResult;
            const stateJson = JSON.stringify(stateCopy);

            // create form data and POST it
            const form = $('#saveGroupForm');
            const action = form.attr('action');
            let formData = form.serializeArray(); // this includes groupName and groupDesc
            formData.push({
                'name': 'state',
                'value': stateJson
            });
            $.ajax({
                type: 'POST',
                url: action,
                data: formData,
                success: function () {
                    $('#saveGroupDialog').dialog('close');
                    $('#groupSubmit').off();
                    window.setTimeout(function () {
                        alert('Group successfully saved.');
                    }, 1); // add a small delay before showing confirmation
                    self.updateList();
                }
            });
        });
    }

    getBoxplot() {
        blockUI(`#${this.boxplotCardId}`);
        const self = this;

        // construct params
        const dataType = $('input[name=boxplotRadioOptions]:checked').val();
        const params = {
            groupId: this.rootStore.groupStore.groupId,
            dataType: dataType,
        };

        // if no groupId then this selection group has not been saved
        // in this case, we have to pass the entire data to the view
        // this can be potentially large!!
        if (params.groupId === null) {
            params.lastQueryResult = JSON.stringify(this.rootStore.firdiStore.queryResult)
        }

        // pass params via POST and set the result to HTML
        setupCsrfForAjax()
        postData(this.boxplotUrl, params).then(data => {
            self.boxplotResultElem.html(data.div);
            unblockUI(`#${this.boxplotCardId}`);
        })
    }

    handleFirdiUpdate(data) {
        console.log('Firdi --> GroupManager');
        this.numSelectedElem.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
    }

    handleClustergrammerUpdate(data) {
        console.log('Clustergrammer --> GroupManager');
        this.numSelectedElem.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
    }

    handleGroupUpdate(data) {
        console.log('GroupStore --> GroupManager');
        if (this.rootStore.firdiStore.totalSelected > 0) {
            this.groupTabElem.removeClass('d-none');
        } else {
            this.groupTabElem.addClass('d-none');
        }

        this.groupIdElem.text(data.groupId);
        this.groupNameElem.text(data.groupName);
        this.groupDescElem.text(data.groupDesc);
        this.timestampElem.text(data.timestamp);

        const obsCount = data.numObservedEntities;
        this.numGenesElem.text(obsCount['genes']);
        this.numProteinsElem.text(obsCount['proteins']);
        this.numCompoundsElem.text(obsCount['compounds']);
        this.numReactionsElem.text(obsCount['reactions']);
        this.numPathwaysElem.text(obsCount['pathways']);
    }

    checkSaveButtonStatus(totalSelected) {
        const disabled = totalSelected == 0 ? true : false;
        this.saveButtonElem.prop('disabled', disabled);
    }

    checkLoadButtonStatus(elem) {
        const disabled = elem.value === '' ? true : false;
        this.loadButtonElem.prop('disabled', disabled);
    }

}

export default GroupManager;