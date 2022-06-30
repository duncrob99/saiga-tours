function minimise_images() {
    document.querySelectorAll(`img`).forEach(img => {
        let img_src;
        if (img.hasAttribute('src')) {
            img_src = img.getAttribute('src');
        } else if (img.hasAttribute('full-size-src')) {
            img_src = img.getAttribute('full-size-src');
        } else return;
        if (img_src.startsWith('/static') || img_src.includes('data:image/') || img_src.includes('http')) return;
        let width = Math.ceil(parseInt(getComputedStyle(img).width) * window.devicePixelRatio);
        let height = img.id === 'header-banner' ? '0' : Math.ceil(parseInt(getComputedStyle(img).height) * window.devicePixelRatio);
        let img_size = `${width}x${height}`;
        img_src = img_src.replace(/^\/media\//, '').replaceAll(/\/resized-image\//g, '').replaceAll(/\/[0-9]+x[0-9]+\//g, '');
        if (img_src && img_size) {
            img.setAttribute('src', `/resized-image/${img_src}/${img_size}/`);
        }
    })
}

minimise_images();

function storageAvailable(type) {
    let storage;
    try {
        storage = window[type];
        let x = '__storage_test__';
        storage.setItem(x, x);
        storage.removeItem(x);
        return true;
    }
    catch(e) {
        return e instanceof DOMException && (
            // everything except Firefox
            e.code === 22 ||
            // Firefox
            e.code === 1014 ||
            // test name field too, because code might not be present
            // everything except Firefox
            e.name === 'QuotaExceededError' ||
            // Firefox
            e.name === 'NS_ERROR_DOM_QUOTA_REACHED') &&
            // acknowledge QuotaExceededError only if there's something already stored
            (storage && storage.length !== 0);
    }
}

if (storageAvailable('sessionStorage')) {
    let left_name = `scroll-left-${window.location.pathname}`;
    let top_name = `scroll-top-${window.location.pathname}`;
    function storeScroll() {
        sessionStorage.setItem(top_name, document.body.scrollTop.toString());
        sessionStorage.setItem(left_name, document.body.scrollLeft.toString());
    }

    document.body.addEventListener('scroll', storeScroll);
    window.addEventListener('resize', storeScroll);


    let nav_type = performance.getEntriesByType('navigation')[0].type;
    if (sessionStorage.getItem(left_name) && sessionStorage.getItem(top_name) && ['reload', 'back_forward'].includes(nav_type)) {
        document.body.scrollTo({
            left: parseFloat(sessionStorage.getItem(left_name)),
            top: parseFloat(sessionStorage.getItem(top_name)),
            behavior: "smooth"
        });
    } else {
        storeScroll();
    }
}
