function startEditing() {
    setCountryNames(destinations, true);
    map_settings.editable = true;
}

function stopEditing() {
    setCountryNames(destinations, false);
    map_settings.editable = false;
}

let editing = document.querySelector('#editing');

function checkEditing() {
    if (!editing.checked) {
        stopEditing();
    } else {
        startEditing();
    }
}

editing.addEventListener('change', checkEditing);
window.addEventListener('resize', checkEditing);
checkEditing();
