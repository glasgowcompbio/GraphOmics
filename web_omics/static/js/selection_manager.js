import {FIRDI_UPDATE_EVENT, CLUSTERGRAMMER_UPDATE_EVENT} from "./common";

class SelectionManager {

    constructor(saveSelectionButton, loadSelectionButton, numSelected, linkerState) {
        this.saveSelectionButton = $(`#${saveSelectionButton}`);
        this.loadSelectionButton = $(`#${loadSelectionButton}`);
        this.numSelected = $(`#${numSelected}`);
        this.linkerState = linkerState;
        this.linkerState.on(FIRDI_UPDATE_EVENT, (data) => {
            this.handleFirdiUpdate(data);
        });
        this.linkerState.on(CLUSTERGRAMMER_UPDATE_EVENT, (data) => {
            this.handleClustergrammerUpdate(data);
        })
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

export default SelectionManager;