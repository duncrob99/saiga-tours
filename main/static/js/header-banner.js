(function() {
    function set_title_size() {
        let title = document.getElementById('title');
        let content = document.getElementById('content-container');
        if (!(title && content)) return;

        title.style.fontSize = '';
        while (title.getBoundingClientRect().right > content.getBoundingClientRect().right) {
            title.style.fontSize = parseFloat(getComputedStyle(title).fontSize) - 1 + 'px';
        }
    }

    function set_banner_height() {
        let banner = document.getElementById('header-banner');
        let title = document.getElementById('title');

        if (!banner || !title) return;

        banner.style.height = '';
        while (banner.getBoundingClientRect().bottom < title.getBoundingClientRect().bottom) {
            banner.style.height = parseInt(getComputedStyle(banner).height) + 1 + 'px';
        }

        document.getElementById('header-content').style.height = banner.style.height;
    }

    function size_banner() {
        set_title_size();
        set_banner_height();
    }

    size_banner()
    window.addEventListener('resize', size_banner);
})();
