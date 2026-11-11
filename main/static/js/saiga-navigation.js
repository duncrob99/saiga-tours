/* Progressive navigation: links remain normal links if HTMX is unavailable. */
(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let mapNavigation = false;
    document.querySelectorAll('form').forEach(form => form.setAttribute('hx-boost','false'));
    document.addEventListener('htmx:beforeProcessNode', e => {
        if (e.target.tagName === 'FORM') e.target.setAttribute('hx-boost','false');
    });
    document.addEventListener('click', e => {
        if (e.button || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
        const a = e.target.closest('a[href]');
        if (!a) return;
        const url = new URL(a.href, location.href);
        if (url.origin !== location.origin || !/^\/(?:replica\/)?(?:tour|article|destination|details)\//.test(url.pathname)) return;
        const card = a.closest('.img-card, .card');
        if (card && !reduced.matches) {
            card.classList.add('saiga-card-opening');
        }
    }, true);
    document.addEventListener('htmx:validateUrl', e => {
        if (e.detail.url.origin !== location.origin || !e.detail.url.pathname.startsWith(location.pathname.startsWith('/replica/') ? '/replica/' : '/')) e.preventDefault();
    });
    document.addEventListener('htmx:afterSwap', e => {
        if (e.detail.target.id !== 'site-page') return;
        mapNavigation = false;
        if (typeof minimise_images === 'function') minimise_images();
        window.scrollTo(0, 0);
        const page = document.getElementById('site-page');
        if (page && !reduced.matches) {
            page.classList.remove('saiga-page-enter');
            void page.offsetWidth;
            page.classList.add('saiga-page-enter');
        }
    });
    // Capturing the whole detailed SVG in a view transition can stall a browser.
    document.addEventListener('htmx:beforeTransition', e => {
        if (mapNavigation) e.preventDefault();
    });
    document.addEventListener('htmx:responseError', e => {
        if (e.detail.requestConfig?.boosted && e.detail.requestConfig.path) location.href = e.detail.requestConfig.path;
    });
    window.saigaNavigate = (url, map) => {
        if (!window.htmx) { location.href = url; return; }
        if (location.pathname.startsWith('/replica/') && url.startsWith('/') && !url.startsWith('/replica/')) url='/replica'+url;
        mapNavigation = !!map;
        if (map && !reduced.matches) {
            const svg=map.closest('svg');
            if (svg) {
                const bounds=svg.getBoundingClientRect(), country=map.getBoundingClientRect();
                const x=country.left + country.width/2 - bounds.left;
                const y=country.top + country.height/2 - bounds.top;
                svg.animate([{transform:'scale(1)',transformOrigin:`${x}px ${y}px`},{transform:'scale(1.35)',transformOrigin:`${x}px ${y}px`}],{duration:300,easing:'ease-out',fill:'forwards'});
            }
        }
        // The legacy map scripts keep global SVG state; a fresh document avoids
        // retaining that state after the map leaves the page.
        if (map) {
            setTimeout(() => { location.href = url; }, reduced.matches ? 0 : 300);
            return;
        }
        const a=document.createElement('a');
        a.href=url; a.hidden=true; document.body.appendChild(a);
        htmx.process(a); a.click(); setTimeout(() => a.remove(),1000);
    };
})();
