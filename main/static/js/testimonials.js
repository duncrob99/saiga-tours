(function () {
    let initialised = false;
    let testimonial_slider = document.querySelector('#testimonial-slider');
    let testimonials = testimonial_slider.querySelectorAll('.testimonial');
    let testimonial_index = 0;
    let animation_complete = true;

    let normal_delay = 5000;
    let long_delay = 20000;
    let testimonial_interval = setInterval(testimonial_slider_loop, normal_delay);

    function testimonial_slider_loop(reverse = false) {
        if (!animation_complete) return;
        if (Visibility.hidden()) {
            clearInterval(testimonial_interval);
            Visibility.onVisible(() => {
                testimonial_interval = setInterval(testimonial_slider_loop, normal_delay);
            });
        }
        animation_complete = false;
        testimonial_index = (testimonial_index + (reverse ? -1 : 1)) % testimonials.length;
        if (testimonial_index < 0) {
            testimonial_index += testimonials.length;
        }
        testimonials.forEach(function (testimonial, index) {
            testimonial.classList.remove('centre');
            testimonial.classList.remove('left-1');
            testimonial.classList.remove('left-2');
            testimonial.classList.remove('right-1');
            testimonial.classList.remove('right-2');
            testimonial.classList.remove('left-3');
            testimonial.classList.remove('right-3');
            testimonial.classList.remove('hidden');

            if (initialised) {
                console.log("initialised");
                testimonial.classList.add('animated');
            } else {
                console.log("Not initialised, not animating");
            }

            let mod_distance = (testimonial_index - index) % testimonials.length;
            if (mod_distance < 0) {
                mod_distance += testimonials.length;
            }
            // Set class to be distance from testimonial_index
            if (index === testimonial_index) {
                testimonial.classList.add('centre');
            } else if (mod_distance < 4) {
                testimonial.classList.add(`left-${mod_distance}`);
            } else if (mod_distance > testimonials.length - 4) {
                testimonial.classList.add(`right-${testimonials.length - mod_distance}`);
            } else {
                testimonial.classList.add('hidden');
            }
        });
        initialised = true;
        setTimeout(function () {
            animation_complete = true;
        }, 1000);
    }

    // Listen to resize events of the slider using ResizeObserver
    let resize_observer = new ResizeObserver(() => {
        setTimeout(resize_testimonials, 500);
    });
    function resize_testimonials() {
        testimonial_slider.style.height = '0';

        let fills_space = (testimonial) => {
            let quote = testimonial.querySelector('.quote');
            let natural_height = quote.offsetHeight;
            quote.classList.add('testing-height');
            let testing_height = quote.offsetHeight;
            quote.classList.remove('testing-height');
            return Math.abs(natural_height - testing_height) < 10;
        }

        let untransformed_height = testimonial => {
            // Remove transformations from the testimonial
            let transform = testimonial.style.transform;
            testimonial.style.transform = '';
            let height = testimonial.offsetHeight;
            testimonial.style.transform = transform;
            return height;
        }

        // Elide testimonial text if it makes the card taller than the container
        let max_height = 0;
        let margin = 10;
        let testimonial_start = document.querySelector('.testimonial-start');
        if (testimonial_start) {
            document.getElementById('testimonial-sizer').style.top = `${testimonial_start.getBoundingClientRect().top + document.body.scrollTop}px`;
            console.log(testimonial_start.getBoundingClientRect().top + document.body.scrollTop);
        }
        let fold_box = document.getElementById('testimonial-sizer').getBoundingClientRect();
        testimonials.forEach(function (testimonial) {
            testimonial.classList.remove('animated');
            let text = testimonial.querySelector('.quote');
            // Reset elided text
            if (text.dataset.original_text) {
                text.innerText = text.dataset.original_text;
            } else {
                text.dataset.original_text = text.innerText;
            }

            let card_box = testimonial.getBoundingClientRect();
            let container_box = testimonial_slider.getBoundingClientRect();

            // Ensure card bottom is above the fold
            if (container_box.top + testimonial.offsetHeight > fold_box.bottom - margin) {
                let words = text.innerText.split(' ');
                testimonial.classList.add('minimised');
                while (container_box.top + testimonial.offsetHeight > fold_box.bottom - margin && words.length > 0 && fills_space(testimonial)) {
                    words.pop();
                    text.innerText = words.join(' ') + '...';
                    card_box = testimonial.getBoundingClientRect();
                }
            } else {
                testimonial.classList.remove('minimised');
            }

            max_height = Math.max(max_height, testimonial.offsetHeight);

            if (initialised) {
                testimonial.classList.add('animated');
                testimonial.classList.add('initialised');
            }
        });
        // Set height of container
        testimonial_slider.style.height = `${max_height}px`;
        while (testimonial_slider.getBoundingClientRect().bottom < fold_box.bottom) {
            max_height += 1;
            testimonial_slider.style.height = `${max_height}px`;
        }
    }

    // Observe the slider
    resize_observer.observe(testimonial_slider);
    resize_observer.observe(document.getElementById('testimonial-sizer'));
    resize_observer.observe(document.body);
    testimonial_slider_loop();

    document.querySelector('#testimonial-slider .left').addEventListener('click', () => {
        testimonial_slider_loop(true);
        clearInterval(testimonial_interval);
        testimonial_interval = setTimeout(() => {
            testimonial_slider_loop();
            testimonial_interval = setInterval(testimonial_slider_loop, normal_delay);
        }, long_delay);
    });

    document.querySelector('#testimonial-slider .right').addEventListener('click', () => {
        testimonial_slider_loop(false);
        clearInterval(testimonial_interval);
        testimonial_interval = setTimeout(() => {
            testimonial_slider_loop();
            testimonial_interval = setInterval(testimonial_slider_loop, normal_delay);
        }, long_delay);
    });

    let country_selector = document.querySelector('.country-selector select');
    let initial_countries = [
        'AU',
        'US',
        'GB',
        'FR',
        'ME',
        'CA',
        'NL',
        'KZ',
        'IN',
        'IE'
    ]

    let country_choices = new Choices(country_selector, {
        allowHTML: false,
        removeItemButton: true,
        duplicateItemsAllowed: false,
        searchResultLimit: 10,
        resetScrollPosition: false,
        sorter: (a, b) => {
            if (initial_countries.includes(a.value) && !initial_countries.includes(b.value)) {
                return -1;
            } else if (!initial_countries.includes(a.value) && initial_countries.includes(b.value)) {
                return 1;
            } else if (initial_countries.includes(a.value) && initial_countries.includes(b.value)) {
                return initial_countries.indexOf(a.value) - initial_countries.indexOf(b.value);
            } else {
                return a.label.localeCompare(b.label);
            }
        }
    });

    country_selector.addEventListener('showDropdown', () => {
        document.querySelector('.country-selector').classList.add('open');
    });

    country_selector.addEventListener('hideDropdown', () => {
        document.querySelector('.country-selector').classList.remove('open');
    });

    // country_choices.setChoices([
    //     {value: 'au', label: 'Australia', selected: true},
    //     {value: 'us', label: 'United States', selected: true},
    // ], 'value', 'label', true);

    window.country_choices = country_choices;
    
    const preloadImage = src =>
        new Promise((resolve, reject) => {
            const image = new Image()
            image.onload = resolve
            image.onerror = reject
            image.src = src
        })

    window.setFlag = (el, src) => {
        el.classList.add('transition-out');
        setTimeout(async () => {
            await preloadImage(src)
            el.src = src;
            el.classList.remove('transition-out');
            el.classList.add('transition-in');
            setTimeout(() => {
                el.classList.remove('transition-in');
            }, 500);
        }, 500);
    }
})();