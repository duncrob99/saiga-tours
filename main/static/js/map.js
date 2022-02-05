function getBase64(file, onLoadCallback) {
    return new Promise(function (resolve, reject) {
        let reader = new FileReader();
        reader.onload = function () {
            resolve(reader.result);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

let btn = document.querySelector('#map-download');
if (btn) {
    let svg = document.querySelector('.map svg');

    let resolution_slider;
    window.addEventListener('load', () => {
        resolution_slider = noUiSlider.create(document.getElementById('resolution-input'), {
            start: 1,
            range: {
                min: 0.1,
                max: 10
            },
            tooltips: true,
            format: {
                to: value => `${Math.round(value * 100) / 100}x`,
                from: value => parseInt(value)
            },
            step: 0.01
        });
    })

    let triggerDownload = (imgURI) => {
        let a = document.createElement('a');

        a.setAttribute('download', 'map.png');
        a.setAttribute('href', imgURI);
        a.setAttribute('target', '_blank');

        a.click();
    }

    let save = (resolution) => {
        let styled_svg = svg.cloneNode(true);
        styled_svg.querySelectorAll('#country-labels text').forEach(el => {
            el.remove();
        })
        // let stop_font = window.getComputedStyle(styled_svg.querySelectorAll('.pointer-text')[0]).font;
        let root_style = window.getComputedStyle(document.querySelector(':root'));
        let stop_font = root_style.getPropertyValue('--bs-body-font-family');
        styled_svg.querySelectorAll('.pointer-text').forEach(el => {
            el.setAttribute('font-family', stop_font);
        })
        styled_svg.querySelectorAll('.mapsvg-region').forEach(el => {
            if (destinations.map(dest => dest[0]).includes(el.getAttribute('title'))) {
                el.style.fill = root_style.getPropertyValue('--accent-background');
            }
        })
        getBase64(font_file).then(result => {
            // let defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            // let style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
            styled_svg.querySelector('defs').innerHTML = `<style>@font-face{font-family: "Poppin"; src:url("${result}") format("woff"); font-weight: normal; font-style: normal;}</style>`
            // styled_svg.appendChild(defs);
            // console.log(result);
            let data = (new XMLSerializer()).serializeToString(styled_svg);
            let svgBlob = new Blob([data], {type: 'image/svg+xml;charset=utf-8'});
            let url = URL.createObjectURL(svgBlob);

            svgUrlToPng(url, resolution, triggerDownload);
        });
    }

    function svgUrlToPng(svgUrl, resolution, callback) {
        const svgImage = document.createElement('img');
        // imgPreview.style.position = 'absolute';
        // imgPreview.style.top = '-9999px';
        document.body.appendChild(svgImage);
        svgImage.onload = function () {
            const canvas = document.createElement('canvas');
            canvas.width = svgImage.clientWidth * resolution;
            canvas.height = svgImage.clientHeight * resolution;
            const canvasCtx = canvas.getContext('2d');
            canvasCtx.drawImage(svgImage, 0, 0, canvas.width, canvas.height);
            const imgData = canvas.toDataURL('image/png');
            callback(imgData);
            // document.body.removeChild(imgPreview);
            svgImage.remove();
        };
        svgImage.src = svgUrl;
    }

    btn.addEventListener('click', () => {
        let modal = new bootstrap.Modal(document.querySelector('#save-modal'));
        let button = document.querySelector('#save-resolution');
        resolution_slider.set(1);
        button.onclick = function () {
            save(resolution_slider.get(true));
            modal.hide();
        }
        modal.show();
    });
}


let menu_instances = [];
let map_content_width = 0;
let map_centre;
let arrow_instances = [];

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

let map_settings;

function make_map_work(destinations, width, height, hoverable, stops, editable, points) {
    resize_map(destinations, width, height, hoverable);

    if (stops !== undefined) {
        // stops = stops.map(stop => {
        //     if (stop.x !== undefined && stop.y !== undefined) {
        //         return stop;
        //     } else {
        //         stop.x = map_centre.x;
        //         stop.y = map_centre.y;
        //         return stop;
        //     }
        // })
        stops.forEach(stop => {
            if (stop.x === undefined) {
                stop.x = map_centre.x;
            }
            if (stop.y === undefined) {
                stop.y = map_centre.y;
            }
        })

        updateStops(stops, points, editable);
    }

    if (points !== undefined) {
        createPoints(points);
    }

    document.querySelectorAll('.pre-load').forEach((el) => el.classList.remove('pre-load'));

    if (stops === undefined || stops.length === 0) {
        setCountryNames(destinations);
    }

    window.addEventListener('resize', () => {
        resize_map(destinations, width, height, hoverable);
        //setCountryNames(destinations);
    })

    map_settings = {
        destinations: destinations,
        width: width,
        height: height,
        hoverable: hoverable,
        stops: stops,
        editable: editable,
        points: points
    }

    setMapZooming(true);
}

function setMapZooming(en) {
    function zoomIn() {
        let cur_zoom = map_svg.zoom();
        map_svg.animate({when: 'now'}).zoom(cur_zoom * 1.5);
    }

    function zoomOut() {
        let cur_zoom = map_svg.zoom();
        map_svg.animate({when: 'now'}).zoom(cur_zoom / 1.5);
    }

    function resetZoom() {
        resize_map(map_settings.destinations, map_settings.width, map_settings.height, map_settings.hoverable);
    }

    let map_svg = SVG(document.querySelector('.map svg'))
    if (en) {
        console.log('zooming');
        map_svg.panZoom({
            zoomMax: 20,
            zoomMin: 1,
            wheelZoom: false
        });

        document.querySelector('#map-zoom-in').addEventListener('click', zoomIn);
        document.querySelector('#map-zoom-out').addEventListener('click', zoomOut);
        document.querySelector('#map-zoom-reset').addEventListener('click', resetZoom);
    } else {
        console.log('no zooming');
        map_svg.panZoom(false);
    }
}

function setCountryNames(destinations) {
    let svg_map = SVG('.map svg');
    let text_els = [];

    for (let country of destinations) {
        //let text_el = new Array(svg_map.querySelectorAll('#country-labels text')).filter(el => el.innerText === country[0]);
        // let text_els = Array.from(svg_map.querySelectorAll('#country-labels text tspan')).filter(el => el.textContent === country[0]);
        // if (text_els.length > 0) {
        //     let text_el = SVG(text_els[0]);
        //     text_el.css('display', 'initial');
        //
        //     let path_el = document.querySelector(`[title="${country[0]}"]`);
        //
        //     path_el.addEventListener('mouseenter', () => {
        //         //text_el.attr('fill', '#3a8f9e');
        //         text_el.parent().animate({
        //             swing: true,
        //             when: 'now',
        //         }).ease('bounce').scale(1.2);
        //     })
        //     path_el.addEventListener('mouseleave', () => {
        //         //text_el.attr('fill', null);
        //         text_el.parent().animate({
        //             swing: true,
        //             when: 'now',
        //         }).scale(1 / 1.2);
        //     })
        // }
        let path_el = SVG(`[title="${country[0]}"]`);
        if (path_el !== null) {
            // let text_el = SVG('.map svg').text(country[0]).cx(path_el.cx()).cy(path_el.cy());
            // let point_array = [for (let path of path_el.array()) if (path.length === 3) path.slice(1)]
            let {com, area} = findCentroid(path_el, country[0]);
            text_els.push(svg_map.text(country[0]).font('size', 5).cx(com.x).cy(com.y).css('pointer-events', 'none').fill('black').stroke('none'));
            // svg_map.circle(1).fill('red').cx(com.x).cy(com.y);
        }
    }

    text_els.forEach(el => {
        el.remember('orig_x', el.cx());
        el.remember('orig_y', el.cy());

        el.moved = () => dist(el.cx(), el.cy(), el.remember('orig_x'), el.remember('orig_y'));
    });

    let change = true;
    let x_margin = 5;
    let y_margin = 1;
    let margin = 5;
    while (change) {
        change = false;
        for (let text_el of text_els) {
            let other_els = text_els.filter(el => el !== text_el);
            for (let other_el of other_els) {
                //console.log(rect_distance(text_el.bbox(), other_el.bbox()));
                if (text_el.bbox().x < other_el.bbox().x2 + x_margin && text_el.bbox().x2 + x_margin > other_el.bbox().x && (text_el.bbox().y < other_el.bbox().y2 + y_margin && text_el.bbox().y2 + y_margin > other_el.bbox().y)) {
                    // if (rect_distance(text_el.bbox(), other_el.bbox()) <= margin) {
                    let direction = {
                        x: text_el.bbox().cx - other_el.bbox().cx,
                        y: text_el.bbox().cy - other_el.bbox().cy
                    };
                    let mag = Math.sqrt(direction.x ** 2 + direction.y ** 2);
                    direction = {x: direction.x / mag, y: direction.y / mag};

                    if (text_el.moved() <= other_el.moved()) {
                        text_el.dmove(direction.x, direction.y);
                    }
                    other_el.dmove(-direction.x, -direction.y);

                    change = true;
                }
            }
        }
    }

    // for (let text_el of text_els) {
    // SVG('.map svg').rect(text_el.bbox().width + margin, text_el.bbox().height + margin).cx(text_el.cx()).cy(text_el.cy()).stroke('red').fill('none');
    // SVG('.map svg').rect(text_el.bbox().width + x_margin, text_el.bbox().height + y_margin).cx(text_el.cx()).cy(text_el.cy()).stroke('red').fill('none');
    // SVG('.map svg').rect(text_el.bbox().width, text_el.bbox().height).cx(text_el.cx()).cy(text_el.cy()).stroke('blue').fill('none');
    // console.log(text_el.moved());
    // }
}

//function rect_distance(x1, y1, x1b, y1b, x2, y2, x2b, y2b) {
function rect_distance(bbox1, bbox2) {
    let x1 = bbox1.x;
    let y1 = bbox1.y;
    let x1b = bbox1.x2;
    let y1b = bbox1.y2;
    let x2 = bbox2.x;
    let y2 = bbox2.y;
    let x2b = bbox2.x2;
    let y2b = bbox2.y2;
    let left = x2b < x1;
    let right = x1b < x2;
    let bottom = y2b < y1;
    let top = y1b < y2;
    if (top && left) {
        return dist(x1, y1b, x2b, y2);
    } else if (left && bottom) {
        return dist(x1, y1, x2b, y2b);
    } else if (bottom && right) {
        return dist(x1b, y1, x2, y2b);
    } else if (right && top) {
        return dist(x1b, y1b, x2, y2);
    } else if (left) {
        return x1 - x2b;
    } else if (right) {
        return x2 - x1b;
    } else if (bottom) {
        return y1 - y2b;
    } else if (top) {
        return y2 - y1b;
    } else {
        return 0
    }
}

function dist(x1, y1, x2, y2) {
    return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

function findCentroid(path) {
    let polygons = path.array().reduce((polygons, path) => {
        if (path[0] === 'M') {
            polygons.push([{x: path[1], y: path[2]}]);
        } else if (path[0] === 'L') {
            polygons[polygons.length - 1].push({x: path[1], y: path[2]});
        } else if (path[0] === 'V') {
            let cur_poly = polygons[polygons.length - 1];
            polygons[polygons.length - 1].push({x: cur_poly[cur_poly.length - 1].x, y: path[1]});
        } else if (path[0] === 'H') {
            let cur_poly = polygons[polygons.length - 1];
            polygons[polygons.length - 1].push({y: cur_poly[cur_poly.length - 1].y, x: path[1]});
        }
        return polygons;
    }, [])
    let coms = [];
    let areas = [];
    for (let pts of polygons) {
        let nPts = pts.length;
        let off = pts[0];
        let twicearea = 0;
        let x = 0;
        let y = 0;
        let p1, p2;
        let f;
        for (let i = 0, j = nPts - 1; i < nPts; j = i++) {
            p1 = pts[i];
            p2 = pts[j];
            f = (p1.x - off.x) * (p2.y - off.y) - (p2.x - off.x) * (p1.y - off.y);
            twicearea += f;
            x += (p1.x + p2.x - 2 * off.x) * f;
            y += (p1.y + p2.y - 2 * off.y) * f;
        }
        f = twicearea * 3;

        let com = {
            x: x / f + off.x,
            y: y / f + off.y
        };
        coms.push(com);
        areas.push(Math.abs(twicearea / 2));
    }
    let area = areas.reduce((sum, value) => sum + value);
    let com = coms.reduce((sum, value, ix) => {
        return {x: sum.x + value.x * areas[ix] / area, y: sum.y + value.y * areas[ix] / area};
    }, {x: 0, y: 0});

    return {com: com, area: area};
}

function createPoints(points) {
    let map_svg = document.querySelector('.map svg');

    for (let i = 0; i < points.length; i++) {
        let point = points[i];

        let text_size = map_content_width * 0.01 * point.size;
        text_size = text_size - text_size % 1;
        let pointer_size = map_content_width * 0.001 * point.size;
        let default_pointer_scale = 1;

        // let text_el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        // text_el.setAttributeNS(null, 'x', `${point.x}`);
        // text_el.setAttributeNS(null, 'y', `${point.y}`);
        // text_el.setAttributeNS(null, 'fill', 'black');
        // text_el.setAttributeNS(null, 'stroke', 'none');
        // text_el.setAttributeNS(null, 'style', `font-size: ${text_size}px;`);
        // text_el.setAttributeNS(null, 'text-anchor', 'middle');
        // text_el.setAttributeNS(null, 'transform', `scale(0.001)`);
        // text_el.classList.add('pointer-text');
        // text_el.id = `pointer-text-${i}`;
        // let text = document.createTextNode(point.name);
        // text_el.appendChild(text);
        //SVG(text_el).path('m0 0q3-1 6 0');

        let text_svg = SVG(map_svg).text(point.name).font({
            size: text_size,
            anchor: 'middle'
        }).fill('black').stroke('none').transform({tx: point.x, ty: point.y}).opacity(0).css('pointer-events', 'none');

        let point_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        // point_el.setAttributeNS(null, 'd', 'm0 0s6-5.686 6-10a6 6 0 00-12 0c0 4.314 6 10 6 10zm0-7a3 3 0 110-6 3 3 0 010 6z');
        let point_radius = 4;
        point_el.setAttributeNS(null, 'd', `m0 0 m -${point_radius},0 a ${point_radius},${point_radius} 0 1,0 ${2 * point_radius},0 a ${point_radius},${point_radius} 0 1,0 ${-2 * point_radius},0`);
        point_el.setAttributeNS(null, 'style', 'fill: red;');
        point_el.setAttributeNS(null, 'transform', `translate(${point.x}, ${point.y}) scale(${0})`);
        point_el.id = `pointer-${i}`;
        point_el.classList.add('pointer');

        // map_svg.appendChild(text_el);
        map_svg.appendChild(point_el);

        let activation_circle = SVG(map_svg).circle(point.radius * 2 * 10).cx(point.x).cy(point.y).fill('#0000').stroke('#0000').css('pointer-events', 'none');
        // text_svg.animate({when: 'now'}).transform({scale: 0.001, origin: 'center center'});
        map_svg.addEventListener('mousemove', ev => {
            let mouse = SVG(map_svg).point(ev.pageX, ev.pageY);
            let cur_scale = SVG(point_el).transform().scaleX;
            SVG(point_el).transform({scale: cur_scale, tx: point.x, ty: point.y, origin: 'bottom center'});
            if (activation_circle.inside(mouse.x, mouse.y)) {
                SVG(point_el).animate({when: 'now'}).ease('bounce').transform({
                    scale: pointer_size,
                    tx: point.x,
                    ty: point.y,
                    origin: 'bottom center'
                });
                text_svg.opacity(1);
                text_svg.animate({when: 'now'}).ease('bounce').transform({
                    scale: 1,
                    ty: point.y - pointer_size * 20,
                    tx: point.x
                });
            } else {
                SVG(point_el).animate({when: 'now'}).transform({
                    scale: 2 ** -20,
                    tx: point.x,
                    ty: point.y,
                    origin: 'bottom center'
                });
                text_svg.animate({when: 'now'}).transform({scale: 2 ** -20, tx: point.x, ty: point.y});
            }
            text_svg.rebuild();
        })
    }

}

SVG.Path.prototype.segmentLengths = function () {
    function get_endpoint(arr) {
        return {
            x: arr.slice(-2)[0],
            y: arr.slice(-1)[0],
            string: function () {
                return `M${this.x} ${this.y}`
            }
        }
    }

    function get_string(arr) {
        return arr[0] + arr.slice(1).join(' ');
    }

    let segments = [];
    let last_point = get_endpoint(this.array()[0]);

    this.array().slice(1).forEach((el, i) => {
        let path_str = `${last_point.string()} ${get_string(el)}`;
        segments.push(SVG().path(path_str).length());
        last_point = get_endpoint(el);
    })

    return segments;
}

function updatePath(stops) {
    if (stops.length < 2) return;
    let map_svg = document.querySelector('.map svg');

    let path_width = map_content_width * 0.006;

    let x = [];
    let y = [];
    let prestrength = [];
    let poststrength = [];
    for (let i = 0; i < stops.length; i++) {
        x.push(stops[i].x);
        y.push(stops[i].y - 0.2);
        prestrength.push(stops[i].prestrength);
        poststrength.push(stops[i].poststrength);
    }

    let path_str = pathString(x, y, prestrength, poststrength);

    let path_el;
    if (document.querySelector('#stop_path') === null) {
        path_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path_el.id = 'stop_path';
        path_el.setAttributeNS(null, 'fill', 'none');
        path_el.setAttributeNS(null, 'stroke', '#106e2e');
        path_el.setAttributeNS(null, 'stroke-width', `${path_width}px`);
        path_el.setAttributeNS(null, 'd', path_str);
        // path_el.setAttributeNS(null, 'marker-mid', 'url(#head)');
        // path_el.setAttributeNS(null, 'marker-end', 'url(#head)');
        map_svg.appendChild(path_el);
    } else {
        path_el = document.querySelector('#stop_path');
        path_el.setAttributeNS(null, 'd', path_str);
    }

    // Add arrows in the middle of each segment
    arrow_instances.forEach(arrow => {
        arrow.remove();
    });

    let segment_lengths = SVG(path_el).segmentLengths();
    console.log(segment_lengths);
    let unmarked_ix = [];
    for (let i in stops) {
        if (!stops[i].arrow_break) {
            unmarked_ix.push(parseInt(i));
        }
    }
    for (let i of unmarked_ix.reverse()) {
        segment_lengths[i - 1] += segment_lengths[i];
        segment_lengths.splice(i, 1);
    }

    let tot_len = segment_lengths[0] / 2;
    for (let i = 0; i < segment_lengths.length; i++) {
        let point = SVG(path_el).pointAt(tot_len);
        let after = SVG(path_el).pointAt(tot_len + 0.1);
        let before = SVG(path_el).pointAt(tot_len - 0.1);
        let angle = Math.atan2(after.y - before.y, after.x - before.x) * 180 / Math.PI - 90;
        console.log(after, before, angle);
        arrow_instances.push(SVG(map_svg).path('M-1 0 L0 1 L1 0').cx(point.x).cy(point.y).fill('none').stroke({
            width: 0.3,
            color: '#106e2e'
        }).rotate(angle).scale(0.3 * map_content_width / 18.5084228515625));
        tot_len += segment_lengths[i] / 2 + segment_lengths[i + 1] / 2;
    }

    console.log(segment_lengths);
}

function updateStops(stops, editable) {
    let map_svg = document.querySelector('.map svg');

    let text_size = map_content_width * 0.04;
    let pointer_size = map_content_width * 0.004;

    updatePath(stops);

    document.querySelectorAll('.pointer').forEach(el => el.remove());
    document.querySelectorAll('.stop-pointer').forEach(el => el.remove());
    document.querySelectorAll('.pointer-text').forEach(el => el.remove());
    menu_instances.forEach(instance => instance.destroy());

    // Create stop pointers
    for (let strIx in stops) {
        let i = parseInt(strIx);
        let stop = stops[i];

        let point_el;
        let text_el;
        if (stop.marked) {
            text_el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text_el.setAttributeNS(null, 'x', `${stop.x + stop.text_x}`);
            text_el.setAttributeNS(null, 'y', `${stop.y + stop.text_y - pointer_size * 20}`);
            text_el.setAttributeNS(null, 'fill', 'black');
            text_el.setAttributeNS(null, 'stroke', 'none');
            text_el.setAttributeNS(null, 'style', `font-size: ${text_size}px;`);
            text_el.setAttributeNS(null, 'text-anchor', 'middle');
            text_el.classList.add('pointer-text');
            text_el.id = `pointer-text-${i}`;
            let text = document.createTextNode(stop.name);
            text_el.appendChild(text);

            point_el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            // point_el.setAttributeNS(null, 'd', 'm0 0s6-5.686 6-10a6 6 0 00-12 0c0 4.314 6 10 6 10zm0-7a3 3 0 110-6 3 3 0 010 6z');
            let point_radius = 4;
            point_el.setAttributeNS(null, 'd', `m0 0 m -${point_radius},0 a ${point_radius},${point_radius} 0 1,0 ${2 * point_radius},0 a ${point_radius},${point_radius} 0 1,0 ${-2 * point_radius},0`);
            point_el.setAttributeNS(null, 'style', 'fill: red;');
            point_el.setAttributeNS(null, 'transform', `translate(${stop.x}, ${stop.y}) scale(${pointer_size})`);
            point_el.id = `pointer-${i}`;
            point_el.classList.add('stop-pointer');

            if (!editable) {
                point_el.addEventListener('click', () => {
                    document.querySelector('#itinerary').scrollIntoView({behavior: 'smooth'});
                    currentSlide(stop.day);
                });
            }

            point_el.addEventListener('mouseenter', () => {
                SVG(point_el).animate({when: 'now'}).transform({
                    scale: pointer_size * 1.2,
                    origin: 'center',
                    tx: stop.x,
                    ty: stop.y
                });
                document.body.style.cursor = "pointer";
            });
            point_el.addEventListener('mouseleave', () => {
                SVG(point_el).animate({when: 'now'}).transform({
                    scale: pointer_size,
                    origin: 'center',
                    tx: stop.x,
                    ty: stop.y
                });
                document.body.style.cursor = "auto";
            });
            map_svg.appendChild(text_el);
            map_svg.appendChild(point_el);
        } else if (editable) {
            point_el = SVG(map_svg).circle(1).cx(stop.x).cy(stop.y).addClass('stop-pointer').node;
            point_el.id = `pointer-${i}`;
        }

        if (editable) {
            document.querySelector(`#id_stops-${stop.form_ix}-order`).value = i;
            document.querySelector(`#id_stops-${stop.form_ix}-marked`).checked = stop.marked;
            document.querySelector(`#id_stops-${stop.form_ix}-arrow_break`).checked = stop.arrow_break;

            point_el.addEventListener('mousedown', click_ev => {
                let start = {x: stops[i].x, y: stops[i].y};

                function move_point(move_ev) {
                    move_ev.preventDefault();
                    stop.x = start.x + (move_ev.x - click_ev.x) / getScale(map_svg);
                    stop.y = start.y + (move_ev.y - click_ev.y) / getScale(map_svg);
                    stops[i] = stop;
                    updatePath(stops);

                    if (stop.marked) {
                        SVG(point_el).animate({when: 'now', duration: 1}).transform({
                            scale: pointer_size,
                            origin: 'center',
                            tx: stop.x,
                            ty: stop.y
                        });
                        SVG(text_el).font({anchor: 'middle'}).cx(stop.x + stop.text_x).cy(stop.y + stop.text_y - pointer_size * 20);
                    } else {
                        point_el.instance.animate({when: 'now', duration: 1}).cx(stop.x).cy(stop.y);
                    }

                    // Edit value in form
                    document.getElementById(`id_stops-${stop.form_ix}-x`).value = stop.x;
                    document.getElementById(`id_stops-${stop.form_ix}-y`).value = stop.y;
                }

                window.addEventListener('mousemove', move_point);

                function stop_dragging() {
                    window.removeEventListener('mousemove', move_point);
                    window.removeEventListener('mouseup', stop_dragging);
                }

                window.addEventListener('mouseup', stop_dragging);
            })

            if (text_el) {
                window.addEventListener('mousedown', click_ev => {
                    let box = text_el.getBoundingClientRect();
                    if (click_ev.x >= box.left && click_ev.x <= box.right && click_ev.y >= box.top && click_ev.y <= box.bottom) {
                        let start = {x: stops[i].text_x, y: stops[i].text_y};

                        function move_text(move_ev) {
                            move_ev.preventDefault();
                            stop.text_x = start.x + (move_ev.x - click_ev.x) / getScale(map_svg);
                            stop.text_y = start.y + (move_ev.y - click_ev.y) / getScale(map_svg);
                            stops[i] = stop;

                            SVG(text_el).font({anchor: 'middle'}).cx(stop.x + stop.text_x).cy(stop.y + stop.text_y - pointer_size * 20);

                            // Edit value in form
                            document.getElementById(`id_stops-${stop.form_ix}-text_x`).value = stop.text_x;
                            document.getElementById(`id_stops-${stop.form_ix}-text_y`).value = stop.text_y;
                        }

                        window.addEventListener('mousemove', move_text);

                        function stop_dragging() {
                            window.removeEventListener('mousemove', move_text);
                            window.removeEventListener('mouseup', stop_dragging);
                        }

                        window.addEventListener('mouseup', stop_dragging);
                    }
                })
            }

            menu_instances.push(new BootstrapMenu(`#pointer-${i}`, {
                actionsGroups: [
                    ['deleteStop', 'renameStop', 'changeMarked', 'toggleArrow'],
                    ['moveForwards', 'moveBackwards'],
                    ['change prestrength', 'change poststrength']
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
                    }, changeMarked: {
                        name: stop.marked ? 'Unmark stop' : 'Mark stop',
                        onClick: () => {
                            stops[i].marked = !stop.marked;
                            updateStops(stops, true);
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, changePrestrength: {
                        name: 'Change prestrength',
                        onClick: () => {
                            let modal = new bootstrap.Modal(document.querySelector('#change-prestrength-modal'));
                            let input = document.querySelector('#change-prestrength-input');
                            let button = document.querySelector('#save-prestrength-change');
                            input.setAttribute('placeholder', stop.prestrength);
                            input.value = "";
                            button.onclick = function () {
                                stops[i].prestrength = parseFloat(document.querySelector('#change-prestrength-input').value);
                                document.querySelector(`#id_stops-${stop.form_ix}-prestrength`).value = stops[i].prestrength;
                                modal.hide();
                                updateStops(stops, true);
                            }
                            input.addEventListener('keyup', (ev) => {
                                if (ev.keyCode === 13) {
                                    button.click();
                                }
                            })
                            modal.show();
                            document.querySelector('#change-prestrength-modal').addEventListener('shown.bs.modal', () => input.focus());
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, changePoststrength: {
                        name: 'Chnage poststrength',
                        onClick: () => {
                            let modal = new bootstrap.Modal(document.querySelector('#change-poststrength-modal'));
                            let input = document.querySelector('#change-poststrength-input');
                            let button = document.querySelector('#save-poststrength-change');
                            input.setAttribute('placeholder', stop.poststrength);
                            input.value = "";
                            button.onclick = function () {
                                stops[i].poststrength = parseFloat(document.querySelector('#change-poststrength-input').value);
                                document.querySelector(`#id_stops-${stop.form_ix}-poststrength`).value = stops[i].poststrength;
                                modal.hide();
                                updateStops(stops, true);
                            }
                            input.addEventListener('keyup', (ev) => {
                                if (ev.keyCode === 13) {
                                    button.click();
                                }
                            })
                            modal.show();
                            document.querySelector('#change-poststrength-modal').addEventListener('shown.bs.modal', () => input.focus());
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }, toggleArrow: {
                        name: !stop.arrow_break ? 'Make arrow break' : 'Remove arrow break',
                        onClick: () => {
                            stops[i].arrow_break = !stop.arrow_break;
                            updateStops(stops, true);
                        },
                        classNames: ['dropdown-item', 'alt-context-menu']
                    }
                }
            }))
        }
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
                        form_ix: new_ix,
                        text_x: 0,
                        text_y: 0,
                        prestrength: 1,
                        poststrength: 1,
                        arrow_break: true
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

function pathString(x, y, prestrength, poststrength) {
    let str;
    if (prestrength === undefined) {
        prestrength = Array(x.length).fill(1);
    }
    if (poststrength === undefined) {
        poststrength = Array(x.length).fill(1);
    }
    if (x.length > 2) {
        let px = computeControlPoints(x);
        let py = computeControlPoints(y);
        str = `M${x[0]} ${y[0]}`;
        let strength = 2;
        for (let i = 0; i < x.length - 1; i++) {
            str += ` C${(px.p1[i] - x[i]) * poststrength[i] + x[i]} ${(py.p1[i] - y[i]) * poststrength[i] + y[i]} ${(px.p2[i] - x[i + 1]) * prestrength[i + 1] + x[i + 1]} ${(py.p2[i] - y[i + 1]) * prestrength[i + 1] + y[i + 1]} ${x[i + 1]} ${y[i + 1]}`;
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
                let start_ev;
                dest_path.addEventListener('mousedown', (ev) => {
                    start_ev = ev
                })
                dest_path.addEventListener('mouseup', (end_ev) => {
                    console.log(start_ev, end_ev);
                    if (start_ev !== undefined) {
                        if ((start_ev.x - end_ev.x) ** 2 + (start_ev.y - end_ev.y) ** 2 < 10 ** 2) {
                            window.location.href = destinations[i][1];
                        }
                        start_ev = undefined;
                    }
                })
            }

            min_bbox = minBBox(dest_path.getBBox(), min_bbox);
        }
    }

    map_content_width = min_bbox[2];
    map_centre = {x: min_bbox[0] + min_bbox[2] / 2, y: min_bbox[1] + min_bbox[3] / 2};
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
    //document.querySelector('svg').setAttribute('viewBox', `${min_bbox[0]} ${min_bbox[1]} ${min_bbox[2]} ${min_bbox[3]}`);
    Visibility.onVisible(() => {
        SVG('.map svg').animate({
            when: 'now',
            duration: 2000
        }).ease('quartInOut').viewbox(`${min_bbox[0]} ${min_bbox[1]} ${min_bbox[2]} ${min_bbox[3]}`);
    })
}
