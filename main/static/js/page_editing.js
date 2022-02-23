CKEDITOR.disableAutoInline = true;

document.querySelector('[name="content"]').parentElement.parentElement.style.display = 'none';
document.querySelector('[name="title"]').parentElement.style.display = 'none';

let csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]');

function updateContentFormField() {
    document.querySelector('[name="content"]').value = document.querySelector('#content').innerHTML;
}

function moveBannerImg(click_ev) {
    let title_rect = document.getElementById('title').getBoundingClientRect();
    if (click_ev.x >= title_rect.left && click_ev.x <= title_rect.right && click_ev.y >= title_rect.top && click_ev.y <= title_rect.bottom) return;

    click_ev.preventDefault();
    let banner = document.getElementById('header-banner');
    let obj_pos = banner.style.objectPosition;
    let init_pos = obj_pos ? {
        left: parseFloat(obj_pos.split(' ')[0]),
        top: parseFloat(obj_pos.split(' ')[1])
    } : {left: 50, top: 50};
    console.log(init_pos);

    // init_pos = {left: parseInt(window.getComputedStyle(banner).left), top: parseInt(window.getComputedStyle(banner).top)};

    function move_callback(move_ev) {
        // banner.style.left = (move_ev.x - click_ev.x) + init_pos.left + 'px';
        // banner.style.top = (move_ev.y - click_ev.y) + init_pos.top + 'px';
        let left = (move_ev.x - click_ev.x) * 0.1 + init_pos.left;
        let top = (move_ev.y - click_ev.y) * -0.1 + init_pos.top;
        banner.style.objectPosition = `${left}% ${top}%`;
        document.querySelector('[name="banner_pos_x"]').value = left;
        document.querySelector('[name="banner_pos_y"]').value = top;
    }

    window.addEventListener('mousemove', move_callback);

    window.addEventListener('mouseup', () => {
        window.removeEventListener('mousemove', move_callback);
    })
}

function activateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', true);

    let editor = createEditor('content');

    editor.on('saveSnapshot', updateContentFormField);
    document.querySelector('#content').addEventListener('input', updateContentFormField);

    let title_input = document.querySelector('#title');
    let title_output = document.querySelector('[name="title"]');
    title_input.setAttribute('contenteditable', true);
    title_input.addEventListener('input', () => {
        title_output.value = title_input.innerText;
    })

    document.getElementById('header-content').addEventListener('mousedown', moveBannerImg);
}

function deactivateEditor() {
    document.querySelector('#content').setAttribute('contenteditable', false);
    if (Object.keys(CKEDITOR.instances).includes('content')) {
        CKEDITOR.instances['content'].destroy();
    }

    document.querySelector('#title').setAttribute('contenteditable', false);
    document.getElementById('header-content').removeEventListener('mousedown', moveBannerImg);
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