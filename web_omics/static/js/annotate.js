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

function showAnnotateDialog(annotationId, annotationUrl, displayName) {
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

function handleAnnotateSubmit(e) {
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
}

export { setupCsrfForAjax, showAnnotateDialog, handleAnnotateSubmit }