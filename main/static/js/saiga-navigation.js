/* Progressive navigation: links remain normal links if HTMX is unavailable. */
(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let selected;
    document.addEventListener('click', e => {
        if (e.button || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
        const a = e.target.closest('a[href]');
        if (!a) return;
        const url = new URL(a.href, location.href);
        if (url.origin !== location.origin || !/^\/(?:replica\/)?(?:tour|article|destination|details)\//.test(url.pathname)) return;
        const card = a.closest('.img-card, .card');
        if (card && !reduced.matches) {
            document.querySelectorAll('[data-saiga-transition]').forEach(el => { el.style.viewTransitionName = ''; el.removeAttribute('data-saiga-transition'); });
            card.dataset.saigaTransition = 'true';
            card.style.viewTransitionName = 'saiga-card';
        }
    }, true);
    document.addEventListener('htmx:validateUrl', e => {
        if (e.detail.url.origin !== location.origin || !e.detail.url.pathname.startsWith(location.pathname.startsWith('/replica/') ? '/replica/' : '/')) e.preventDefault();
    });
    document.addEventListener('htmx:afterSwap', e => {
        if (e.detail.target.id !== 'site-page') return;
        if (typeof minimise_images === 'function') minimise_images();
        window.scrollTo({top:0, behavior:'instant'});
    });
    document.addEventListener('htmx:responseError', e => {
        if (e.detail.requestConfig?.boosted && e.detail.requestConfig.path) location.href = e.detail.requestConfig.path;
    });
    window.saigaNavigate = (url, map) => {
        if (!window.htmx) { location.href = url; return; }
        if (map && !reduced.matches) {
            map.animate([{transform:'scale(1)'},{transform:'scale(1.12)'}],{duration:260,easing:'ease-out'});
        }
        const a=document.createElement('a');
        a.href=url; a.hidden=true; document.body.appendChild(a);
        htmx.process(a); a.click(); setTimeout(() => a.remove(),1000);
    };
})();
