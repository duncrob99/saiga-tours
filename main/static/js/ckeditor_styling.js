(function() {
    function getFanBounds(fan) {
        let above_img = fan.querySelector('.above-img');
        let below_img = fan.querySelector('.below-img');
        let above_img_rect = above_img.getBoundingClientRect();
        let below_img_rect = below_img.getBoundingClientRect();

        return {
            left: Math.min(above_img_rect.left, below_img_rect.left),
            right: Math.max(above_img_rect.right, below_img_rect.right),
            top: Math.min(above_img_rect.top, below_img_rect.top),
            bottom: Math.max(above_img_rect.bottom, below_img_rect.bottom)
        };
    }

    function fitFans() {
        document.querySelectorAll('div.image-fan').forEach(fan => {
            console.log("Fitting fan image", fan);
            fan.style.setProperty('transform', `scale(1)`);
            let fan_bounds = getFanBounds(fan);
            let fan_parent = fan.parentElement;
            let max_bounds = fan_parent.getBoundingClientRect();

            let width_scale = (max_bounds.right - max_bounds.left) / (fan_bounds.right - fan_bounds.left);
            let height_scale = (max_bounds.bottom - max_bounds.top) / (fan_bounds.bottom - fan_bounds.top);
            let scale = Math.min(width_scale, height_scale);
            console.log(fan_bounds, max_bounds, scale);

            fan.style.setProperty('transform', `scale(${scale})`);
            fan.style.setProperty('transform-origin', 'left');
            fan_bounds = getFanBounds(fan);
            max_bounds = fan_parent.getBoundingClientRect();

            let transform_x = ((max_bounds.left + max_bounds.right) - (fan_bounds.left + fan_bounds.right)) / 2;
            let transform_y = ((max_bounds.top + max_bounds.bottom) - (fan_bounds.top + fan_bounds.bottom)) / 2;

            fan.style.setProperty('transform', `scale(${scale}) translateX(${transform_x}px) translateY(${transform_y}px)`);
            fan.style.setProperty('transform-origin', 'left');
        });
    }

    fitFans();
    document.addEventListener('resize', fitFans);
})();

(function() {
    document.querySelectorAll('.separator path').forEach(sep => {
        sep.style.transform = `translateX(${-Math.random() * 50}px)`;
    });

    function clearText() {
        // Ensure that the split-section separators doesn't block the text
        document.querySelectorAll('.split-section').forEach(split => {
            let pre_sep = split.querySelector('.pre-separator');
            let post_sep = split.querySelector('.post-separator');

            if (!pre_sep || !post_sep) return;

            let pre_sep_rect = pre_sep.getBoundingClientRect();
            let post_sep_rect = post_sep.getBoundingClientRect();

            // Get previous and next sibling
            let el_before_split = split.previousElementSibling;
            let el_after_split = split.nextElementSibling;

            if (el_after_split === null || el_before_split === null) return;

            // Get the bounds of the previous and next sibling
            let el_before_bounds = el_before_split.getBoundingClientRect();
            let el_after_bounds = el_after_split.getBoundingClientRect();

            // Calculate required extra margin
            let top_cover = el_before_bounds.bottom - pre_sep_rect.top;
            let bottom_cover = post_sep_rect.bottom - el_after_bounds.top;

            if (top_cover > 0) {
                el_before_split.style.marginBottom = `${parseInt(getComputedStyle(el_before_split).marginBottom) + top_cover}px`;
            }
            if (bottom_cover > 0) {
                el_after_split.style.marginTop = `${parseInt(getComputedStyle(el_after_split).marginTop) + bottom_cover}px`;
            }
        });
    }

    window.addEventListener('resize', clearText);
    clearText();
})();