const DateTime = luxon.DateTime;

let start_picker, end_picker, start_date, end_date;
if (dated) {
    start_date = Date.parse(document.querySelector('#iso-start').innerText.trim());
    end_date = Date.parse(document.querySelector('#iso-end').innerText.trim());
}

let initial_slider_button_width = document.querySelector(':root').style.getPropertyValue('--slider-button-width');

CKEDITOR.disableAutoInline = true;
let desc = document.querySelector('#tour-desc');
desc.setAttribute('contenteditable', true);

document.querySelector('[name="description"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="name"]').parentElement.style.display = 'none';
document.querySelector('[name="duration"]').parentElement.style.display = 'none';
document.querySelector('[name="price"]').parentElement.style.display = 'none';
if (dated) {
    document.querySelector('[name="start_date"]').parentElement.style.display = 'none';
} else {
    start_picker = new Litepicker({
        element: document.querySelector('[name="start_date"]'),
    });
}

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

function deactivateEditor() {
    for (let editor_name in rich_field_map) {
        document.querySelector(`#${editor_name}`).setAttribute('contenteditable', false);
        if (Object.keys(CKEDITOR.instances).includes(editor_name)) {
            CKEDITOR.instances[editor_name].destroy();
        }
    }

    for (let input_id in poor_field_map) {
        let input_field = document.querySelector(`#${input_id}`);
        input_field.setAttribute('contenteditable', false);
    }

    if (dated) {
        if (start_picker !== undefined) {
            start_picker.destroy();
        }
        if (end_picker !== undefined) {
            end_picker.destroy();
        }
    }

    document.querySelector(':root').style.setProperty('--slider-button-width', initial_slider_button_width);

    if (typeof updateStops === 'function') {
        updateStops(stops, false);
    }
}

function activateEditor() {
    rich_fields: for (let editor_name in rich_field_map) {
        document.querySelector(`#${editor_name}`).setAttribute('contenteditable', true);
        for (let instance in CKEDITOR.instances) {
            if (instance === editor_name) {
                continue rich_fields;
            }
        }
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

    if (dated) {
        start_picker = new Litepicker({
            element: document.getElementById('start-date'),
            startDate: start_date,
            scrollToDate: true
        });
        start_picker.on('selected', (date) => {
            document.querySelector('#start-date').innerHTML = DateTime.fromJSDate(date.dateInstance).toLocaleString(DateTime.DATE_MED);
            let end_date = DateTime.fromJSDate(end_picker.getDate().dateInstance);
            let duration = end_date.diff(DateTime.fromJSDate(date.dateInstance), 'days').toObject()['days'] + 1
            document.querySelector('#duration').innerHTML = duration;
            document.querySelector('#id_duration').value = duration;
            start_date = date;
        })
        end_picker = new Litepicker({
            element: document.getElementById('end-date'),
            startDate: end_date,
            scrollToDate: true
        });
        end_picker.on('selected', (date) => {
            document.querySelector('#end-date').innerHTML = DateTime.fromJSDate(date.dateInstance).toLocaleString(DateTime.DATE_MED);
            let start_date = DateTime.fromJSDate(start_picker.getDate().dateInstance);
            let duration = DateTime.fromJSDate(date.dateInstance).diff(start_date, 'days').toObject()['days'] + 1
            document.querySelector('#duration').innerHTML = duration;
            document.querySelector('#id_duration').value = duration;
            end_date = date;
        })
    }

    document.querySelector(':root').style.setProperty('--slider-button-width', '10%');

    if (typeof updateStops === 'function') {
        updateStops(stops, true);
    }
}

// Set editing iff editing checkbox checked
let editing = document.querySelector('#editing');

function checkEditing() {
    if (!editing.checked) {
        deactivateEditor();
    } else {
        activateEditor();
    }
}

editing.addEventListener('change', checkEditing);
window.addEventListener('resize', checkEditing);
checkEditing();

desc.addEventListener('input', editorChange);

function editorChange() {
    document.querySelector('textarea[name="description"]').value = desc.innerHTML;
}

document.querySelectorAll('textarea').forEach(el => {
    el.style.resize = 'none';
    el.style.height = '1px';
    el.style.height = `${el.scrollHeight + parseInt(getComputedStyle(el).lineHeight) / 2}px`;
    el.addEventListener('input', () => {
        el.style.height = '1px';
        el.style.height = `${el.scrollHeight + parseInt(getComputedStyle(el).lineHeight) / 2}px`;
    })
})