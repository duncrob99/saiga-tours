const preloadImage = src =>
    new Promise((resolve, reject) => {
        const image = new Image()
        image.onload = resolve
        image.onerror = reject
        image.src = src
    })

let pause_async = async (t) => {
    return new Promise(resolve => {
        setTimeout(resolve, t);
    })
}

async function minimise_image(img, downscale) {
    return new Promise(async (resolve, reject) => {

        let img_src;
        if (img.hasAttribute('full-size-src')) {
            img_src = img.getAttribute('full-size-src');
        } else if (img.hasAttribute('data-filename')) {
            img_src = img.getAttribute('data-filename');
        } else if (img.hasAttribute('src')) {
            img_src = img.getAttribute('src');
        } else return reject('No src attribute found');

        let original_src = img_src;
        if (img_src.startsWith('/static') || img_src.includes('data:image/') || img_src.includes('http')) return reject('Not a local media image');

        if (downscale === undefined) {
            // await minimise_image(img, 50).catch(reason => {
            //     reject(reason);
            // });
            // await pause_async(5000);
            console.log("Finished minimising");
            downscale = 1;
        }

        if (downscale !== 1 && !img.hasAttribute('data-full-size-loaded')) {
            img.classList.add('downscaled');
            console.log('downscaling');
        } else {
            img.setAttribute('data-full-size-loaded', 'true');
            downscale = 1;
        }

        let width = Math.ceil(parseInt(getComputedStyle(img).width) * window.devicePixelRatio / downscale);
        let height = img.id === 'header-banner' ? 0 : Math.ceil(parseInt(getComputedStyle(img).height) * window.devicePixelRatio / downscale);

        if (isNaN(width) || isNaN(height)) {
            console.warn("Image width or height is NaN, not minimising");
            console.log(parseInt(getComputedStyle(img).width), parseInt(getComputedStyle(img).height), window.devicePixelRatio, downscale);
            return reject('Image has no width or height');
        }

        let {orig_width, orig_height} = {orig_width: width, orig_height: height};
        // Only increase the size of the image
        if (img.hasAttribute('loaded-width') && !isNaN(parseInt(img.getAttribute('loaded-width')))) {
            width = Math.max(width, parseInt(img.getAttribute('loaded-width')));
        }
        if (img.hasAttribute('loaded-height') && !isNaN(parseInt(img.getAttribute('loaded-height')))) {
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
            img.onload = () => {
                if (img.hasAttribute('data-full-size-loaded')) {
                    img.classList.remove('downscaled');
                }
                resolve(img);
            }
            img.onerror = reject;
            img.setAttribute('src', `/resized-image/${img_src}/${img_size}/`);
        }
    });
}

function minimise_images() {
    let images = document.querySelectorAll('img');
    let general_observer = new IntersectionObserver(async entries => {
        for (const entry of entries) {
            if (entry.intersectionRatio > 0) {
                general_observer.unobserve(entry.target);
                // entry.target.setAttribute('observing-intersection', 'false');
                await minimise_image(entry.target).catch(reason => {
                    console.warn("Failed to minimise image: ", entry.target, reason);
                });
            }
        }
    }, {threshold: [0], rootMargin: '20%', root: document.body});
    let blurred_observer = new IntersectionObserver(async entries => {
        for (const entry of entries) {
            if (entry.intersectionRatio > 0) {
                blurred_observer.unobserve(entry.target);
                await minimise_image(entry.target, 50).catch(reason => {
                    console.warn("Failed to blur image: ", entry.target, reason);
                });
                general_observer.observe(entry.target);
            }
        }
    }, {threshold: [0], rootMargin: '200%', root: document.body});
    let banner_observer = new IntersectionObserver(async entries => {
        for (const entry of entries) {
            if (entry.intersectionRatio > 0) {
                banner_observer.unobserve(entry.target);
                entry.target.setAttribute('observing-intersection', 'false');
                await minimise_image(entry.target);
            }
        }
    }, {threshold: [0], rootMargin: '20%', root: document.body});
    images.forEach(img => {
        if (img.hasAttribute('data-no-minimise')) return;
        if (img.hasAttribute('data-lazy-load') && img.getAttribute('data-lazy-load') === 'false') {
            minimise_image(img).then();
            return;
        }
        if (img.classList.contains('banner-img')) {
            banner_observer.observe(img);
        } else {
            // blurred_observer.observe(img);
            general_observer.observe(img);
        }
        img.setAttribute('observing-intersection', 'true');
    });

    let resize_observer = new ResizeObserver(entries => {
        entries.forEach(async entry => {
            if (entry.target.hasAttribute('observing-intersection') && entry.target.getAttribute('observing-intersection') === 'false') {
                if (entry.target.classList.contains('banner-img')) {
                    banner_observer.observe(entry.target);
                } else {
                    // blurred_observer.observe(entry.target);
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
    } catch (e) {
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

function css_browser_selector(u) {
    let ua = u.toLowerCase(), is = function (t) {
            return ua.indexOf(t) > -1
        }, g = 'gecko', w = 'webkit', s = 'safari', o = 'opera', m = 'mobile', h = document.documentElement,
        b = [(!(/opera|webtv/i.test(ua)) && /msie\s(\d)/.test(ua)) ? ('ie ie' + RegExp.$1) : is('firefox/2') ? g + ' ff2' : is('firefox/3.5') ? g + ' ff3 ff3_5' : is('firefox/3.6') ? g + ' ff3 ff3_6' : is('firefox/3') ? g + ' ff3' : is('gecko/') ? g : is('opera') ? o + (/version\/(\d+)/.test(ua) ? ' ' + o + RegExp.$1 : (/opera(\s|\/)(\d+)/.test(ua) ? ' ' + o + RegExp.$2 : '')) : is('konqueror') ? 'konqueror' : is('blackberry') ? m + ' blackberry' : is('android') ? m + ' android' : is('chrome') ? w + ' chrome' : is('iron') ? w + ' iron' : is('applewebkit/') ? w + ' ' + s + (/version\/(\d+)/.test(ua) ? ' ' + s + RegExp.$1 : '') : is('mozilla/') ? g : '', is('j2me') ? m + ' j2me' : is('iphone') ? m + ' iphone' : is('ipod') ? m + ' ipod' : is('ipad') ? m + ' ipad' : is('mac') ? 'mac' : is('darwin') ? 'mac' : is('webtv') ? 'webtv' : is('win') ? 'win' + (is('windows nt 6.0') ? ' vista' : '') : is('freebsd') ? 'freebsd' : (is('x11') || is('linux')) ? 'linux' : '', 'js'];
    let c = b.join(' ');
    h.className += ' ' + c;
    return c;
};
css_browser_selector(navigator.userAgent);

if (storageAvailable('sessionStorage')) {
    var left_name = `scroll-left-${window.location.pathname}`;
    var top_name = `scroll-top-${window.location.pathname}`;

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

(function () {
    let message_container = document.getElementById('messages-container');
    const alert = (message, type) => {
        const wrapper = document.createElement('div')
        wrapper.innerHTML = [
            `<div class="alert alert-${type.toLowerCase()} alert-dismissible" role="alert">`,
            `   <div>${message}</div>`,
            '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
            '</div>'
        ].join('')

        message_container.append(wrapper)
    }


    // Fetch messages from the server
    fetch('/messages/').then(response => response.json()).then(data => {
        console.log("Data: ", data);
        let messages = data.messages;
        let message_html = '';
        if (messages.length > 0) {
            messages.forEach(message => {
                alert(message.message, message.level);
            });
        }
    });
})();