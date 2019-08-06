import 'block-ui';

async function loadData(viewUrl, params) {
    try {
        const result = await $.getJSON(viewUrl, params);
        return result;
    } catch (e) {
        console.log(e);
    }
}

// https://stackoverflow.com/questions/122102/what-is-the-most-efficient-way-to-deep-clone-an-object-in-javascript/5344074#5344074
const deepCopy = obj => JSON.parse(JSON.stringify(obj));

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

function setupCsrfForAjax() {
    var csrftoken = getCookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

const FIRDI_UPDATE_EVENT = 0;
const CLUSTERGRAMMER_UPDATE_EVENT = 1;
const FIRDI_LOADED_EVENT = 2;

export {
    loadData,
    deepCopy,
    blockUI,
    unblockUI,
    setupCsrfForAjax,
    FIRDI_UPDATE_EVENT,
    CLUSTERGRAMMER_UPDATE_EVENT,
    FIRDI_LOADED_EVENT
}