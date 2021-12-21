let current_idx = 0;

function resize() {
    let navbar_height = document.querySelector('.navbar').getBoundingClientRect().height;
    let aspect_ratio = document.documentElement.clientWidth / (document.documentElement.clientHeight - navbar_height);
    let bottom_margin = 50;

    let banner_imgs = document.querySelectorAll('#banner-slideshow img');

    banner_imgs.forEach(el => {
        el.style.top = navbar_height + "px";
        el.style.height = document.documentElement.clientHeight - navbar_height - bottom_margin + 'px';
        let min_ar = parseFloat(el.getAttribute('min_ar'));
        let max_ar = parseFloat(el.getAttribute('max_ar'));
        if (min_ar < aspect_ratio && aspect_ratio < max_ar) {
            el.classList.add('well-sized');
            el.classList.remove('badly-sized');
        } else {
            el.classList.remove('well-sized');
            el.classList.add('badly-sized');
        }
    });

    document.querySelector('.banner').style.top = navbar_height + "px";
    document.querySelector('.banner').style.height = document.documentElement.clientHeight - navbar_height - bottom_margin + "px";
}

function setVisible() {
    let current_el = document.querySelectorAll('.banner-img.show');
    if (current_el.length === 0) {
        current_el = document.querySelectorAll('.banner-img')[0]
        show(current_el);
    } else if (current_el.length === 1) {
        current_el = current_el[0];
    } else {
        current_el.forEach((el) => {
            if (el !== current_el[0]) {
                hide(el);
            }
        })
        current_el = current_el[0];
    }
    let banner_imgs = document.querySelectorAll('.banner-img');

    let allowed_imgs = [];
    banner_imgs.forEach((el) => {
        if (el.classList.contains('well-sized') && el !== current_el) {
            allowed_imgs.push(el);
        }
    })

    if (allowed_imgs.length === 0) {
        return
    }
    let rand_index = Math.floor(Math.random() * allowed_imgs.length);

    show(allowed_imgs[rand_index]);
    hide(current_el);
}

function scheduleBannerChange(last_updated) {
    if (new Date().getTime() - last_updated >= banner_delay * 900) {
        setVisible()
        last_updated = new Date().getTime();
    }
    setTimeout(scheduleBannerChange, banner_delay * 1000 - (new Date().getTime() - last_updated), last_updated)
}

function hide(banner_el) {
    if (banner_el !== undefined) {
        setTimeout(() => {
            banner_el.classList.add('hide-right');
            banner_el.addEventListener('transitionend', () => {
                banner_el.classList.add('hide');
                banner_el.classList.remove('show');
                banner_el.classList.add('hide-left');
                banner_el.classList.remove('hide-right');
            }, {
                capture: false,
                once: true,
                passive: false
            })
        }, 1);
    }
}

function show(el) {
    el.classList.remove('hide');
    el.classList.add('show');
    setTimeout(() => {
        el.classList.remove('hide-left');
        el.classList.remove('hide-right');
    }, 0)
}

window.addEventListener('load', () => {
    //scheduleBannerChange(new Date().getTime());
    Visibility.onVisible(() => {
        resize();
        progress(0, banner_init_delay * 1000);
        loadNextImg();
    })
    document.querySelector('.banner-img:last-child').classList.add('hide');
});
window.addEventListener('resize', resize);

function loadImg(img_el) {
    img_el.src = img_el.dataset.src;
    img_el.classList.remove('to-load')
}

function loadNextImg() {
    let all_imgs = document.querySelectorAll('.banner-img');
    let to_load = Array.from(document.querySelectorAll('.banner-img.to-load'));
    if (to_load.length === 0) {
        return
    }

    let allowed_to_load = Array.from(document.querySelectorAll('.banner-img.to-load.well-sized'));
    let current = all_imgs[current_idx];
    let next_to_load;
    if (current.classList.contains('to-load')) {
        next_to_load = current;
    } else if (allowed_to_load.length > 0) {
        next_to_load = allowed_to_load.find(el => parseInt(el.getAttribute('idx')) > current_idx);
    } else {
        next_to_load = to_load.find(el => parseInt(el.getAttribute('idx')) > current_idx);
    }
    next_to_load.addEventListener('load', loadNextImg);
    loadImg(next_to_load);
}

function shortestModDistance(origin, target, mod) {
    let raw_diff = Math.abs(target - origin);
    let mod_diff = raw_diff % mod;

    if (mod_diff > mod / 2) {
        return target > origin ? (mod_diff - mod) : (mod - mod_diff);
    } else {
        return origin > target ? (-1 * mod_diff) : mod_diff;
    }
}

function progress(index, delay) {
    current_idx = index;
    if (!Visibility.hidden()) {
        let all_els = Array.from(document.querySelectorAll('.banner-img'));
        let allowed_els = Array.from(document.querySelectorAll('.banner-img.well-sized'));

        if (!allowed_els.includes(all_els[index])) {
            let next_allowed = all_els.slice(index).findIndex((el) => el.classList.contains('well-sized'));
            if (next_allowed === -1 || all_els.slice(index).length === 0) {
                index = all_els.findIndex((el) => el.classList.contains('well-sized'));
            } else {
                index += next_allowed;
            }
        }

        let allowed_index = allowed_els.findIndex((el) => el === all_els[index]);
        all_els.forEach((el, ix) => {
            let dist;
            if (allowed_els.includes(el)) {
                let idx = allowed_els.findIndex((element) => element === el);
                dist = shortestModDistance(allowed_index, idx, allowed_els.length);
            } else {
                dist = shortestModDistance(index, ix, all_els.length);
            }
            el.setAttribute('dist', dist);

            if (dist > 1) {
                el.classList.add('left');
                el.classList.remove('right');
                el.classList.add('hide');
            } else if (dist === 1) {
                el.classList.add('left');
                el.classList.remove('right');
                el.classList.add('below');
                el.classList.remove('hide');
            } else if (dist === 0) {
                el.classList.remove('left');
                el.classList.remove('right');
                el.classList.remove('below');
                el.classList.remove('hide');
            } else if (dist === -1) {
                el.classList.add('right');
                el.classList.remove('left');
                el.classList.remove('below');
                el.classList.remove('hide');
            } else {
                el.classList.add('right');
                el.classList.remove('left');
                el.classList.add('below');
                el.classList.add('hide');
            }
        })

        setTimeout(progress, delay, index + 1, banner_delay * 1000);
    } else {
        setTimeout(() => {
            Visibility.onVisible(() => progress(index, delay));
        }, delay);
    }
}
