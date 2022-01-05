HTMLElement.prototype.isInvisible = function () {
    if (this.style.display === 'none') return true;
    if (getComputedStyle(this).display === 'none') return true;
    if (this.parentNode.isInvisible) return this.parentNode.isInvisible();
    return false;
};

// Filter form elements
const start_picker = new Litepicker({
    element: document.getElementById('date-start-input'),
    minDate: new Date(),
    resetButton: true
});
const end_picker = new Litepicker({
    element: document.getElementById('date-end-input'),
    minDate: new Date(),
    resetButton: true
});

// Get min and max durations and prices of tours
let slider_min_duration = 9e99;
let slider_max_duration = -9e99;
let slider_min_price = 9e99;
let slider_max_price = -9e99;

document.querySelectorAll('.tour-col').forEach(tour_col => {
    let duration = parseInt(tour_col.querySelector('.tour-data').getAttribute('duration'));
    let price = parseInt(tour_col.querySelector('.tour-data').getAttribute('price'));

    if (duration < slider_min_duration) {
        slider_min_duration = duration;
    } else if (duration > slider_max_duration) {
        slider_max_duration = duration;
    }

    if (price < slider_min_price) {
        slider_min_price = Math.floor(price / 1000) * 1000;
    } else if (price > slider_max_price) {
        slider_max_price = Math.ceil(price / 1000) * 1000;
    }
});

const duration_margin = 0.1 * (slider_max_duration - slider_min_duration);
let duration_slider = noUiSlider.create(document.getElementById('duration-input'), {
    start: [slider_min_duration, slider_max_duration],
    connect: true,
    range: {
        'min': Math.max(slider_min_duration - duration_margin, 0),
        'max': slider_max_duration + duration_margin - 1e-10
    },
    // step: 1,
    tooltips: true,
    format: {
        to: value => {
            let new_val = Math.min(Math.max(Math.round(value), slider_min_duration), slider_max_duration);
            return new_val + ' day' + (new_val === 1 ? '' : 's');
        },
        from: value => parseInt(value.replace(' days', '').replace('+', ''))
    },
    animate: true
});

duration_slider.on('change', (values, handle, unencoded, tap, positions, noUiSlider) => {
    unencoded[handle] = Math.min(Math.max(Math.round(unencoded[handle]), slider_min_duration), slider_max_duration);
    duration_slider.set(unencoded);
    // duration_slider.setHandle(handle, Math.round(unencoded[handle]), true, false);
})

mergeTooltips(document.getElementById('duration-input'), 30, ' - ', document.getElementById('duration-selection'));

const price_margin = 0.1 * (slider_max_price - slider_min_price);
let price_slider = noUiSlider.create(document.getElementById('price-input'), {
    start: [slider_min_price, slider_max_price],
    connect: true,
    range: {
        'min': slider_min_price - price_margin,
        'max': slider_max_price + price_margin
    },
    step: 100,
    tooltips: true,
    format: {
        to: value => 'US$' + Math.min(Math.max(Math.round(value), slider_min_price), slider_max_price),
        from: value => parseInt(value.replace('US$', '').replace('+', ''))
    },
    margin: 1000
});

price_slider.on('change', (values, handle, unencoded, tap, positions, noUiSlider) => {
    unencoded[handle] = Math.min(Math.max(unencoded[handle], slider_min_price), slider_max_price);
    price_slider.set(unencoded);
    // price_slider.setHandle(handle, Math.min(Math.max(unencoded[handle], slider_min_price), slider_max_price), true, false);
})

mergeTooltips(document.getElementById('price-input'), 40, ' - ', document.getElementById('price-selection'));


// Filter callbacks
let search_input = document.getElementById('search-input');
let destination_checkboxes = document.querySelectorAll('.destination-checkbox');
let start_date_input = document.getElementById('date-start-input');
let end_date_input = document.getElementById('date-end-input');

search_input.addEventListener('input', setVisibleTours);
duration_slider.on('update', setVisibleTours);
price_slider.on('update', setVisibleTours);
destination_checkboxes.forEach((cb) => cb.addEventListener('change', setVisibleTours))
start_picker.on('selected', setVisibleTours);
end_picker.on('selected', setVisibleTours);
start_picker.on('clear:selection', setVisibleTours);
end_picker.on('clear:selection', setVisibleTours);

function setVisibleTours() {
    let tour_cols = document.querySelectorAll('.tour-col');

    // Get filter parameters
    let duration_lims = duration_slider.get(true).map(Math.round);
    let price_lims = price_slider.get(true).map(Math.round);

    let start_date_lim = new Date(start_date_input.value);
    let end_date_lim = new Date(end_date_input.value);

    let allowed_destinations = [];
    destination_checkboxes.forEach(function (dest_cb) {
        if (dest_cb.checked) {
            allowed_destinations.push(dest_cb.id.replace('filter-destination-', ''));
        }
    })

    let search_terms = search_input.value;
    let tour_objs = [];
    tour_cols.forEach((tour_col) => {
        tour_objs.push({
            // 'title': tour_col.querySelector('.img-title-card .card-img-overlay .card-title').innerText,
            'title': tour_col.querySelector('.card-body .tour-name').innerText,
            'excerpt': tour_col.querySelector('.tour-text .card-body').innerText,
            'destinations': tour_col.querySelector('.tour-data').getAttribute('destinations'),
            'col_element': tour_col
        });
        tour_col.style.order = '';
    })

    let search = new Fuse(tour_objs, {
        includeScore: true,
        keys: ['title', 'excerpt', 'destinations']
    })
    let search_results = search.search(search_terms);

    let search_passed_cols = [];
    search_results.forEach((result, index) => {
        result['item']['col_element'].style.order = index + 1;
        search_passed_cols.push(result['item']['col_element']);
    })

    tour_cols.forEach(function (el) {
        let data = el.querySelector('.tour-data');

        let duration = parseInt(data.getAttribute('duration'));

        let price = parseInt(data.getAttribute('price'));

        let start_date = new Date(data.getAttribute('start_date'));
        let end_date = new Date(data.getAttribute('end_date'));

        let destinations = data.getAttribute('destinations').split(' ');

        if ((duration < duration_lims[0] && duration_lims[0] !== slider_min_duration) || (duration > duration_lims[1] && duration_lims[1] !== slider_max_duration)) {
            hideTour(el);
        } else if ((price < price_lims[0] && price_lims[0] !== slider_min_price) || (price > price_lims[1] && price_lims[1] !== slider_min_price)) {
            hideTour(el);
        } else if ((end_date < start_date_lim && start_date_input.value !== '') || (start_date > end_date_lim && end_date_input.value !== '')) {
            hideTour(el);
        } else if (!destinations.some(dest => allowed_destinations.includes(dest))) {
            hideTour(el);
        } else if (!search_passed_cols.includes(el) && search_terms !== '') {
            hideTour(el);
        } else {
            showTour(el);
        }
    })
}

