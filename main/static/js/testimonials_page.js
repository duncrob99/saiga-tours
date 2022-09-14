(function() {
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