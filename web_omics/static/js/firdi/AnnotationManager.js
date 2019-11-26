class AnnotationManager {

    constructor(state, annotId, annotUrl, displayName, annotation) {
        this.state = state;
        this.annotId = annotId;
        this.annotUrl = annotUrl;
        this.displayName = displayName;
        this.annotation = annotation;
    }

    getAnnotationLink() {
        const annotationLink = $('<button/>', {
            text: '📝',
            type: 'button',
            style: 'margin-left: 5px',
            class: 'btn btn-outline-primary btn-sm',
            click: () => { this.showAnnotateDialog(); }
        });
        return annotationLink;
    }

    getReactomeViewerLink() {
        const reactomeViewerLink = $('<button/>', {
            text: '🔍',
            type: 'button',
            style: 'margin-left: 5px',
            class: 'btn btn-outline-primary btn-sm',
            click: () => {
                this.showReactomeViewerDialog();
            }
        });
        return reactomeViewerLink;
    }

    getAnnotationDiv() {
        let annotationHtml = '';
        if (this.annotation.length > 0) {
            annotationHtml = `<p><strong>Annotation</strong>: ${this.annotation}</p>`
        }
        const annotationDiv = $('<div\>', {
            id: this.getDivAnnotId(),
            html: annotationHtml,
            class: 'annotation'
        });
        return annotationDiv;
    }

    showAnnotateDialog() {
        // show dialog
        let annotation = this.annotation;
        $('annotationId').val(this.annotId);
        $('#displayName').val(this.displayName);
        $('#annotationValue').val(annotation);
        $('#annotationForm').attr('action', this.annotUrl);
        $('#annotationDialog').dialog({
            modal: true,
            width: 460,
        });
        $('#annotationSubmit').on('click', () => {
            const divAnnotId = this.getDivAnnotId();
            const form = $('#annotationForm');
            const action = form.attr('action');
            const data = form.serialize();
            $.ajax({
                type: 'POST',
                url: action,
                data: data,
                success: function () {
                    this.annotation = $('#annotationValue').val();
                    const annotHtml = `<p><strong>Annotation:</strong> ${this.annotation}</p>`;
                    $(document.getElementById(divAnnotId)).html(annotHtml);
                    $('#annotationDialog').dialog('close');
                    $('#annotationSubmit').off();
                }
            });
        });
    }

    getDivAnnotId() {
        return `#annotation-${this.annotId}`;
    }

    showReactomeViewerDialog() {
        // show dialog
        $('#reactomeWidgetDialog').dialog({
            modal: true,
            width: 1000,
            height: 700
        });
        var diagram = Reactome.Diagram.create({
            "placeHolder" : "diagramHolder",
            "width" : 975,
            "height" : 600
        });

        //Initialising it to the currently selected pathway
        diagram.loadDiagram(this.annotId);
        diagram.onDiagramLoaded(function (loaded) {
            console.log('Diagram loaded');
            // diagram.flagItems('ENSMUSG00000001323')
        });
    }

}

export default AnnotationManager;