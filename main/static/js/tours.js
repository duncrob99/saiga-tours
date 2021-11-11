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

const slider_min_duration = 0;
const slider_max_duration = 60;
let duration_slider = noUiSlider.create(document.getElementById('duration-input'), {
    start: [slider_min_duration, slider_max_duration],
    connect: true,
    range: {
        'min': slider_min_duration,
        'max': slider_max_duration
    },
    step: 1,
    tooltips: true,
    format: {
        to: value => Math.floor(value) + (value >= slider_max_duration ? '+' : '') + ' days',
        from: value => parseInt(value.replace(' days', '').replace('+', ''))
    },
});

const slider_min_price = 0;
const slider_max_price = 20000;
let price_slider = noUiSlider.create(document.getElementById('price-input'), {
    start: [slider_min_price, slider_max_price],
    connect: true,
    range: {
        'min': slider_min_price,
        'max': slider_max_price
    },
    step: 500,
    tooltips: true,
    format: {
        to: value => 'US$' + Math.floor(value) + (value >= slider_max_price ? '+' : ''),
        from: value => parseInt(value.replace('US$', '').replace('+', ''))
    },
    margin: 1000
});


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
    let duration_lims = duration_slider.get(true);
    let price_lims = price_slider.get(true);
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
            'title': tour_col.querySelector('.img-title-card .card-img-overlay .card-title').innerText,
            'excerpt': tour_col.querySelector('.tour-text .card-body').innerText,
            'col_element': tour_col
        });
        tour_col.style.order = '';
    })

    let search = new Fuse(tour_objs, {
        includeScore: true,
        keys: ['title', 'excerpt']
    })
    let search_results = search.search(search_terms);

    let search_passed_cols = [];
    search_results.forEach((result, index) => {
        console.log(result);
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