(function() {
    const form = document.querySelector('form');
    const SignaturePad = window.SignaturePad;
    const signaturePadWrapper = document.querySelector('.signature-pad-wrapper');
    const canvas = document.getElementById('signature-pad');
    const clearButton = document.getElementById('clear-signature');
    const undoButton = document.getElementById('undo-signature');
    const fullscreenButton = document.getElementById('fullscreen-signature');
    const rawSignatureInput = document.getElementById('signature-raw');
    const svgSignatureInput = document.getElementById('signature-svg');
    let data = rawSignatureInput.value ? JSON.parse(rawSignatureInput.value) : null;

    const fullscreen_signature_pad_wrapper = document.getElementById('fullscreen-signature-pad-wrapper');
    const fullscreen_canvas = document.getElementById('fullscreen-signature-pad');
    const fullscreen_clearButton = document.getElementById('fullscreen-clear-signature');
    const fullscreen_undoButton = document.getElementById('fullscreen-undo-signature');
    const fullscreen_fullscreenButton = document.getElementById('fullscreen-fullscreen-signature');

    const navbar_height = document.querySelector('.navbar').offsetHeight;
    let scroll_marker;
    let scroll_marker_locked = false;

    function convertRemToPixels(rem) {    
        return rem * parseFloat(getComputedStyle(document.documentElement).fontSize);
    }

    const scroll_margin = 10;
    const form_scroll_top = () => (window.innerWidth < 1000 ? navbar_height : navbar_height + ((window.innerHeight - navbar_height) - (window.innerHeight - convertRemToPixels(10)))/2) + scroll_margin;

    const clamp = (min, val, max) => Math.min(Math.max(min, val), max);
    const default_widths = (width) => {
        return {
            maxWidth: clamp(1.25, width * 2.5 / 1650, 5),
            minWidth: clamp(0.5, width * 0.5 / 1650, 2),
        };
    }

    function normaliseData(data, canvas) {
        const { width, height } = canvas.getBoundingClientRect();
        const { minWidth, maxWidth } = default_widths(width);

        return data.map(line => {
            return {
                ...line,
                maxWidth,
                minWidth,
                points: line.points.map(point => {
                    return {
                        ...point,
                        x: point.x / width,
                        y: point.y / height,
                    };
                }),
            };
        });
    }

    function denormaliseData(data, canvas) {
        const { width, height } = canvas.getBoundingClientRect();
        const { minWidth, maxWidth } = default_widths(width);

        return data.map(line => {
            return {
                ...line,
                maxWidth,
                minWidth,
                points: line.points.map(point => {
                    return {
                        ...point,
                        x: point.x * width,
                        y: point.y * height,
                    };
                }),
            };
        });
    }

    function setLineWidth(canvas, sig_pad, size) {
        size = size ?? 1;
        const { width } = canvas.getBoundingClientRect();
        const { minWidth, maxWidth } = default_widths(width);
        sig_pad.maxWidth = size * maxWidth
        sig_pad.minWidth = size * minWidth
        console.log("sig_pad.maxWidth: ", sig_pad.maxWidth);
        console.log("sig_pad.minWidth: ", sig_pad.minWidth);
    }

    const signaturePad = new SignaturePad(canvas);
    const fullscreen_signaturePad = new SignaturePad(fullscreen_canvas);
    signaturePad.fromData(data ? denormaliseData(data, canvas) : []);
    fullscreen_signaturePad.fromData(data ? denormaliseData(data, fullscreen_canvas) : []);

    setLineWidth(canvas, signaturePad);
    setLineWidth(fullscreen_canvas, fullscreen_signaturePad);

    const update_inputs = () => {
        if (signaturePad.isEmpty()) {
            rawSignatureInput.value = '';
            svgSignatureInput.value = '';
        } else {
            rawSignatureInput.value = JSON.stringify(data);
            svgSignatureInput.value = signaturePad.toDataURL('image/svg+xml');
        }
    }

    signaturePad.addEventListener('afterUpdateStroke', () => {
        data = normaliseData(signaturePad.toData(), canvas);
        fullscreen_signaturePad.fromData(denormaliseData(data, fullscreen_canvas));
        update_inputs();
    });

    fullscreen_signaturePad.addEventListener('afterUpdateStroke', () => {
        data = normaliseData(fullscreen_signaturePad.toData(), fullscreen_canvas);
        signaturePad.fromData(denormaliseData(data, canvas));
        update_inputs();
    });

    update_inputs();

    const clear_pads = () => {
        signaturePad.clear();
        fullscreen_signaturePad.clear();
        data = [];
        update_inputs();
    };

    clearButton.addEventListener('click', clear_pads);
    fullscreen_clearButton.addEventListener('click', clear_pads);

    const undo_pads = () => {
        if (data.length > 0) {
            data.pop(); // remove the last dot or line
            signaturePad.fromData(denormaliseData(data, canvas));
            fullscreen_signaturePad.fromData(denormaliseData(data, fullscreen_canvas));
            update_inputs();
        }
    };

    undoButton.addEventListener('click', undo_pads);
    fullscreen_undoButton.addEventListener('click', undo_pads);

    fullscreenButton.addEventListener('click', () => {
        document.documentElement.requestFullscreen();
        fullscreen_signature_pad_wrapper.classList.remove('hidden');
    });

    fullscreen_fullscreenButton.addEventListener('click', () => {
        document.exitFullscreen();
        fullscreen_signature_pad_wrapper.classList.add('hidden');
    });

    form.addEventListener('submit', update_inputs);

    const resizeObserver = new ResizeObserver(entries => {
        for (const entry of entries) {
            const { width, height } = entry.contentRect;
            console.log("width: ", width);
            console.log("height: ", height);
            const ratio = Math.max(window.devicePixelRatio || 1, 1);
            entry.target.width = width * ratio;
            entry.target.height = height * ratio;
            entry.target.getContext('2d').scale(ratio, ratio);
            signaturePad.clear();
            signaturePad.fromData(denormaliseData(data, canvas));
            fullscreen_signaturePad.clear();
            fullscreen_signaturePad.fromData(denormaliseData(data, fullscreen_canvas));
            setLineWidth(canvas, signaturePad);
            setLineWidth(fullscreen_canvas, fullscreen_signaturePad);
        }
    });

    resizeObserver.observe(canvas);
    resizeObserver.observe(fullscreen_canvas);

    function setScrollMarker() {
        if (scroll_marker_locked) return;

        let fields = document.querySelectorAll('.field, .section-header');
        let start = 0;
        let end = fields.length - 1;

        while (start < end) {
            let mid = Math.floor((start + end) / 2);
            let field = fields[mid];
            let rect = field.getBoundingClientRect();
            if (rect.top < form_scroll_top()) {
                start = mid + 1;
            } else {
                end = mid - 1;
            }
        }

        let field = fields[start];
        if (field.getBoundingClientRect().top < form_scroll_top()) {
            scroll_marker = fields[start + 1];
        } else {
            scroll_marker = field;
        }
    }

    let last_scroll_time = Date.now();
    const debounce_time = 100;
    function scrollToMarker() {
        last_scroll_time = Date.now();
        scroll_marker_locked = true;
        setTimeout(() => {
            if (Date.now() - last_scroll_time < debounce_time) return;
            let marker = scroll_marker;
            if (marker) {
                let body_scrollable = window.innerWidth < 1000;
                let form_scrollable = !body_scrollable;
                if (!body_scrollable) {
                    document.body.scrollTo({
                        top: 0,
                        left: 0,
                        behavior: 'instant'
                    });
                }
                if (!form_scrollable) {
                    form.scrollTo({
                        top: 0,
                        left: 0,
                        behavior: 'instant'
                    });
                }
                let cur_pos = marker.getBoundingClientRect().top;
                console.log(marker);
                console.log(cur_pos - form_scroll_top(), body_scrollable, form_scrollable);
                if (body_scrollable) {
                    //document.body.scrollBy(0, cur_pos - form_scroll_top() - 30);
                    document.body.scrollBy({
                        top: cur_pos - form_scroll_top(),
                        left: 0,
                        behavior: 'instant',
                    });
                } else if (form_scrollable) {
                    //form.scrollBy(0, cur_pos - form_scroll_top() - 30);
                    form.scrollBy({
                        top: cur_pos - form_scroll_top(),
                        left: 0,
                        behavior: 'instant',
                    });
                }

                scroll_marker_locked = false;
                /*
                form.scrollTo({
                    top: 0,
                    left: 0,
                    behavior: 'instant'
                });
                marker.scrollIntoView({
                    behavior: 'instant',
                });
                */
                setScrollMarker();
            }
        }, debounce_time);
    }

    setScrollMarker();
    
    window.addEventListener('scroll', setScrollMarker);
    document.body.addEventListener('scroll', setScrollMarker);
    form.addEventListener('scroll', setScrollMarker);

    window.addEventListener('resize', scrollToMarker);

    // Close fullscreen on click outside of the canvas and buttons
    fullscreen_signature_pad_wrapper.addEventListener('click', ev => {
        if (ev.target == fullscreen_signature_pad_wrapper) {
            document.exitFullscreen();
            fullscreen_signature_pad_wrapper.classList.add('hidden');
        }
    });
})();
