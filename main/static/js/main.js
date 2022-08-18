function minimise_image(img) {
    let img_src;
    if (img.hasAttribute('src')) {
        img_src = img.getAttribute('src');
    } else if (img.hasAttribute('full-size-src')) {
        img_src = img.getAttribute('full-size-src');
    } else if (img.hasAttribute('data-filename')) {
        img_src = img.getAttribute('data-filename');
    } else return;
    let original_src = img_src;
    if (img_src.startsWith('/static') || img_src.includes('data:image/') || img_src.includes('http')) return;
    let width = Math.ceil(parseInt(getComputedStyle(img).width) * window.devicePixelRatio);
    let height = img.id === 'header-banner' ? '0' : Math.ceil(parseInt(getComputedStyle(img).height) * window.devicePixelRatio);

    // Only increase the size of the image
    if (img.hasAttribute('loaded-width')) {
        width = Math.max(width, parseInt(img.getAttribute('loaded-width')));
    }
    if (img.hasAttribute('loaded-height')) {
        height = Math.max(height, parseInt(img.getAttribute('loaded-height')));
    }
    img.setAttribute('loaded-width', width);
    img.setAttribute('loaded-height', height);

    let img_size = `${width}x${height}`;
    img_src = img_src.replace(/^\/media\//, '').replaceAll(/\/?resized-image\//g, '').replaceAll(/\/[0-9]+x[0-9]+\//g, '');

    // Remove trailing slash if it exists
    if (img_src.endsWith('/')) {
        img_src = img_src.substring(0, img_src.length - 1);
    }

    // Check if img src still has resized-image in it
    if (img_src.includes('resized-image')) {
        console.warn("Image still has resized-image in it: ", img, img_src, original_src);
    }
    if (img_src && img_size) {
        img.setAttribute('src', `/resized-image/${img_src}/${img_size}/`);
    }
}

function minimise_images() {
    let images = document.querySelectorAll('img');
    let general_observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.intersectionRatio > 0) {
                minimise_image(entry.target);
                general_observer.unobserve(entry.target);
                entry.target.setAttribute('observing-intersection', 'false');
            }
        });
    }, { threshold: [0], rootMargin: '200%', root: document.body });
    let banner_observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.intersectionRatio > 0) {
                minimise_image(entry.target);
                banner_observer.unobserve(entry.target);
                entry.target.setAttribute('observing-intersection', 'false');
            }
        });
    }, { threshold: [0], rootMargin: '20%', root: document.body });
    images.forEach(img => {
        if (img.hasAttribute('data-no-minimise')) return;
        if (img.classList.contains('banner-img')) {
            banner_observer.observe(img);
        } else {
            general_observer.observe(img);
        }
        img.setAttribute('observing-intersection', 'true');
    });

    let resize_observer = new ResizeObserver(entries => {
        entries.forEach(entry => {
            if (entry.target.hasAttribute('observing-intersection') && entry.target.getAttribute('observing-intersection') === 'false') {
                if (entry.target.classList.contains('banner-img')) {
                    banner_observer.observe(entry.target);
                } else {
                    general_observer.observe(entry.target);
                }
                entry.target.setAttribute('observing-intersection', 'true');
            }
        });
    });
    images.forEach(img => {
        if (img.hasAttribute('data-no-minimise')) return;
        resize_observer.observe(img);
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
