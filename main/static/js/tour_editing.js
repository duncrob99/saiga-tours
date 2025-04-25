const DateTime = luxon.DateTime;

let start_picker, end_picker, start_date, end_date;
if (dated) {
    start_date = Date.parse(document.querySelector('#iso-start').innerText.trim());
    end_date = Date.parse(document.querySelector('#iso-end').innerText.trim());
}

let initial_slider_button_width = document.querySelector(':root').style.getPropertyValue('--slider-button-width');

let desc = document.querySelector('#tour-desc');
desc.setAttribute('contenteditable', true);

document.querySelector('textarea[name="description"]').parentElement.parentElement.style.display = 'none';
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

    minimise_images();
}

function activateEditor() {
    make_images_fullsize();

    rich_fields: for (let editor_name in rich_field_map) {
        document.querySelector(`#${editor_name}`).setAttribute('contenteditable', true);
        for (let instance in CKEDITOR.instances) {
            if (instance === editor_name) {
                continue rich_fields;
            }
        }
        let editor = createEditor(editor_name);
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

function make_images_fullsize() {
    for (let editor_name in rich_field_map) {
        document.querySelectorAll(`#${editor_name} img`).forEach(img => {
            if (img.hasAttribute('full-size-src')) {
                img.setAttribute('src', img.getAttribute('full-size-src'));
            }
        });
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

window.addEventListener('load', () => {
    document.getElementById('editor-form').addEventListener('submit', (ev) => {
        deactivateEditor();
        for (let editor_name in rich_field_map) {
            rich_field_map[editor_name].value = document.querySelector(`#${editor_name}`).innerHTML;
        }
    })
})

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

// Initialise buttons to bind itinerary day templates
let select = document.querySelector('#select-itinerary-template');
let input = document.querySelector('#new-itinerary-template-input');
let choices, select_container;

// Wait for choices to load
function setChoices() {
    if (typeof Choices === 'undefined') {
        setTimeout(setChoices, 100);
        console.log('Waiting for choices');
        return;
    }

    console.log('Choices loaded');

    choices = new Choices(select, {
        allowHTML: false,
        removeItemButton: true,
        duplicateItemsAllowed: false,
        // searchResultLimit: 10,
        resetScrollPosition: false
    });

    select = document.querySelector('#select-itinerary-template');
    select_container = document.querySelector('#select-container');
}

setChoices();

document.querySelectorAll('.bind-itinerary-template-button').forEach(btn => {

    btn.addEventListener('click', () => {
        let day = days[parseInt(btn.getAttribute('data-model-pk'))];
        if (day.template) {
            day.template = undefined;
            document.querySelector(`#id_itinerary-${day.position}-template`).value = '';
            console.log('Removed bind');
            btn.innerText = 'Bind Template';
            btn.removeAttribute('data-template-name');
            btn.classList.remove('hover-template-name');
        } else {
            let modal = new bootstrap.Modal(document.querySelector('#bind-itinerary-template-modal'));
            let submitButton = document.querySelector('#save-itinerary-template-selection');
            let creating_new = false;

            let newButton = document.querySelector('#new-itinerary-template-button');
            let existingButton = document.querySelector('#use-existing-itinerary-template-button');

            // select.querySelectorAll('option').forEach(opt => opt.remove());
            // let opt = document.createElement('option');
            // opt.value = '';
            // opt.innerHTML = '-----';
            // select.appendChild(opt);
            // for (let [templateId, templateData] of Object.entries(itinerary_templates)) {
            //     let opt = document.createElement('option');
            //     opt.value = templateId;
            //     opt.innerHTML = templateData.title;
            //     if (templateId === day.template) {
            //         opt.selected = true;
            //     }
            //     select.appendChild(opt);
            // }
            // select.value = day.template;

            let template_choices = [];
            for (let [templateId, templateData] of Object.entries(itinerary_templates)) {
                template_choices.push({
                    value: templateId,
                    label: templateData.title,
                });
            }
            console.log(template_choices);

            choices.setChoices(template_choices, 'value', 'label', true);

            submitButton.onclick = function () {
                if (creating_new) {
                    if (!Object.values(itinerary_templates).map(temp => temp.title).includes(input.value)) {
                        show_spinner();
                        create_itinerary_template({
                            data: {
                                title: input.value,
                                body: document.querySelector(`#day-${day.position + 1}-body`).innerHTML
                            },
                            success: (data) => {
                                day.template = parseInt(data.pk);
                                itinerary_templates[parseInt(data.pk)] = {
                                    title: data.title,
                                    body: data.body
                                };

                                let opt = document.createElement('option');
                                opt.value = parseInt(data.pk);
                                opt.text = input.value;
                                document.querySelector(`#id_itinerary-${day.position}-template`).appendChild(opt);

                                document.querySelector(`#id_itinerary-${day.position}-template`).value = parseInt(data.pk);
                                modal.hide();
                                btn.textContent = 'Unbind Template';
                                btn.setAttribute('data-template-name', input.value);
                                btn.classList.add('hover-template-name');
                                hide_spinner();
                            },
                            error: (data) => {
                                console.warn(`Error adding itinerary template, data: ${data}`);
                                modal.hide();
                                hide_spinner();
                            }
                        });
                    } else {
                        console.log('Duplicate template name');
                        input.classList.add('is-invalid');
                    }
                } else {
                    day.template = parseInt(select.value);
                    day.body = itinerary_templates[day.template].body;
                    if (!day.title) {
                        day.title = itinerary_templates[day.template].title;
                    }
                    document.querySelector(`#id_itinerary-${day.position}-template`).value = day.template;
                    document.querySelector(`#id_itinerary-${day.position}-body`).value = day.body;
                    document.querySelector(`#id_itinerary-${day.position}-title`).value = day.title;
                    document.querySelector(`#day-${day.position + 1}-body`).innerHTML = day.body;
                    document.querySelector(`#day-${day.position + 1}-title`).innerHTML = day.title;
                    modal.hide();
                    btn.textContent = 'Unbind Template';
                    btn.setAttribute('data-template-name', itinerary_templates[day.template].title);
                    btn.classList.add('hover-template-name');
                }
            }

            newButton.onclick = function () {
                select_container.setAttribute('hidden', true);
                input.parentElement.removeAttribute('hidden');
                newButton.setAttribute('hidden', true);
                existingButton.removeAttribute('hidden');
                creating_new = true;
            }

            existingButton.onclick = function () {
                input.parentElement.setAttribute('hidden', true);
                select_container.removeAttribute('hidden');
                existingButton.setAttribute('hidden', true);
                newButton.removeAttribute('hidden');
                creating_new = false;
            }

            modal.show();
            document.querySelector('#bind-itinerary-template-modal').addEventListener('shown.bs.modal', () => select.focus());
        }
        // point_el.setAttributeNS(null, 'style', `fill: ${stop.template && editable ? 'blue' : 'red'};`);
    })
})

function create_itinerary_template(input) {
    let csrfToken = document.cookie.substring(document.cookie.indexOf('csrftoken=') + 'csrftoken='.length).split(';')[0];
    $.ajax({
        type: "POST",
        url: `/create/itinerary_template/`,
        data: input.data,
        success: input.success,
        error: input.error,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
}

const form = document.querySelector("#editor-form");
form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const formData = new FormData(form);
    console.log("Sending form with data: ", formData);
    show_spinner();

    try {
        const response = await fetch('', {
            method: "POST",
            body: formData,
        });
        console.log("Form submission response: ", response);
        hide_spinner();
        if (response.ok) {
            show_message('Successfully saved, <a href="#" target="_blank" class="nice-link">check it\'s correct by clicking here to reload</a>', "info");
        } else {
            show_message(`Saving error (${response.status}): ${response.statusText}`, "danger");
        }
    } catch (e) {
        console.error(e);
        hide_spinner();
        show_message(`Saving error: ${e}`, "danger");
    }
});
