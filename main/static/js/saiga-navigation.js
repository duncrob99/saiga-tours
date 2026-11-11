/* HTMX owns navigation and scroll position. Keep only compatibility for legacy SVG links. */
(() => {
    window.saigaNavigate = url => {
        if (location.pathname.startsWith('/replica/') && url.startsWith('/') && !url.startsWith('/replica/')) {
            url = '/replica' + url;
        }
        window.location.assign(url);
    };
    document.addEventListener('htmx:afterSwap', event => {
        if (event.detail.target?.id !== 'site-page') return;
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
        window.scrollTo({top: 0, left: 0, behavior: 'instant'});
    });
})();
