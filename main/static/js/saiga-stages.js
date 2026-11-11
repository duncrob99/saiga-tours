/* Load page sections in content priority order, independently of scroll position. */
(() => {
    const scriptURL = document.currentScript.src;
    let inFlight = null;
    let mapScripts;

    function pending() {
        return [...document.querySelectorAll('#site-page [data-saiga-stage]:not([data-saiga-started])')]
            .sort((a, b) => Number(a.dataset.priority) - Number(b.dataset.priority));
    }

    function pump() {
        if (inFlight && inFlight.isConnected) return;
        inFlight = pending()[0] || null;
        if (!inFlight) return;
        if (!window.htmx) {
            const url = new URL(location.href);
            url.searchParams.set('full', '1');
            location.replace(url.href);
            return;
        }
        inFlight.dataset.saigaStarted = 'true';
        htmx.trigger(inFlight, 'saiga-load');
    }

    function failed(target) {
        if (target !== inFlight) return;
        target.removeAttribute('data-saiga-started');
        target.setAttribute('data-saiga-failed', 'true');
        target.dataset.saigaStarted = 'true';
        target.innerHTML = '<button type="button" class="saiga-retry">Section unavailable. Try again</button>';
        target.querySelector('button').addEventListener('click', () => {
            target.removeAttribute('data-saiga-failed');
            target.removeAttribute('data-saiga-started');
            target.innerHTML = '<div class="saiga-skeleton">Loading…</div>';
            inFlight = null;
            pump();
        });
        inFlight = null;
        pump();
    }

    document.addEventListener('htmx:beforeTransition', e => {
        if (e.detail.target?.hasAttribute('data-saiga-stage')) e.preventDefault();
    });
    document.addEventListener('htmx:afterSwap', e => {
        if (e.detail.target?.id === 'site-page') inFlight = null;
        if (e.detail.target?.hasAttribute('data-saiga-stage')) inFlight = null;
        if (typeof minimise_images === 'function') minimise_images();
        pump();
    });
    document.addEventListener('htmx:responseError', e => failed(e.detail.elt));
    document.addEventListener('htmx:sendError', e => failed(e.detail.elt));
    document.addEventListener('htmx:timeout', e => failed(e.detail.elt));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', pump);
    else pump();

    function addScript(name) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = new URL(name, scriptURL).href;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Could not load ${name}`));
            document.head.appendChild(script);
        });
    }
    window.saigaLoadMap = async () => {
        // map.js binds its SVG when evaluated, so wait until the fragment is in the DOM.
        if (typeof window.make_map_work === 'function') {
            map_svg = SVG('.map svg');
            return;
        }
        if (!mapScripts) mapScripts = (async () => {
            if (!window.SVG) await addScript('svg.js');
            await addScript('svg.panzoom.min.js');
            await addScript('svg.easing.min.js');
            await addScript('map.js');
        })().catch(error => { mapScripts = null; throw error; });
        await mapScripts;
        map_svg = SVG('.map svg');
    };
})();
