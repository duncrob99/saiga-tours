(function () {
    let initialised = false;
    let testimonial_slider = document.querySelector('#testimonial-slider');
    let testimonials = testimonial_slider.querySelectorAll('.testimonial');
    let testimonial_index = 0;
    let testimonial_interval = setInterval(testimonial_slider_loop, 10000);

    function testimonial_slider_loop() {
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
        testimonial_index = (testimonial_index + 1) % testimonials.length;
        initialised = true;
    }

    // Listen to resize events of the slider using ResizeObserver
    let resize_observer = new ResizeObserver(() => {
        setTimeout(resize_testimonials, 500);
    });
    function resize_testimonials() {
        testimonial_slider.style.height = '0';
        // Set the height of the slider to the height of the tallest testimonial
        // let max_height = 0;
        // testimonials.forEach(function (testimonial) {
        //     max_height = Math.max(max_height, testimonial.offsetHeight);
        // });
        // testimonial_slider.style.height = `${max_height}px`;

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
        let margin = 100;
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
                while (container_box.top + testimonial.offsetHeight > fold_box.bottom - margin && words.length > 0 && fills_space(testimonial)) {
                    words.pop();
                    text.innerText = words.join(' ') + '...';
                    card_box = testimonial.getBoundingClientRect();
                }
            }
            // else if (testimonial_start !== null && card_box.height + testimonial_start.getBoundingClientRect().height > fold_box.height - margin) {
            //     let words = text.innerText.split(' ');
            //     while (card_box.height + testimonial_start.getBoundingClientRect().height > fold_box.height - margin && words.length > 0 && fills_space(testimonial)) {
            //         words.pop();
            //         text.innerText = words.join(' ') + '...';
            //         card_box = testimonial.getBoundingClientRect();
            //     }
            // }

            max_height = Math.max(max_height, testimonial.offsetHeight + 2*margin);

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
})();