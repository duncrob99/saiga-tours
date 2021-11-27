function hideOffscreen() {
    let dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(el => {
        let caret = el.parentElement.querySelector('.bi')
        if (caret !== null) {
            if (el.getBoundingClientRect().right > document.body.getBoundingClientRect().right) {
                el.style.visibility = 'hidden';
                caret.style.visibility = 'hidden';
            } else {
                el.style.visibility = 'visible';
                caret.style.visibility = 'visible';
            }
        }
    })
}

function resizeMobileDropdown() {
    let items = document.querySelectorAll('.navbar-nav > .nav-item');
    let bottom = 0;
    items.forEach(el => {
        bottom = Math.max(bottom, el.getBoundingClientRect().bottom);
    })
    document.querySelector('#navbarNav').style.setProperty('--navbar-height', `calc(${bottom}px - 10vh)`);
}

document.querySelector('.navbar-toggler').addEventListener('click', resizeMobileDropdown);

hideOffscreen();
window.addEventListener('resize', hideOffscreen);