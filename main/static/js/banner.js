/* Banner slideshow: safe on direct loads and HTMX page swaps. */
(() => {
    let cleanup = () => {};
    function init() {
        cleanup();
        const banner = document.querySelector('#site-page .banner');
        if (!banner) { cleanup = () => {}; return; }
        const images = [...banner.querySelectorAll('.banner-img')];
        if (!images.length) return;
        let index = 0, timer, disposed = false;
        const initial = Math.max(0, Number(banner.dataset.bannerInitialDelay || 4) * 1000);
        const interval = Math.max(1500, Number(banner.dataset.bannerDelay || 7) * 1000);
        
        function size() {
            if (disposed || !banner.isConnected) return;
            const ratio = banner.clientWidth / Math.max(1, banner.clientHeight);
            images.forEach(img => {
                const min = Number(img.getAttribute('min_ar'));
                const max = Number(img.getAttribute('max_ar'));
                img.classList.toggle('well-sized', !(Number.isFinite(min) && Number.isFinite(max)) || (min < ratio && ratio < max));
            });
        }
        function display(next) {
            if (disposed || !banner.isConnected) return;
            // Prefer an aspect-matched banner, but never hide every image.
            const eligible = images.filter(img => img.classList.contains('well-sized'));
            const candidates = eligible.length ? eligible : images;
            index = ((next % candidates.length) + candidates.length) % candidates.length;
            const active = candidates[index];
            images.forEach(img => {
                const shown = img === active;
                img.classList.toggle('hide', !shown);
                img.classList.toggle('show', shown);
                img.classList.remove('left', 'right', 'below', 'hide-left', 'hide-right');
            });
        }
        function advance(direction = 1) {
            const eligible = images.filter(img => img.classList.contains('well-sized'));
            const candidates = eligible.length ? eligible : images;
            const current = candidates.findIndex(img => img.classList.contains('show'));
            display((current < 0 ? 0 : current) + direction);
        }
        function schedule(delay) {
            clearTimeout(timer);
            timer = setTimeout(() => {
                if (!document.hidden) advance();
                schedule(interval);
            }, delay);
        }
        const onClick = event => {
            if (event.target.closest('a, button, input, form')) return;
            if (event.clientX < innerWidth / 3) advance(-1);
            else if (event.clientX > innerWidth * 2 / 3) advance(1);
            else return;
            schedule(interval);
        };
        const onVisibility = () => { if (!document.hidden) schedule(interval); };
        size();
        display(0);
        schedule(initial || interval);
        banner.addEventListener('click', onClick);
        window.addEventListener('resize', size);
        document.addEventListener('visibilitychange', onVisibility);
        cleanup = () => {
            disposed = true;
            clearTimeout(timer);
            banner.removeEventListener('click', onClick);
            window.removeEventListener('resize', size);
            document.removeEventListener('visibilitychange', onVisibility);
        };
    }
    document.addEventListener('htmx:afterSwap', event => {
        if (event.detail.target?.id === 'site-page') init();
    });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once: true});
    else init();
})();
