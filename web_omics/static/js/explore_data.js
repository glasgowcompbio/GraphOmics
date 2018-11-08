import Linker from './linker.js';
require('../css/linker.css');
require('webpack-jquery-ui');
require('webpack-jquery-ui/css');
const Clustergrammer = require('clustergrammer');
require('../css/summary.css');
import check_setup_enrichr from './enrichrgram';

const baseUrl = 'http://localhost:8000/linker/get_short_info/';
const seenData = {};

function renderHeatmap(elementId, dataType, clusterJson) {
    if (clusterJson.hasOwnProperty(dataType) && clusterJson[dataType]) {
        $(elementId).text('');
        $(elementId).addClass('heatmap_container');
        const jsonData = JSON.parse(clusterJson[dataType]);
        const rowTipCallback = {
            'gene': getGeneInfo,
            'protein': getProteinInfo,
            'compound': getCompoundInfo
        }
        const args = {
            root: elementId,
            network_data: jsonData,
            // opacity_scale: 'linear',
            row_tip_callback: rowTipCallback[dataType],
            col_tip_callback: testColCallback,
            tile_tip_callback: testTileCallback,
            dendro_callback: dendroCallback
        };
        const cgm = Clustergrammer(args);
        // TODO: buggy modal dialog!!
        // if (dataType === 'gene') {
        //     check_setup_enrichr(cgm);
        // }
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
    var url = baseUrl + dataType + '/' + displayName;
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

$(document).ready(function () {

    let pqr = Linker.init(data);

    // see https://docs.djangoproject.com/en/dev/ref/csrf/#ajax
    // using jQuery
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    var csrftoken = getCookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // TODO: shouldn't put this in global scope
    window.annotate = function(annotationId, annotationUrl, displayName) {
        $('#annotationId').val(`annotation-${annotationId}`);
        let annotation = $(`#annotation-${annotationId}`).text();
        if (annotation.length > 0) {
            annotation = annotation.split(':')[1].trim();
        }
        $('#displayName').val(displayName);
        $('#annotationValue').val(annotation);
        $('#annotationForm').attr('action', annotationUrl);
        $('#annotationDialog').dialog({
            modal: true,
            width: 460,
        });
    }

    $('#annotationSubmit').on('click', function (e) {
        const form = $('#annotationForm');
        const action = form.attr('action');
        const data = form.serialize();
        $.ajax({
            type: 'POST',
            url: action,
            data: data,
            success: function () {
                const annotId = $('#annotationId').val();
                const annotValue = $('#annotationValue').val();
                const annotHtml = `<p><strong>Annotation:</strong> ${annotValue}</p>`;
                $(`#${annotId}`).html(annotHtml);
                $('#annotationDialog').dialog('close');
            }
        });
    });

    renderHeatmap('#summary-vis-gene', 'genes', clusterJson);
    renderHeatmap('#summary-vis-protein', 'proteins', clusterJson);
    renderHeatmap('#summary-vis-compound', 'compounds', clusterJson);

});