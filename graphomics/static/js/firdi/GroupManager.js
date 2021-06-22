import {
    blockFirdiTable,
    blockUI,
    GROUP_LOADED_EVENT,
    GROUP_UPDATED_EVENT,
    LAST_CLICKED_GROUP_MANAGER,
    loadData,
    postData, QUERY_FILTER_EVENT, SELECT_ALL_EVENT,
    SELECTION_UPDATE_EVENT,
    setupCsrfForAjax,
    unblockFirdiTable,
    unblockUI
} from "../common";
import Awesomplete from 'awesomplete-es6';

class GroupManager {

    constructor(rootStore, viewNames) {
        this.rootStore = rootStore;

        // set an initial linker state to be updated later
        this.rootStore.firdiStore.on(SELECTION_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data); // a new item is selected from Firdi
        });
        this.rootStore.firdiStore.on(GROUP_LOADED_EVENT, (data) => {
            this.handleFirdiUpdate(data); // a new group is loaded by clicking 'Load Group'
        });
        this.rootStore.groupStore.on(GROUP_UPDATED_EVENT, (data) => {
            this.handleGroupUpdate(data); // group information has been reset by calling GroupStore.reset()
        });
        this.rootStore.firdiStore.on(QUERY_FILTER_EVENT, (data) => {
            this.handleFirdiUpdate(data); // a new item is selected from Firdi
        });
        this.rootStore.firdiStore.on(SELECT_ALL_EVENT, (data) => {
            this.handleFirdiUpdate(data); // a new item is selected from Firdi
        });

        this.awesomeplete = undefined; // drop down for group selection
        this.selectedSuggestion = undefined; // currently selected Suggestion object from awesomeplete
        this.selectedTarget = undefined; // currently selected target DOM that generates the Suggestion above

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

        const boxplotResultId = 'groupResult';
        this.boxplotResultElem = $(`#${boxplotResultId}`);
        this.boxplotCardId = 'groupAnalysis';

        const goButtonId = 'getGoButton';
        this.goUrl = viewNames['get_gene_ontology'];
        this.goButtonElem = $(`#${goButtonId}`);
        this.goButtonElem.on('click', () => {
            this.getGeneOntology();
        })

        const goResultId = 'groupResult';
        this.goResultElem = $(`#${goResultId}`);
        this.goCardId = 'groupAnalysis';
    }

    updateList() {
        loadData(this.listUrl).then(data => {
            const elem = document.getElementById(this.selectBoxId);
            if (elem === null) {
                return;
            }
            if (this.awesomeplete) {
                this.awesomeplete.destroy();
            }
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
                this.selectedTarget = e.target;
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
        const params = this.prepareParams();
        const dataType = $('input[name=boxplotRadioOptions]:checked').val();
        params.dataType = dataType;

        // pass params via POST and set the result to HTML
        postData(this.boxplotUrl, params).then(data => {
            self.boxplotResultElem.html(data.div);
            unblockUI(`#${this.boxplotCardId}`);
        })
    }

    getGeneOntology() {
        blockUI(`#${this.goCardId}`);
        const self = this;

        // construct params
        const params = this.prepareParams();
        const namespace = $('input[name=goRadioOptions]:checked').val();
        params.namespace = namespace;

        // pass params via POST and set the result to HTML
        postData(this.goUrl, params).then(data => {
            self.goResultElem.html(data.div);
            unblockUI(`#${this.goCardId}`);
        })
    }

    prepareParams() {
        setupCsrfForAjax()
        const params = {
            groupId: this.rootStore.groupStore.groupId,
        };

        // if no groupId then this selection group has not been saved
        // in this case, we have to pass the entire data to the view
        // this can be potentially large!!
        if (params.groupId === null) {
            params.lastQueryResult = JSON.stringify(this.rootStore.firdiStore.queryResult)
        }
        return params;
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
        if (data.groupId === null) {
            this.selectedSuggestion = null;
            if (this.selectedTarget !== undefined) { // no group has been selected yet
                this.selectedTarget.value = null;
            }
        }

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
        if (elem !== null) {
            const disabled = elem.value === '' ? true : false;
            this.loadButtonElem.prop('disabled', disabled);
        }
    }

}

export default GroupManager;