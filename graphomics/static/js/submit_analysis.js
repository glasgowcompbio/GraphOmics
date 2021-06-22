import {blockUI} from './common';

$(document).ready(function () {

    // https://stackoverflow.com/questions/15671335/prevent-multiple-form-submissions-in-django
    function isFormHtml5Valid(form) {
        for (const el of form.querySelectorAll('input,textarea,select')) {
            if (!el.checkValidity())
                return false;
        }
        return true;
    }

    const buttonId = 'submitBtn';
    const buttonElem = $(`#${buttonId}`);
    buttonElem.on('click', () => {
        const myForm = document.getElementById('analysis_form');
        if (isFormHtml5Valid(myForm)) {
            buttonElem.attr("disabled", true);
            $('#collapseExample1').removeClass('show');
            $('#collapseExample2').removeClass('show');
            blockUI('#main-form');
            myForm.submit();
        }
    })

});