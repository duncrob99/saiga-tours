let menu_instances = [];
let map_content_width = 0;

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


function make_map_work(destinations, width, height, hoverable, stops, editable, points) {
    resize_map(destinations, width, height, hoverable);

    if (stops !== undefined) {
        updateStops(stops, points, editable);
    }

    if (points !== undefined) {
        createPoints(points);
    }

    document.querySelectorAll('.pre-load').forEach((el) => el.classList.remove('pre-load'));
    window.addEventListener('resize', () => {
        resize_map(destinations, width, height, hoverable);
    })
}

function createPoints(points) {
    let map_svg = document.querySelector('.map svg');

    for (let i = 0; i < points.length; i++) {
        let point = points[i];

        let text_size = map_content_width * 0.03 * point.size;
        let pointer_size = map_content_width * 0.003 * point.size;

        let text_el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text_el.setAttributeNS(null, 'x', `${point.x}`);
        text_el.setAttributeNS(null, 'y', `${point.y}`);
        text_el.setAttributeNS(null, 'fill', 'black');
        text_el.setAttributeNS(null, 'stroke', 'none');
        text_el.setAttributeNS(null, 'style', `font-size: ${0}px;`);
        text_el.setAttributeNS(null, 'text-anchor', 'middle');
        text_el.classList.add('pointer-text');
        text_el.id = `pointer-text-${i}`;
        let text = document.createTextNode(point.name);
        text_el.appendChild(text);

        let point_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        point_el.setAttributeNS(null, 'd', 'm0 0s6-5.686 6-10a6 6 0 00-12 0c0 4.314 6 10 6 10zm0-7a3 3 0 110-6 3 3 0 010 6z');
        point_el.setAttributeNS(null, 'style', 'fill: red;');
        point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${0})`);
        point_el.id = `pointer-${i}`;
        point_el.classList.add('pointer');

        map_svg.appendChild(text_el);
        map_svg.appendChild(point_el);

        let transition_start_time;
        let transition_start_val = 0;
        let transition_cur_val = 0;
        let grow_dur = 500;
        let shrink_dur = 1000;
        let max_size = pointer_size;
        let min_size = 0;
        let changing = false;

        function set_size() {
            changing = true;
            let cur_time = new Date().getTime();
            if (point_el.classList.contains('growing') || point_el.classList.contains('shrinking')) {
                if (transition_start_time === undefined) {
                    transition_start_time = cur_time;
                    setTimeout(set_size, 50);
                } else if (cur_time - transition_start_time <= grow_dur && point_el.classList.contains('growing')) {
                    let perc_done = (new Date().getTime() - transition_start_time) / grow_dur;
                    transition_cur_val = transition_start_val + perc_done * (max_size - transition_start_val);
                    text_el.setAttributeNS(null, 'y', `${point.y - transition_cur_val * pointer_size * 20 / pointer_size}`);
                    text_el.setAttributeNS(null, 'style', `font-size: ${transition_cur_val * text_size / pointer_size}px;`);
                    point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${transition_cur_val})`);
                    setTimeout(set_size, 50);
                } else if (cur_time - transition_start_time <= shrink_dur && point_el.classList.contains('shrinking')) {
                    let perc_done = (new Date().getTime() - transition_start_time) / shrink_dur;
                    transition_cur_val = transition_start_val - perc_done * (transition_start_val - min_size);
                    text_el.setAttributeNS(null, 'y', `${point.y - transition_cur_val * pointer_size * 20 / pointer_size}`);
                    text_el.setAttributeNS(null, 'style', `font-size: ${transition_cur_val * text_size / pointer_size}px;`);
                    point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${transition_cur_val})`);
                    setTimeout(set_size, 50);
                } else if (point_el.classList.contains('growing')) {
                    point_el.classList.remove('growing');
                    point_el.classList.remove('shrinking');
                    text_el.setAttributeNS(null, 'y', `${point.y - pointer_size * 20}`);
                    text_el.setAttributeNS(null, 'style', `font-size: ${text_size}px;`);
                    point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${max_size})`);
                    transition_start_time = undefined;
                    changing = false;
                } else {
                    point_el.classList.remove('growing');
                    point_el.classList.remove('shrinking');
                    text_el.setAttributeNS(null, 'y', `${0}`);
                    text_el.setAttributeNS(null, 'style', `font-size: ${0}px;`);
                    point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${min_size})`);
                    transition_start_time = undefined;
                    changing = false;
                }
            }
        }

        window.addEventListener('mousemove', (ev) => {
            let map_rect = map_svg.getAttributeNS(null, 'viewBox').split(' ');
            let map_bounds = map_svg.getBoundingClientRect();
            let perc_x = (ev.x - map_bounds.x) / map_bounds.width;
            let perc_y = (ev.y - map_bounds.y) / map_bounds.height;
            let x = perc_x * parseInt(map_rect[2]) + parseInt(map_rect[0]);
            let y = perc_y * parseInt(map_rect[3]) + parseInt(map_rect[1]);

            let dist = Math.max(1 - Math.sqrt((x - point.x) ** 2 + (y - point.y) ** 2) / (point.radius * 20), 0);
            text_el.setAttributeNS(null, 'y', `${point.y - dist * pointer_size * 20}`);
            text_el.setAttributeNS(null, 'style', `font-size: ${dist * text_size}px;`);
            point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${pointer_size * dist})`);

            // if (Math.sqrt((x-point.x)**2 + (y-point.y)**2) < point.radius * map_content_width/10) {
            //     point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${pointer_size})`);
            //     text_el.setAttributeNS(null, 'style', `font-size: ${text_size}px;`);
            // } else {
            //     point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${0})`);
            //     text_el.setAttributeNS(null, 'style', `font-size: ${0}px;`);
            // }

            // if (Math.sqrt((x - point.x) ** 2 + (y - point.y) ** 2) < point.radius * map_content_width / 10) {
            //     point_el.classList.add('growing');
            //     point_el.classList.remove('shrinking');
            //     transition_start_val = transition_cur_val;
            //     transition_start_time = new Date().getTime();
            //     if (!changing) {
            //         set_size();
            //     }
            // } else {
            //     point_el.classList.remove('growing');
            //     point_el.classList.add('shrinking');
            //     transition_start_val = transition_cur_val;
            //     transition_start_time = new Date().getTime();
            //     if (!changing) {
            //         set_size();
            //     }
            // }
        })
    }

}

