/* Keep the first page response small; retrieve the full nested menu later. */
(() => {
    let loading;
    async function loadNavbar(openMenu = false) {
        const container = document.getElementById('saiga-navbar-container');
        if (!container) return;
        if (!loading) {
            let url = container.dataset.navUrl;
            if (location.pathname.startsWith('/replica/') && url.startsWith('/') && !url.startsWith('/replica/')) url = '/replica' + url;
            loading = fetch(url, {credentials: 'same-origin'}).then(response => {
                if (!response.ok) throw new Error(`Navigation returned ${response.status}`);
                return response.text();
            }).then(html => {
                container.innerHTML = html;
                // The wrapper owns the sticky position; nested sticky navs can
                // jump over the newly swapped page on mobile.
                container.querySelector('nav.navbar')?.classList.remove('sticky-top');
                if (window.htmx) htmx.process(container);
                if (window.saigaRefreshNavbar) window.saigaRefreshNavbar();
                return container;
            }).catch(error => {
                loading = null;
                throw error;
            });
        }
        try {
            await loading;
            if (openMenu && window.bootstrap) {
                bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('offcanvasNav')).show();
            }
        } catch (error) {
            if (openMenu) {
                const button = container.querySelector('[data-saiga-open-menu]');
                if (button) button.setAttribute('aria-label', 'Menu unavailable; tap to retry');
            }
        }
    }
    document.addEventListener('click', event => {
        if (!event.target.closest('[data-saiga-open-menu]')) return;
        event.preventDefault();
        loadNavbar(true);
    });
    document.addEventListener('saiga:stages-complete', () => loadNavbar());
})();
