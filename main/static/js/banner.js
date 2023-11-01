(function () {
    let current_idx = 0;
    let banner_width = 10;
    let banner_height = 10;
    let banner_timeout = null;
    let latest_progression = null;
    let click_throttle = banner_transition_time * 1000;
    let latest_direction = null;
    console.log('banner_transition_time', banner_transition_time);

    function resize() {
        let navbar_height = document.querySelector('.navbar').getBoundingClientRect().height;
        let aspect_ratio = document.documentElement.clientWidth / (document.documentElement.clientHeight - navbar_height);
        let bottom_margin = 50;

        banner_width = Math.max(Math.round(document.documentElement.clientWidth * window.devicePixelRatio), banner_width);
        banner_height = Math.max(Math.round(document.documentElement.clientHeight - navbar_height - bottom_margin * window.devicePixelRatio), banner_height);

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
        })
        document.querySelector('.banner-img:last-child').classList.add('hide');

        document.querySelectorAll('.banner-img').forEach(el => {
            el.addEventListener('transitionstart', () => {
                el.classList.add('transitioning');
            });
            el.addEventListener('transitionend', () => {
                el.classList.remove('transitioning');
            });
        });

        document.querySelector('.banner').addEventListener('click', (ev) => {
            let transitioning = document.querySelectorAll('.banner-img.transitioning').length > 0;

            let direction;
            if (ev.clientX < document.documentElement.clientWidth / 3) {
                direction = 1;
            } else if (ev.clientX > document.documentElement.clientWidth * 2 / 3) {
                direction = -1;
            }

            if (transitioning && direction === latest_direction) {
                return;
            }

            progress(direction);
        });

    });
    window.addEventListener('resize', resize);

    function shortestModDistance(origin, target, mod) {
        let raw_diff = Math.abs(target - origin);
        let mod_diff = raw_diff % mod;

        if (mod_diff > mod / 2) {
            return target > origin ? (mod_diff - mod) : (mod - mod_diff);
        } else {
            return origin > target ? (-1 * mod_diff) : mod_diff;
        }
    }

    function progress(step, delay) {
        step = step ?? 1;
        delay = delay ?? banner_delay * 1000;
        clearTimeout(banner_timeout);
        current_idx = (current_idx + step + document.querySelectorAll('.banner-img').length) % document.querySelectorAll('.banner-img').length;
        latest_direction = Math.sign(step);
        if (!Visibility.hidden()) {
            let all_els = Array.from(document.querySelectorAll('.banner-img'));
            let allowed_els = Array.from(document.querySelectorAll('.banner-img.well-sized'));

            if (!allowed_els.includes(all_els[current_idx])) {
                if (step < 0) {
                    all_els.reverse();
                    let next_allowed = all_els.slice(all_els.length - current_idx - 1).findIndex((el) => el.classList.contains('well-sized'));
                    if (next_allowed === -1) {
                        current_idx = all_els.length - all_els.findIndex((el) => el.classList.contains('well-sized'));
                    } else {
                        current_idx = current_idx - next_allowed;
                    }
                    all_els.reverse();
                } else {
                    let next_allowed = all_els.slice(current_idx).findIndex((el) => el.classList.contains('well-sized'));
                    if (next_allowed === -1) {
                        current_idx = all_els.findIndex((el) => el.classList.contains('well-sized'));
                    } else {
                        current_idx = current_idx + next_allowed;
                    }
                }
            }

            console.log('new current_idx', current_idx);

            let allowed_index = allowed_els.findIndex((el) => el === all_els[current_idx]);
            all_els.forEach((el, ix) => {
                let dist;
                if (allowed_els.includes(el)) {
                    let idx = allowed_els.findIndex((element) => element === el);
                    dist = shortestModDistance(allowed_index, idx, allowed_els.length);
                } else {
                    dist = shortestModDistance(current_idx, ix, all_els.length);
                }
                el.setAttribute('dist', dist);

                if (dist > 1) {
                    el.classList.add('left');
                    el.classList.remove('right');
                    el.classList.add('below');
                    el.classList.add('hide');
                } else if (dist === 1) {
                    el.classList.add('left');
                    el.classList.remove('below');
                    el.classList.remove('right');
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

            banner_timeout = setTimeout(progress, delay, 1, banner_delay * 1000);
        } else {
            banner_timeout = setTimeout(() => {
                Visibility.onVisible(() => progress(step, delay));
            }, delay);
        }
        latest_progression = new Date().getTime();
    }

})();
