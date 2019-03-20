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

export { showAnnotateDialog, handleAnnotateSubmit }