import {
    blockFirdiTable,
    blockUI,
    GROUP_LOADED_EVENT,
    HEATMAP_CLICKED_EVENT,
    LAST_CLICKED_GROUP_MANAGER,
    loadData,
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
        this.rootStore.cgmStore.on(HEATMAP_CLICKED_EVENT, (data) => {
            this.handleClustergrammerUpdate(data); // update selected item counter from cgm
        });

        this.awesomeplete = undefined;
        this.selectedSuggestion = undefined;

        const numSelectedId = 'numSelectedElem';
        this.numSelectedElem = $(`#${numSelectedId}`);

        const groupId = 'groupId';
        const groupName = 'groupName';
        const groupTab = 'pills-factor-tab';
        this.groupIdElem = $(`#${groupId}`);
        this.groupNameElem = $(`#${groupName}`);
        this.groupTabElem = $(`#${groupTab}`);

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
        this.saveButtonElem.on('click', () => { this.showSaveDialog(); })

        const loadButtonId = 'loadGroupButton';
        this.loadUrl = viewNames['load_group'];
        this.loadButtonElem = $(`#${loadButtonId}`);
        this.loadButtonElem.on('click', () => { this.loadLinkerState(); })

        this.selectBoxId = 'group';
        const selectBoxElem = document.getElementById(this.selectBoxId);
        this.listUrl = viewNames['list_groups'];
        this.updateList();
        this.checkSaveButtonStatus(this.rootStore.firdiStore.totalSelected);
        this.checkLoadButtonStatus(selectBoxElem);

        const boxplotButtonId = 'getBoxplotButton';
        this.boxplotUrl = viewNames['get_boxplot'];
        this.boxplotButtonElem = $(`#${boxplotButtonId}`);
        this.boxplotButtonElem.on('click', () => { this.getBoxplot(); })

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

    loadLinkerState() {
        blockFirdiTable();
        this.rootStore.groupId = this.selectedSuggestion.value;
        this.rootStore.groupName = this.selectedSuggestion.label;

        const self = this;
        loadData(this.loadUrl, { 'groupId' : this.rootStore.groupId }).then( data => {
            const newState = JSON.parse(data.state);
            self.rootStore.lastClicked = LAST_CLICKED_GROUP_MANAGER;
            self.rootStore.firdiStore.restoreSelection(newState);
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

    getBoxplot() {
        blockUI(`#${this.boxplotCardId}`);
        const dataType = $('input[name=boxplotRadioOptions]:checked').val();
        const self = this;
        loadData(this.boxplotUrl, {
            'groupId' : this.rootStore.groupId,
            'dataType': dataType,
        }).then( data => {
            // console.log(data);
            self.boxplotResultElem.html(data.div);
            unblockUI(`#${this.boxplotCardId}`);
        })
    }

    handleFirdiUpdate(data) {
        console.log('Firdi --> GroupManager');
        this.numSelectedElem.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
        this.showGroupTab(data.totalSelected, data.queryResult);
    }

    handleClustergrammerUpdate(data) {
        console.log('Clustergrammer --> GroupManager');
        this.numSelectedElem.text(data.totalSelected);
        this.checkSaveButtonStatus(data.totalSelected);
        this.showGroupTab(data.totalSelected, data.queryResult);
    }

    showGroupTab(totalSelected, queryResult) {
        if (totalSelected > 0){
            this.groupTabElem.removeClass('d-none');
            this.groupIdElem.text(this.rootStore.groupId);
            this.groupNameElem.text(this.rootStore.groupName);

            this.rootStore.observedEntities['genes'] = this.getObservedEntities(queryResult.genes_table);
            this.rootStore.observedEntities['proteins'] = this.getObservedEntities(queryResult.proteins_table);
            this.rootStore.observedEntities['compounds'] = this.getObservedEntities(queryResult.compounds_table);
            this.rootStore.observedEntities['reactions'] = this.getObservedEntities(queryResult.reactions_table);
            this.rootStore.observedEntities['pathways'] = this.getObservedEntities(queryResult.pathways_table);

            this.numGenesElem.text(this.rootStore.observedEntities['genes'].length);
            this.numProteinsElem.text(this.rootStore.observedEntities['proteins'].length);
            this.numCompoundsElem.text(this.rootStore.observedEntities['compounds'].length);
            this.numReactionsElem.text(this.rootStore.observedEntities['reactions'].length);
            this.numPathwaysElem.text(this.rootStore.observedEntities['pathways'].length);
        }
    }

    getObservedEntities(result) {
        // count rows where obs is either true (for genes, proteins and compounds) or null (for reactions and pathways)
        return (result.filter(x => (x.obs == true) || (x.obs == null)))
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