function hideTour(col_el) {
    col_el.classList.add('should-hide');
    if (!(col_el.classList.contains('hide'))) {
        col_el.classList.add('hide-visually');
        col_el.addEventListener('transitionend', function (el) {
            if (col_el.classList.contains('should-hide')) {
                col_el.classList.add('hide');
            }
        }, {
            capture: false,
            once: true,
            passive: false
        });
    }
}

function showTour(col_el) {
    col_el.classList.remove('should-hide');
    col_el.classList.remove('hide');
    setTimeout(() => col_el.classList.remove('hide-visually'), 1);
}

/**
 * @param slider HtmlElement with an initialized slider
 * @param threshold Minimum proximity (in percentages) to merge tooltips
 * @param separator String joining tooltips
 * @param boundingElement Element that defines max & min pos of tooltip
 */
function mergeTooltips(slider, threshold, separator, boundingElement) {

    var textIsRtl = getComputedStyle(slider).direction === 'rtl';
    var isRtl = slider.noUiSlider.options.direction === 'rtl';
    var isVertical = slider.noUiSlider.options.orientation === 'vertical';
    var tooltips = slider.noUiSlider.getTooltips();
    var origins = slider.noUiSlider.getOrigins();

    // Move tooltips into the origin element. The default stylesheet handles this.
    tooltips.forEach(function (tooltip, index) {
        if (tooltip) {
            origins[index].appendChild(tooltip);
        }
    });

    slider.noUiSlider.on('update', function (values, handle, unencoded, tap, positions) {

        var pools = [[]];
        var poolPositions = [[]];
        var poolValues = [[]];
        var atPool = 0;

        // Assign the first tooltip to the first pool, if the tooltip is configured
        if (tooltips[0]) {
            pools[0][0] = 0;
            poolPositions[0][0] = positions[0];
            poolValues[0][0] = values[0];
        }

        for (var i = 1; i < positions.length; i++) {
            if (!tooltips[i] || (positions[i] - positions[i - 1]) > threshold) {
                atPool++;
                pools[atPool] = [];
                poolValues[atPool] = [];
                poolPositions[atPool] = [];
            }

            if (tooltips[i]) {
                pools[atPool].push(i);
                poolValues[atPool].push(values[i]);
                poolPositions[atPool].push(positions[i]);
            }
        }

        pools.forEach(function (pool, poolIndex) {
            var handlesInPool = pool.length;

            for (var j = 0; j < handlesInPool; j++) {
                var handleNumber = pool[j];

                if (j === handlesInPool - 1) {
                    var offset = 0;

                    poolPositions[poolIndex].forEach(function (value) {
                        offset += 1000 - value;
                    });

                    var direction = isVertical ? 'bottom' : 'right';
                    var last = isRtl ? 0 : handlesInPool - 1;
                    var lastOffset = 1000 - poolPositions[poolIndex][last];
                    offset = (textIsRtl && !isVertical ? 100 : 0) + (offset / handlesInPool) - lastOffset;

                    // Center this tooltip over the affected handles
                    tooltips[handleNumber].innerHTML = poolValues[poolIndex].join(separator);
                    tooltips[handleNumber].style.display = 'block';
                    tooltips[handleNumber].style[direction] = offset + '%';
                } else {
                    // Hide this tooltip
                    tooltips[handleNumber].style.display = 'none';
                }
            }

            // let margin = 10;
            // tooltips.forEach(function (tooltip, index) {
            //     if (tooltip && !tooltip.isInvisible()) {
            //         let maxRect = boundingElement.getBoundingClientRect();
            //         let rect = tooltip.getBoundingClientRect();
            //         let iter = 0;
            //         tooltip.style.right = window.getComputedStyle(tooltip).right;
            //         while (rect.left <= maxRect.left + margin) {
            //             tooltip.style.right = Math.round(parseInt(tooltip.style.right)) - 1 + 'px';
            //             rect = tooltip.getBoundingClientRect();
            //             if (iter++ > 500) {
            //                 console.log('breaking left');
            //                 console.log(tooltip.style.right);
            //                 console.log(rect, maxRect);
            //                 console.log(tooltip);
            //                 break;
            //             }
            //         }
            //         while (rect.right >= maxRect.right - margin) {
            //             tooltip.style.right = Math.round(parseInt(tooltip.style.right)) + 1 + 'px';
            //             rect = tooltip.getBoundingClientRect();
            //             if (iter++ > 500) {
            //                 console.log('breaking left');
            //                 console.log(tooltip);
            //             }
            //         }
            //     }
            // });
        });
    });
}