function updatePath(stops) {
    let map_svg = document.querySelector('.map svg');

    let path_width = map_content_width * 0.006;

    let x = [];
    let y = [];
    for (let i = 0; i < stops.length; i++) {
        x.push(stops[i].x);
        y.push(stops[i].y - 0.2);
    }

    let path_str = pathString(x, y);

    if (document.querySelector('#stop_path') === null) {
        let path_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path_el.id = 'stop_path';
        path_el.setAttributeNS(null, 'fill', 'none');
        path_el.setAttributeNS(null, 'stroke', '#106e2e');
        path_el.setAttributeNS(null, 'stroke-width', `${path_width}px`);
        path_el.setAttributeNS(null, 'd', path_str);
        map_svg.appendChild(path_el);
    } else {
        let path_el = document.querySelector('#stop_path');
        path_el.setAttributeNS(null, 'd', path_str);
    }
}

function updateStops(stops, editable) {
    let map_svg = document.querySelector('.map svg');

    let text_size = map_content_width * 0.04;
    let pointer_size = map_content_width * 0.004;

    updatePath(stops);

    document.querySelectorAll('.pointer').forEach(el => el.remove());
    document.querySelectorAll('.pointer-text').forEach(el => el.remove());
    menu_instances.forEach(instance => instance.destroy());

    // Create stop pointers
    for (let strIx in stops) {
        let i = parseInt(strIx);
        let stop = stops[i];
        let text_el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text_el.setAttributeNS(null, 'x', `${stop.x}`);
        text_el.setAttributeNS(null, 'y', `${stop.y - pointer_size * 20}`);
        text_el.setAttributeNS(null, 'fill', 'black');
        text_el.setAttributeNS(null, 'stroke', 'none');
        text_el.setAttributeNS(null, 'style', `font-size: ${text_size}px;`);
        text_el.setAttributeNS(null, 'text-anchor', 'middle');
        text_el.classList.add('pointer-text');
        text_el.id = `pointer-text-${i}`;
        let text = document.createTextNode(stop.name);
        text_el.appendChild(text);

        let point_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        point_el.setAttributeNS(null, 'd', 'm0 0s6-5.686 6-10a6 6 0 00-12 0c0 4.314 6 10 6 10zm0-7a3 3 0 110-6 3 3 0 010 6z');
        point_el.setAttributeNS(null, 'style', 'fill: red;');
        point_el.setAttributeNS(null, 'transform', `translate(${stop.x}, ${stop.y}) scale(${pointer_size})`);
        point_el.id = `pointer-${i}`;
        point_el.classList.add('pointer');

        point_el.addEventListener('click', () => {
            currentSlide(stop.day);
        });

        document.querySelector(`#id_stops-${stop.form_ix}-order`).value = i;

        let transition_start_time;
        let transition_start_val = pointer_size;
        let transition_cur_val = pointer_size;
        let grow_dur = 500;
        let shrink_dur = 1000;
        let max_size = pointer_size * 1.25;
        let min_size = pointer_size;
        let x = stop.x;
        let y = stop.y;

        function set_size() {
            let cur_time = new Date().getTime();
            if (point_el.classList.contains('growing') || point_el.classList.contains('shrinking')) {
                if (transition_start_time === undefined) {
                    transition_start_time = cur_time;
                    setTimeout(set_size, 1);
                } else if (cur_time - transition_start_time <= grow_dur && point_el.classList.contains('growing')) {
                    let perc_done = (new Date().getTime() - transition_start_time) / grow_dur;
                    let val_mod = -2.1 * perc_done ** 3 + 3.1 * perc_done ** 2;
                    transition_cur_val = transition_start_val + val_mod * (max_size - transition_start_val);
                    point_el.setAttributeNS(null, 'transform', `translate(${x}, ${y}) scale(${transition_cur_val})`);
                    setTimeout(set_size, 1);
                } else if (cur_time - transition_start_time <= shrink_dur && point_el.classList.contains('shrinking')) {
                    let perc_done = (new Date().getTime() - transition_start_time) / shrink_dur;
                    let val_mod = -2.1 * perc_done ** 3 + 3.1 * perc_done ** 2;
                    transition_cur_val = transition_start_val - val_mod * (transition_start_val - min_size);
                    point_el.setAttributeNS(null, 'transform', `translate(${x}, ${y}) scale(${transition_cur_val})`);
                    setTimeout(set_size, 1);
                } else if (point_el.classList.contains('growing')) {
                    point_el.classList.remove('growing');
                    point_el.classList.remove('shrinking');
                    point_el.setAttributeNS(null, 'transform', `translate(${x}, ${y}) scale(${max_size})`);
                    transition_start_time = undefined;
                } else {
                    point_el.classList.remove('growing');
                    point_el.classList.remove('shrinking');
                    point_el.setAttributeNS(null, 'transform', `translate(${x}, ${y}) scale(${min_size})`);
                    transition_start_time = undefined;
                }
            }
        }

        point_el.addEventListener('mouseenter', () => {
            point_el.classList.add('growing');
            point_el.classList.remove('shrinking');
            transition_start_val = transition_cur_val;
            transition_start_time = new Date().getTime();
            set_size();
            document.body.style.cursor = "pointer";
            //point_el.setAttributeNS(null, 'transform', `translate(${stop[1]}, ${stop[2]}) scale(0.23)`);
        });
        point_el.addEventListener('mouseleave', () => {
            point_el.classList.remove('growing');
            point_el.classList.add('shrinking');
            transition_start_val = transition_cur_val;
            transition_start_time = new Date().getTime();
            set_size();
            document.body.style.cursor = "auto";
            //point_el.setAttributeNS(null, 'transform', `translate(${stop[1]}, ${stop[2]}) scale(0.2)`);
        });

        if (editable) {
            point_el.addEventListener('mousedown', click_ev => {
                let start = {x: stops[i].x, y: stops[i].y}

                function move_point(move_ev) {
                    move_ev.preventDefault();
                    stops[i].x = start.x + (move_ev.x - click_ev.x) / getScale(map_svg);
                    stops[i].y = start.y + (move_ev.y - click_ev.y) / getScale(map_svg);
                    x = stops[i].x;
                    y = stops[i].y;
                    point_el.setAttributeNS(null, 'transform', `translate(${x} ${y}) scale(${transition_cur_val})`);
                    text_el.setAttributeNS(null, 'x', `${x}`);
                    text_el.setAttributeNS(null, 'y', `${y - pointer_size * 20}`);
                    updatePath(stops);

                    // Edit value in form
                    console.log(x, y);
                    document.getElementById(`id_stops-${stop.form_ix}-x`).value = x;
                    document.getElementById(`id_stops-${stop.form_ix}-y`).value = y;
                }

                window.addEventListener('mousemove', move_point);

                function stop_dragging() {
                    window.removeEventListener('mousemove', move_point);
                    window.removeEventListener('mouseup', stop_dragging);
                }

                window.addEventListener('mouseup', stop_dragging);
            })

            menu_instances.push(new BootstrapMenu(`#pointer-${i}`, {
                actionsGroups: [
                    ['deleteStop', 'renameStop'],
                    ['moveForwards', 'moveBackwards']
                ],
                actions: {
                    deleteStop: {
                        name: 'Delete stop',
                        onClick: () => {
                            document.querySelector(`#id_stops-${stop.form_ix}-DELETE`).checked = true;
                            stops.splice(i, 1);
                            updateStops(stops, true);
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, renameStop: {
                        name: 'Rename stop',
                        onClick: () => {
                            let modal = new bootstrap.Modal(document.querySelector('#rename-modal'));
                            let input = document.querySelector('#rename-stop-input');
                            let button = document.querySelector('#save-stop-rename');
                            input.setAttribute('placeholder', stop.name);
                            input.value = "";
                            button.onclick = function () {
                                stops[i].name = document.querySelector('#rename-stop-input').value;
                                document.querySelector(`#id_stops-${stop.form_ix}-name`).value = stops[i].name;
                                modal.hide();
                                updateStops(stops, true);
                            }
                            input.addEventListener('keyup', (ev) => {
                                if (ev.keyCode === 13) {
                                    button.click();
                                }
                            })
                            modal.show();
                            document.querySelector('#rename-modal').addEventListener('shown.bs.modal', () => input.focus());
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, changeDay: {
                        name: `Change day (currently ${stop.day})`,
                        onClick: () => {
                            let modal = new bootstrap.Modal(document.querySelector('#change-day-modal'));
                            let input = document.querySelector('#change-day-input');
                            let button = document.querySelector('#save-day-change');
                            input.setAttribute('placeholder', stop.day);
                            input.value = "";
                            button.onclick = function () {
                                stops[i].day = document.querySelector('#change-day-input').value;
                                document.querySelector(`#id_stops-${stop.form_ix}-day`).value = stops[i].day;
                                modal.hide();
                                updateStops(stops, true);
                            }
                            input.addEventListener('keyup', (ev) => {
                                if (ev.keyCode === 13) {
                                    button.click();
                                }
                            })
                            modal.show();
                            document.querySelector('#change-day-modal').addEventListener('shown.bs.modal', () => input.focus());
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, moveForwards: {
                        name: 'Move forwards',
                        onClick: () => {
                            if (i < stops.length) {
                                stops.splice(i + 1, 0, stops.splice(i, 1)[0])
                                updateStops(stops, true);
                            }
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, moveBackwards: {
                        name: 'Move backwards',
                        onClick: () => {
                            if (i > 0) {
                                stops.splice(i - 1, 0, stops.splice(i, 1)[0])
                                updateStops(stops, true);
                            }
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }
                }
            }))
        }

        map_svg.appendChild(text_el);
        map_svg.appendChild(point_el);
    }

    if (editable) {
        menu_instances.push(new BootstrapMenu('.map svg', {
            actions: [{
                name: 'Create stop',
                onClick: () => {
                    let viewBox = map_svg.getAttributeNS(null, 'viewBox').split(" ");
                    let new_ix = parseInt(document.querySelector('#id_stops-TOTAL_FORMS').value);
                    let new_name = 'New Stop';
                    let new_x = parseFloat(viewBox[0]) + 0.5 * parseFloat(viewBox[2]);
                    let new_y = parseFloat(viewBox[1]) + 0.5 * parseFloat(viewBox[3]);
                    let new_day = 1;
                    stops.push({
                        name: new_name,
                        x: new_x,
                        y: new_y,
                        day: new_day,
                        form_ix: new_ix
                    })
                    let new_form = document.querySelector('#form-template').cloneNode(true);
                    new_form.id = "";
                    new_form.innerHTML = new_form.innerHTML.replaceAll('%i', new_ix).replaceAll("%x", new_x)
                        .replaceAll('%y', new_y).replaceAll('%name', new_name)
                        .replaceAll('%day', new_day).replaceAll('%order', stops.length).replaceAll("\n", "").replaceAll('  ', "");
                    //document.querySelector('#editor-form').appendChild(new_form);
                    for (let i = 0; i < new_form.childNodes.length; i++) {
                        document.querySelector('#editor-form').appendChild(new_form.childNodes[i].cloneNode(true));
                    }
                    document.querySelector('#id_stops-TOTAL_FORMS').value = new_ix + 1;
                    updateStops(stops, true);
                },
                classNames: ['dropdown-item', 'alt-context-menu']
            }]
        }))
    }
}


function getScale(svg_el) {
    return svg_el.getBoundingClientRect().height / parseFloat(svg_el.getAttribute('viewBox').split(' ')[3])
}


function computeControlPoints(K) {
    let p1 = [];
    let p2 = [];
    let n = K.length - 1;

    /*rhs vector*/
    let a = [];
    let b = [];
    let c = [];
    let r = [];

    /*left most segment*/
    a[0] = 0;
    b[0] = 2;
    c[0] = 1;
    r[0] = K[0] + 2 * K[1];

    /*internal segments*/
    for (let i = 1; i < n - 1; i++) {
        a[i] = 1;
        b[i] = 4;
        c[i] = 1;
        r[i] = 4 * K[i] + 2 * K[i + 1];
    }

    /*right segment*/
    a[n - 1] = 2;
    b[n - 1] = 7;
    c[n - 1] = 0;
    r[n - 1] = 8 * K[n - 1] + K[n];

    /*solves Ax=b with the Thomas algorithm (from Wikipedia)*/
    for (let i = 1; i < n; i++) {
        let m = a[i] / b[i - 1];
        b[i] = b[i] - m * c[i - 1];
        r[i] = r[i] - m * r[i - 1];
    }

    p1[n - 1] = r[n - 1] / b[n - 1];
    for (let i = n - 2; i >= 0; --i)
        p1[i] = (r[i] - c[i] * p1[i + 1]) / b[i];

    /*we have p1, now compute p2*/
    for (let i = 0; i < n - 1; i++)
        p2[i] = 2 * K[i + 1] - p1[i + 1];

    p2[n - 1] = 0.5 * (K[n] + p1[n - 1]);

    return {p1: p1, p2: p2};
}

// function pathString(x1, y1, px1, py1, px2, py2, x2, y2) {
//     return `M${x1} ${y1} C ${px1} ${py1} ${px2} ${py2} ${x2} ${y2}`;
// }

function pathString(x, y) {
    let str;
    if (x.length > 2) {
        let px = computeControlPoints(x);
        let py = computeControlPoints(y);
        str = `M${x[0]} ${y[0]}`;
        for (let i = 0; i < x.length - 1; i++) {
            str += ` C${px.p1[i]} ${py.p1[i]} ${px.p2[i]} ${py.p2[i]} ${x[i + 1]} ${y[i + 1]}`;
        }
    } else if (x.length === 2) {
        str = `M${x[0]} ${y[0]} L${x[1]} ${y[1]}`;
    }
    return str;
}

function resize_map(destinations, width, height, hoverable) {
    if (width === undefined) {
        width = document.querySelector('#content-container').getBoundingClientRect().width;
    }
    if (height === undefined) {
        let navbar_height = document.querySelector('.navbar').getBoundingClientRect().height;
        height = document.documentElement.clientHeight - navbar_height;
    }
    if (hoverable === undefined) {
        hoverable = true;
    }

    let ar = width / height;

    let dest_path;
    let min_bbox = [999999, 999999, -999999, -999999];
    for (let i = 0; i < destinations.length; i++) {
        //dest_path = document.querySelector('#' + destinations[i][0]);
        dest_path = document.querySelector(`[title="${destinations[i][0]}"]`);
        if (dest_path !== null) {
            if (hoverable) {
                dest_path.classList.add('available')
                dest_path.addEventListener('click', () => {
                    window.location.href = destinations[i][1];
                })
            }

            min_bbox = minBBox(dest_path.getBBox(), min_bbox);
        }
    }

    map_content_width = min_bbox[2];
    let margin_factor = 0.2;
    min_bbox = [min_bbox[0] - margin_factor / 2 * min_bbox[2], min_bbox[1] - margin_factor / 2 * min_bbox[3], min_bbox[2] * (1 + margin_factor), min_bbox[3] * (1 + margin_factor)];
    if (ar !== undefined) {
        let cur_ar = min_bbox[2] / min_bbox[3];
        if (cur_ar > ar) {
            min_bbox[1] -= min_bbox[3] * (cur_ar / ar - 1) / 2;
            min_bbox[3] *= (cur_ar / ar);
        } else {
            min_bbox[0] -= min_bbox[2] * (ar / cur_ar - 1) / 2;
            min_bbox[2] *= (ar / cur_ar);
        }
    }
    document.querySelector('svg').setAttribute('viewBox', `${min_bbox[0]} ${min_bbox[1]} ${min_bbox[2]} ${min_bbox[3]}`);
}
