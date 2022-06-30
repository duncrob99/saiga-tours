document.querySelectorAll('.separator path').forEach(sep => {
    sep.style.transform = `translateX(${-Math.random()*50}px)`;
});

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