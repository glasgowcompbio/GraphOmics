class AnnotationManager {

    constructor(state, annotId, annotUrl, displayName, annotation,
                reactomeOraToken, reactomeExprToken) {
        this.state = state;
        this.annotId = annotId;
        this.annotUrl = annotUrl;
        this.displayName = displayName;
        this.annotation = annotation;
        this.reactomeOraToken = reactomeOraToken;
        this.reactomeExprToken = reactomeExprToken;
        this.loaded = false;
    }

    getAnnotationLink() {
        const annotationLink = $('<button/>', {
            text: '📝 Annotate',
            type: 'button',
            style: 'margin-top: 5px',
            class: 'btn btn-primary btn-sm',
            click: () => { this.showAnnotateDialog(); }
        });
        return annotationLink;
    }

    getReactomeOraViewerLink() {
        if (this.reactomeOraToken === undefined) {
            return;
        }
        const reactomeViewerLink = $('<button/>', {
            text: '🔍 Show Pathway (with Reactome ORA results)',
            type: 'button',
            style: 'margin-top: 5px',
            class: 'btn btn-primary btn-sm',
            click: () => {
                this.showReactomeViewerDialog(this.reactomeOraToken);
            }
        });
        return reactomeViewerLink;
    }

    getReactomeExprViewerLink() {
        if (this.reactomeExprToken === undefined) {
            return;
        }
        let text = '🔍 Show Pathway';
        if (this.reactomeExprToken) {
            text = '🔍 Show Pathway (with expression data)'
        }
        const reactomeViewerLink = $('<button/>', {
            text: text,
            type: 'button',
            style: 'margin-top: 5px',
            class: 'btn btn-primary btn-sm',
            click: () => {
                this.showReactomeViewerDialog(this.reactomeExprToken);
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

    showReactomeViewerDialog(token) {
        // show dialog
        $('#reactomeWidgetDialog').dialog({
            modal: true,
            width: 1000,
            height: 700
        });
        const diagram = Reactome.Diagram.create({
            "placeHolder" : "diagramHolder",
            "width" : 975,
            "height" : 600
        });

        //Initialising it to the currently selected pathway, if not loaded
        if (!this.loaded) {
            console.log('Load diagram for ' + this.annotId + ' using reactome token: ' + token);
            diagram.loadDiagram(this.annotId);
            diagram.setAnalysisToken(token, 'TOTAL');
            this.loaded = true;
        } else { // already loaded. just change the overlay
            console.log('Reset overlay using reactome token: ' + token);
            diagram.resetAnalysis();
            diagram.setAnalysisToken(token, 'TOTAL');
        }
    }

}

export default AnnotationManager;