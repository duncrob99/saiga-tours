(function() {
    const search_modal = document.getElementById('search-modal');
    const search_input = search_modal.querySelector('input');
    const search_close = search_modal.querySelector('.search-close');
    const search_results = search_modal.querySelector('.results');
    const search_result_templates = search_modal.querySelector('.result-templates');
    const search_togglers = document.querySelectorAll('.toggle-search');
    const ai_answer = search_modal.querySelector('.ai-answer');
    const ai_wrapper = search_modal.querySelector('.ai-wrapper');
    const ai_search_button = search_modal.querySelector('.ai-button');

    const filter_dialog = search_modal.querySelector('#filter-dialog');
    const filter_open_button = search_modal.querySelector('.filter-open');
    const filter_close_button = filter_dialog.querySelector('.filter-close');

    const filters = filter_dialog.querySelector('.body');
    const type_checkboxes = filters.querySelectorAll('#filter-type-checkboxes input');

    window.mark_loaded = (el) => el.classList.add("loaded");

    function preload_thumbs(results) {
        results.map(res => res.metadata.image.replace(/^\/media\//, "/resized-image/") + "/18x12/")
            .forEach(preloadImage);
    }

    function generate_result(result) {
        const template = search_result_templates.querySelector(`[data-result-type="${result.type}"]`);
        if (template) {
            const template_content = template.innerHTML
                .replace(/ template-(.+?)="(.*?)"/g, ' $1="$2"')
                .replace(/{([A-z]+)}/g, (_, key) => {
                    if (key === 'date') {
                        return new Date(result.date).toLocaleDateString();
                    } else if (key === 'detail_type') {
                        return result.metadata.type === 'g' ? 'Guides' : 'Tours';
                    } else if (key === 'article_type') {
                        return result.metadata.type === 'a' ? 'Article' : 'News';
                    } else if (key === 'thumb_image') {
                        return result.metadata.image.replace(/^\/media\//, "/resized-image/") + "/18x12/";
                    } else if (key === 'image') {
                        return result.metadata.image.replace(/^\/media\//, "/resized-image/") + "/300x200/";
                    }
                    return result.metadata[key];
                });

            //const element = document.createElement('div');
            const el = document.createElement('div');
            el.innerHTML = template_content;
            return template_content;
        } else {
            const element = document.createElement('div');
            element.outerHTML = `<div class="result unknown-type"><div class="result-title">${result.title}</div><div class="result-description">${result.description}</div></div>`;
            return element;
        }
    }

    let fetch_controller = new AbortController();
    
    let last_search_time; // Used to prevent search spamming
    let last_search;
    async function search() {
        console.log("controller state: ", fetch_controller.signal);
        fetch_controller.abort();
        fetch_controller = new AbortController();
        try {
        const time_since_last_search = Date.now() - last_search_time;
        if (time_since_last_search < 500) return;
        last_search_time = Date.now();

        const query = search_input.value;
        if (query.length < 3) return;

        console.log(`Searching for ${query}`);
        search_input.classList.add("searching");

        const filter_string = get_filter_string();
        const search_string = filter_string ? `/api/search?q=${query}&${filter_string}` : `/api/search?q=${query}`;
        console.log(search_string);
        last_search = search_string;
        const response = await fetch(search_string, {signal: fetch_controller.signal});

        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }

        const results = (await response.json()).results;
        window.results = results;

        console.log(results);

        if (last_search !== search_string) return;
        search_results.innerHTML = '';
        preload_thumbs(results);
        for (const result of results) {
            const element = generate_result(result);
            //search_results.appendChild(element);
            search_results.insertAdjacentHTML("beforeend", element);
        }
        search_input.classList.remove("searching");
        } catch (error) {
            if (error.name === "AbortError") {
                console.log("aborting search");
                return;
            }
            search_input.classList.remove("searching");
            search_input.classList.remove("failed");
            search_input.classList.add("failed");
            console.error(error);
        }
    }
    
    search_input.addEventListener('input', () => {
        const cur_input = search_input.value;
        setTimeout(() => {
            if (cur_input !== search_input.value) return;
            const time_since_last_search = Date.now() - last_search_time;
            setTimeout(search, Math.max(0, 500 - time_since_last_search + 1));
        }, 500);
    });

    let last_ai_search_time; // Used to prevent search spamming
    let ai_search_timeout;
    let to_type = '';
    let in_tag = false;
    let type_interval;
    const wpm = 500;
    async function ai_search() {
        const time_since_last_search = Date.now() - last_ai_search_time;
        if (time_since_last_search < 2000) return;
        last_ai_search_time = Date.now();

        const query = search_input.value;
        if (query.length < 3) return;

        ai_answer.innerHTML = '';
        to_type = '';
        clearInterval(type_interval);

        ai_wrapper.setAttribute('data-state', 'loading');
        ai_search_button.setAttribute('data-state', 'loading');

        console.log(`Searching for ${query}`);

        const response = await fetch(`/api/ai_answer?q=${query}`)
            .catch(() => {
                ai_wrapper.setAttribute('data-state', 'error');
                ai_search_button.setAttribute('data-state', 'error');
            });

        let answer = (await response.json()).answer;

        // Replace markdown links with HTML links
        answer = answer.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, (_, text, link) => {
            console.log(text, link);
            return `<a href="${link}" class="nice-link">${text}</a>`;
        }).replace(/\n/g, '<br>');

        ai_wrapper.setAttribute('data-state', 'loaded');
        ai_search_button.setAttribute('data-state', 'loaded');

        to_type = answer;
        type_interval = setInterval(typeLetter, 60 / wpm * 1000 / 5);
    }

    function typeLetter() {
        let tag_match = to_type.match(/^<([A-z]+)(.*?)>(.*?)<\/\1>/);
        let end_tag_match = to_type.match(/^<\/([A-z]+)>/);
        if (tag_match) {
            console.log('tag', tag_match);
            ai_answer.innerHTML += `<${tag_match[1]}${tag_match[2]}>${tag_match[3][0]}</${tag_match[1]}>`;
            in_tag = true;
            to_type = `${tag_match[3].slice(1)}</${tag_match[1]}>${to_type.slice(tag_match[0].length)}`;
            return;
        } else if (in_tag && !end_tag_match) {
            console.log('in tag');
            ai_answer.innerHTML = ai_answer.innerHTML.replace(/<([A-z]+)(.*?)>(.*?)<\/\1>$/, (_, tag, attrs, text) => {
                console.log(tag, attrs, text);
                return `<${tag}${attrs}>${text}${to_type[0]}</${tag}>`;
            });
            to_type = to_type.slice(1);
            return;
        } else if (end_tag_match && in_tag) {
            console.log('end tag', end_tag_match);
            in_tag = false;
            to_type = to_type.slice(end_tag_match[0].length);
        }

        let br_match = to_type.match(/^<br>/);
        if (br_match) {
            console.log('br');
            ai_answer.innerHTML += '<br>';
            to_type = to_type.slice(br_match[0].length);
            return;
        }

        ai_answer.innerHTML += to_type[0];
        to_type = to_type.slice(1);
        if (to_type.length === 0) clearInterval(type_interval);
    }

    ai_search_button?.addEventListener('click', () => {
        const time_since_last_search = Date.now() - last_ai_search_time;
        console.log(time_since_last_search);
        clearTimeout(ai_search_timeout);
        ai_search_timeout = setTimeout(ai_search, Math.max(0, 2000 - time_since_last_search + 1));
    });

    search();

    let transition_timeout = {};
    const transition_duration = 200;
    let modal_open = {};

    function open_modal(el) {
        if (modal_open[el.id]) return;
        el.showModal();
        setTimeout(() => {
            console.log(el);
            el.classList.add('show');
            modal_open[el.id] = true;
            console.log(modal_open);
        }, 0);
    }

    function close_modal(el) {
        if (!modal_open[el.id]) return;
        el.classList.remove('show');
        clearTimeout(transition_timeout[el.id]);
        transition_timeout[el.id] = setTimeout(() => {
            console.log(el);
            el.close();
            modal_open[el.id] = false;
            console.log(modal_open);
            console.log("Transition timeout: ", transition_timeout);
        }, transition_duration);
        console.log('close');
    }

    search_togglers.forEach(toggler => {
        toggler.addEventListener('click', () => open_modal(search_modal));
    });

    search_close.addEventListener('click', () => close_modal(search_modal));

    window.addEventListener('click', (event) => {
        const modal_bounds = search_modal.getBoundingClientRect();
        if (event.target === search_modal && event.clientX < modal_bounds.left || event.clientX > modal_bounds.right || event.clientY < modal_bounds.top || event.clientY > modal_bounds.bottom) {
            close_modal(search_modal);
        }

        const filter_dialog_bounds = filter_dialog.getBoundingClientRect();
        if (event.target === filter_dialog && event.clientX < filter_dialog_bounds.left || event.clientX > filter_dialog_bounds.right || event.clientY < filter_dialog_bounds.top || event.clientY > filter_dialog_bounds.bottom) {
            close_modal(filter_dialog);
        }
    });

    filter_open_button.addEventListener('click', () => {
        open_modal(filter_dialog);
    });

    filter_close_button.addEventListener('click', () => {
        close_modal(filter_dialog);
    });

    window.open_modal = open_modal;
    window.close_modal = close_modal;


    function get_filter_string() {
        return Array.from(type_checkboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => `include_${checkbox.value}=true`)
            .join('&');
    }

    filters.addEventListener('change', search);
})();
