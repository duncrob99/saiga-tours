CKEDITOR.disableAutoInline = true;

document.querySelector('[name="content"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="title"]').parentElement.style.display = 'none';

let csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]');

CKEDITOR.stylesSet.add('styles', [
    {name: 'Above', element: 'img', attributes: {'class': 'above-img'}},
    {name: 'Below', element: 'img', attributes: {'class': 'below-img'}},
    {name: 'Bordered', element: 'img', attributes: {'class': 'bordered'}},
    {name: 'Underlined Title', element: 'h3', attributes: {'class': 'underlined-title'}},
    {name: 'Faded', element: 'p', attributes: {'class': 'faded'}},
    {name: 'Text block', element: 'p', attributes: {'class': 'block'}}
])

function updateContentFormField() {
    document.querySelector('[name="content"]').value = document.querySelector('#content').innerHTML;
}

function activateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', true);

    let editor = CKEDITOR.inline('content', {
        extraPlugins: 'sourcedialog, uploadimage, sharedspace, splitsection, imagefan',
        removePlugins: 'exportpdf',
        filebrowserImageBrowseUrl: '/ckeditor/browse/?csrfmiddlewaretoken=' + csrf_token,
        filebrowserImageUploadUrl: "/ckeditor/upload/?csrfmiddlewaretoken=" + csrf_token,
        image: {
            styles: {
                options: [{
                    name: 'cool',
                    title: 'Cool image',
                    className: 'cool-img',
                    modelElements: ['imageInline']
                }]
            }
        },
        stylesSet: 'styles',
        sharedSpaces: {
            top: 'editor-toolbar'
        }
    });

    customiseCK(editor);

    editor.on('saveSnapshot', updateContentFormField);
    document.querySelector('#content').addEventListener('input', updateContentFormField);

    let title_input = document.querySelector('#title');
    let title_output = document.querySelector('[name="title"]');
    title_input.setAttribute('contenteditable', true);
    title_input.addEventListener('input', () => {
        title_output.value = title_input.innerText;
    })
}

function deactivateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', false);
    if (Object.keys(CKEDITOR.instances).includes('content')) {
        CKEDITOR.instances['content'].destroy();
    }

    document.querySelector('#title').setAttribute('contenteditable', false);
}

let editing = document.querySelector('#editing');

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