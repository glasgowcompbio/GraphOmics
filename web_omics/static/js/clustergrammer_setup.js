import 'bootstrap';
import Clustergrammer from './clustergrammer/main';
import check_setup_enrichr from './enrichrgram';

const seenData = {};

function renderHeatmap(elementId, dataType, clusterJson) {
    if (clusterJson.hasOwnProperty(dataType) && clusterJson[dataType]) {
        $(elementId).text('');
        $(elementId).addClass('heatmap_container');
        const jsonData = JSON.parse(clusterJson[dataType]);
        const rowTipCallback = {
            'genes': getGeneInfo,
            'proteins': getProteinInfo,
            'compounds': getCompoundInfo
        }
        const about_string = 'Zoom, scroll, and click buttons to interact with the clustergram. <a href="http://amp.pharm.mssm.edu/clustergrammer/help"> <i class="fa fa-question-circle" aria-hidden="true"></i> </a>';
        const args = {
            root: elementId,
            network_data: jsonData,
            about: about_string,
            row_tip_callback: rowTipCallback[dataType],
            col_tip_callback: testColCallback,
            tile_tip_callback: testTileCallback,
            dendro_callback: dendroCallback,
            sidebar_width: 200
        };
        const cgm = Clustergrammer(args);
        // TODO: still broken!!
        if (dataType === 'genes') {
            check_setup_enrichr(cgm);
        }
    } else {
        $(elementId).text('No data is available.');
    }
}

function getGeneInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'gene');
}

function getProteinInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'protein');
}

function getCompoundInfo(rootTip, rowData) {
    getInfo(rootTip, rowData, 'compound');
}

function getInfo(rootTip, rowData, dataType) {
    let displayName = rowData.name;
    if (displayName.indexOf(' ') > 0) {
        displayName = displayName.split(' ')[0];
    } else if (displayName.indexOf('_') > 0) {
        displayName = displayName.split('_')[0];
    }
    if (_.has(seenData, displayName)) {
        const cachedData = seenData[displayName];
        setTooltip(cachedData, rootTip, displayName);
    } else {
        setTimeout(getMouseOver, 250, rootTip, displayName, dataType);
    }
}

function setTooltip(data, rootTip, displayName) {
    if (data.name != undefined) {
        d3.selectAll(rootTip + '_row_tip')
            .html(function () {
                var symName = displayName + ': ' + data.name;
                var fullHtml = `<p>${symName}</p><p>${data.description}</p>`;
                return fullHtml;
            });
    }
}

function getMouseOver(rootTip, displayName, dataType) {
    // not sure if this is necessary
    if (d3.select(rootTip + '_row_tip').classed(displayName)) {
        getRequest(rootTip, displayName, dataType);
    }
}

function getRequest(rootTip, displayName, dataType) {
    const params = $.param({
        'data_type': dataType,
        'display_name': displayName
    });
    const url = baseUrl + '?' + params;
    $.get(url, function (data) {
        // save data for repeated use
        seenData[displayName] = {}
        seenData[displayName].name = data.name;
        seenData[displayName].description = data.description;
        setTooltip(data, rootTip, displayName);
        return data;
    });
}

function testTileCallback(tile_data) {
    var row_name = tile_data.row_name;
    var col_name = tile_data.col_name;
    console.log(`tile_callback ${row_name} ${col_name}`);
}

function testColCallback(col_data) {
    var col_name = col_data.name;
    console.log(`col_callback ${col_name}`);
}

function dendroCallback(instSelection) {
    var instRc;
    var instData = instSelection.__data__;
    // TODO: buggy modal dialog!!
    // toggle enrichr export section
    // if (instData.instRc === 'row') {
    //     d3.select('.enrichr_export_section')
    //         .style('display', 'block');
    // } else {
    //     d3.select('.enrichr_export_section')
    //         .style('display', 'none');
    // }
}

export default renderHeatmap;