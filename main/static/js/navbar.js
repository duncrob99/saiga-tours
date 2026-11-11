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
    let menu_eg = document.querySelector('.nav-link.main-nav');
    if (!navbar || !menus || !menu_eg) return;
    navbar.style.fontSize = '';
    let shrink = 0;
    while (menus.getBoundingClientRect().right > document.documentElement.getBoundingClientRect().right && shrink++ < 100) {
        navbar.style.fontSize = parseFloat(window.getComputedStyle(navbar, null).getPropertyValue('font-size')) - 0.1 + 'px';
    }

    menus.style.top = '';
    let iter = 0;
    while (navbar.getBoundingClientRect().bottom > menu_eg.getBoundingClientRect().bottom && iter < 100) {
        menus.style.top = parseFloat(window.getComputedStyle(menus, null).getPropertyValue('top')) + 1 + 'px';
        iter++;
    }

    document.querySelector(':root').style.setProperty('--navbar-menu-height', parseFloat(window.getComputedStyle(menu_eg).getPropertyValue('height')) + 1 + 'px');
}

hideOffscreen();
window.addEventListener('resize', hideOffscreen);

window.saigaRefreshNavbar = () => { hideOffscreen(); resizeText(); };
resizeText();
window.addEventListener('resize', resizeText);
