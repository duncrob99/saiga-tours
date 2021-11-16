function minBBox(bbox1, bbox2) {
    let right1 = bbox1.x + bbox1.width;
    let right2 = bbox2[0] + bbox2[2];
    let top1 = bbox1.y + bbox1.height;
    let top2 = bbox2[1] + bbox2[3];

    let x = Math.min(bbox1.x, bbox2[0]);
    let y = Math.min(bbox1.y, bbox2[1]);

    let width = Math.max(right1, right2) - x;
    let height = Math.max(top1, top2) - y;

    return [x, y, width, height];
}

function make_map_work(destinations) {
    let dest_path;
    let min_bbox = [999999, 999999, -999999, -999999];
    for (let i = 0; i < destinations.length; i++) {
        dest_path = document.querySelector('#' + destinations[i][0]);
        if (dest_path !== null) {
            dest_path.classList.add('available');
            dest_path.addEventListener('click', () => {
                window.location.href = destinations[i][1];
            })

            min_bbox = minBBox(dest_path.getBBox(), min_bbox);
        }
    }

    let margin_factor = 0.3;
    min_bbox = [min_bbox[0] - margin_factor / 2 * min_bbox[2], min_bbox[1] - margin_factor / 2 * min_bbox[3], min_bbox[2] * (1 + margin_factor), min_bbox[3] * (1 + margin_factor)];
    document.querySelector('svg').setAttribute('viewBox', `${min_bbox[0]} ${min_bbox[1]} ${min_bbox[2]} ${min_bbox[3]}`);

    document.querySelectorAll('.pre-load').forEach((el) => el.classList.remove('pre-load'));
}
