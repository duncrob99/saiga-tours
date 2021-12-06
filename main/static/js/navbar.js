function hideOffscreen() {
    let dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(el => {
        let caret = el.parentElement.querySelector('.bi')
        if (caret !== null) {
            if (el.getBoundingClientRect().right > document.body.getBoundingClientRect().right || el.children.length === 0) {
                el.style.visibility = 'hidden';
                caret.style.visibility = 'hidden';
            } else {
                el.style.visibility = 'visible';
                caret.style.visibility = 'visible';
            }
        }
    })
}

function resizeText() {
    let navbar = document.querySelector('.navbar');
    let menus = document.querySelector('#navbarNav > .navbar-nav');
    let contact_button = document.querySelector('#separate-contact');
    navbar.style.fontSize = '';
    while (menus.getBoundingClientRect().right > contact_button.getBoundingClientRect().left) {
        navbar.style.fontSize = parseFloat(window.getComputedStyle(navbar, null).getPropertyValue('font-size')) - 0.1 + 'px';
    }
}

hideOffscreen();
window.addEventListener('resize', hideOffscreen);

resizeText();
window.addEventListener('resize', resizeText);
