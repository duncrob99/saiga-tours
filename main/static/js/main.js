function minimise_images() {
    document.querySelectorAll(`img`).forEach(img => {
        let img_src;
        if (img.hasAttribute('src')) {
            console.log('from src');
            img_src = img.getAttribute('src');
        } else if (img.hasAttribute('full-size-src')) {
            console.log('from full-size-src');
            img_src = img.getAttribute('full-size-src');
        }
        console.log('orig src: ', img_src);
        if (img_src.startsWith('/static')) return;
        let img_size = `${Math.ceil(parseInt(getComputedStyle(img).width) * window.devicePixelRatio)}x${Math.ceil(parseInt(getComputedStyle(img).height) * window.devicePixelRatio)}`;
        img_src = img_src.replace(/^\/media\//, '').replaceAll(/\/resized-image\//g, '').replaceAll(/\/[0-9]+x[0-9]+\//g, '');
        console.log('final src: ', `/resized-image/${img_src}/${img_size}/`);
        img.setAttribute('src', `/resized-image/${img_src}/${img_size}/`);
    })
}

minimise_images();