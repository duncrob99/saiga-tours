CKEDITOR.disableAutoInline = true;

document.querySelector('[name="content"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="title"]').parentElement.style.display = 'none';

let csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]');

CKEDITOR.stylesSet.add('img_styles', [
    {name: 'Cool image', element: 'img', attributes: {'class': 'cool-img'}}
])

function activateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', true);

    let editor = CKEDITOR.inline('content', {
        extraPlugins: 'sourcedialog, uploadimage, sharedspace',
        removePlugins: 'floatingspace, maximize, resize',
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
        stylesSet: 'img_styles',
        sharedSpaces: {
            top: 'editor-toolbar'
        }
    });

    editor.on('saveSnapshot', () => document.querySelector('[name="content"]').value = document.querySelector('#content').innerHTML);
    document.querySelector('#content').addEventListener('input', () => document.querySelector('[name="content"]').value = document.querySelector('#content').innerHTML);

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
editing.addEventListener('change', checkEditing);