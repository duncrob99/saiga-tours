const DateTime = luxon.DateTime;
document.querySelector('[name="content"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="title"]').parentElement.style.display = 'none';

let date_picker;

let csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]');

function updateContentFormField() {
    document.querySelector('[name="content"]').value = document.querySelector('#content').innerHTML;
}

function make_images_fullsize() {
    document.querySelectorAll(`#content img`).forEach(img => {
        if (img.hasAttribute('full-size-src')) {
            img.setAttribute('src', img.getAttribute('full-size-src'));
        }
    });
}

function activateEditor() {
    make_images_fullsize();

    document.querySelector('#content').setAttribute('contenteditable', true);
    // document.querySelector('#date').setAttribute('contenteditable', true);

    let editor = createEditor('content');

    editor.on('saveSnapshot', updateContentFormField);
    document.querySelector('#content').addEventListener('input', updateContentFormField);

    let title_input = document.querySelector('#title');
    let title_output = document.querySelector('[name="title"]');
    title_input.setAttribute('contenteditable', true);
    title_input.addEventListener('input', () => {
        title_output.value = title_input.innerText;
    })

    date_picker = new Litepicker({
        element: document.getElementById('date'),
    });

    date_picker.on('selected', (date) => {
        document.querySelector('#date').innerHTML = DateTime.fromJSDate(date.dateInstance).toLocaleString(DateTime.DATE_MED);
        console.log(DateTime.fromJSDate(date.dateInstance).toISODate());
        document.querySelector('#id_published_date').value = DateTime.fromJSDate(date.dateInstance).toISODate();
    });
}

function deactivateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', false);
    // document.querySelector('#date').setAttribute('contenteditable', false);
    if (Object.keys(CKEDITOR.instances).includes('content')) {
        CKEDITOR.instances['content'].destroy();
    }

    document.querySelector('#title').setAttribute('contenteditable', false);

    if (date_picker !== undefined) {
        date_picker.destroy();
    }

    minimise_images();
}

let editing = document.querySelector('#editing');
editing.checked = false;

function checkEditing() {
    if (editing.checked) {
        activateEditor();
    } else {
        deactivateEditor();
    }
}

checkEditing();
window.addEventListener('load', checkEditing);
editing.addEventListener('change', checkEditing);

window.addEventListener('load', () => {
    document.getElementById('edit-page-form').addEventListener('submit', () => {
        deactivateEditor();
        updateContentFormField();
    });
})
