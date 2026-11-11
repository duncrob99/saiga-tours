/* HTMX loads the section placeholders with hx-trigger=load/revealed.
   Only the legacy interactive SVG map requires an on-demand script loader. */
(() => {
    const scriptURL = document.currentScript.src;
    let mapScripts;
    const addScript = name => new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = new URL(name, scriptURL).href;
        script.onload = resolve;
        script.onerror = () => reject(new Error('Map script unavailable: ' + name));
        document.head.appendChild(script);
    });
    window.saigaLoadMap = async () => {
        if (!mapScripts) {
            mapScripts = (async () => {
                if (!window.SVG) await addScript('svg.min.js');
                await addScript('svg.panzoom.min.js');
                await addScript('svg.easing.min.js');
                await addScript('map.js');
            })().catch(error => { mapScripts = null; throw error; });
        }
        await mapScripts;
        if (window.SVG && document.querySelector('.map svg')) window.map_svg = SVG('.map svg');
    };
})();
