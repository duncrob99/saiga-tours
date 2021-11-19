const DateTime = luxon.DateTime;

CKEDITOR.disableAutoInline = true;
let desc = document.querySelector('#tour-desc');
desc.setAttribute('contenteditable', true);

document.querySelector('[name="description"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="name"]').parentElement.style.display = 'none';
document.querySelector('[name="start_date"]').parentElement.style.display = 'none';
document.querySelector('[name="end_date"]').parentElement.style.display = 'none';
document.querySelector('[name="price"]').parentElement.style.display = 'none';

let csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]');

CKEDITOR.stylesSet.add('img_styles', [
    {name: 'Cool image', element: 'img', attributes: {'class': 'cool-img'}}
])

let rich_field_map = {
    'tour-desc': document.querySelector('textarea[name="description"]'),
}

let poor_field_map = {
    'title': 'id_name',
    'price': 'id_price'
}

let num_days_forms = document.querySelector('#id_itinerary-TOTAL_FORMS').value;
for (let i = 0; i < num_days_forms; i++) {
    rich_field_map[`day-${i + 1}-body`] = document.querySelector(`#id_itinerary-${i}-body`);
    poor_field_map[`day-${i + 1}-title`] = `id_itinerary-${i}-title`;
    poor_field_map[`day-${i + 1}-day`] = `id_itinerary-${i}-day`;
}
let start_picker;
let end_picker;

function deactivateEditor() {
    for (let editor_name in rich_field_map) {
        console.log(`deactivating ${editor_name}`);
        document.querySelector(`#${editor_name}`).setAttribute('contenteditable', false);
        if (Object.keys(CKEDITOR.instances).includes(editor_name)) {
            CKEDITOR.instances[editor_name].destroy();
        }
    }

    for (let input_id in poor_field_map) {
        let input_field = document.querySelector(`#${input_id}`);
        input_field.setAttribute('contenteditable', false);
    }

    document.querySelector('#create-day').setAttribute('hidden', 'hidden');
    document.querySelector('#delete-day').setAttribute('hidden', 'hidden');

    if (start_picker !== undefined) {
        start_picker.destroy();
    }
    if (end_picker !== undefined) {
        end_picker.destroy();
    }
}

function activateEditor() {
    for (let editor_name in rich_field_map) {
        console.log(`activating ${editor_name}`);
        document.querySelector(`#${editor_name}`).setAttribute('contenteditable', true);
        let editor = CKEDITOR.inline(editor_name, {
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
        editor.on('saveSnapshot', () => rich_field_map[editor_name].value = document.querySelector(`#${editor_name}`).innerHTML);
        document.querySelector(`#${editor_name}`).addEventListener('input', () => rich_field_map[editor_name].value = document.querySelector(`#${editor_name}`).innerHTML);
    }

    for (let input_id in poor_field_map) {
        let input_field = document.querySelector(`#${input_id}`);
        let output_field = document.querySelector(`#${poor_field_map[input_id]}`);
        input_field.setAttribute('contenteditable', true);
        input_field.addEventListener('input', () => {
            output_field.value = input_field.innerText;
        })
    }

    document.querySelector('#create-day').removeAttribute('hidden');
    document.querySelector('#delete-day').removeAttribute('hidden');

    start_picker = new Litepicker({
        element: document.getElementById('start-date'),
        startDate: Date.parse(document.querySelector('#id_start_date').value),
        scrollToDate: true
    });
    start_picker.on('selected', (date) => {
        console.log(date);
        document.querySelector('#start-date').innerHTML = DateTime.fromJSDate(date.dateInstance).toLocaleString(DateTime.DATE_MED);
        document.querySelector('#id_start_date').value = DateTime.fromJSDate(date.dateInstance).toISODate();
        let end_date = DateTime.fromJSDate(end_picker.getDate().dateInstance);
        document.querySelector('#duration').innerHTML = end_date.diff(DateTime.fromJSDate(date.dateInstance), 'days').toObject()['days'] + 1;
    })
    end_picker = new Litepicker({
        element: document.getElementById('end-date'),
        startDate: Date.parse(document.querySelector('#id_end_date').value),
        scrollToDate: true
    });
    end_picker.on('selected', (date) => {
        console.log(date);
        document.querySelector('#end-date').innerHTML = DateTime.fromJSDate(date.dateInstance).toLocaleString(DateTime.DATE_MED);
        document.querySelector('#id_end_date').value = DateTime.fromJSDate(date.dateInstance).toISODate();
        let start_date = DateTime.fromJSDate(start_picker.getDate().dateInstance);
        document.querySelector('#duration').innerHTML = DateTime.fromJSDate(date.dateInstance).diff(start_date, 'days').toObject()['days'] + 1;
    })
}

// Set editing iff editing checkbox checked
let editing = document.querySelector('#editing');
if (!editing.checked) {
    deactivateEditor();
    document.querySelector(':root').style.setProperty('--slider-button-width', '50%');
} else {
    activateEditor();
    document.querySelector(':root').style.setProperty('--slider-button-width', '10%');
}

editing.addEventListener('change', () => {
    if (editing.checked) {
        activateEditor();
        document.querySelector(':root').style.setProperty('--slider-button-width', '10%');
    } else {
        deactivateEditor();
        document.querySelector(':root').style.setProperty('--slider-button-width', '50%');
    }
})


desc.addEventListener('input', editorChange);

function editorChange() {
    document.querySelector('textarea[name="description"]').value = desc.innerHTML;
}

document.querySelector('#create-day').addEventListener('click', () => {
    console.log('creating day');
})

document.querySelector('#delete-day').addEventListener('click', () => {
    console.log('deleting day');
})
