//(function() {
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

    function normaliseData(data, canvas) {
        const { width, height } = canvas.getBoundingClientRect();

        return data.map(line => {
            return {
                ...line,
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
        const maxWidth = 2.5 / 1650 * width;
        const minWidth = 0.5 / 1650 * width;

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
    console.log("data: ", data);

    const signaturePad = new SignaturePad(canvas);
    const fullscreen_signaturePad = new SignaturePad(fullscreen_canvas);
    signaturePad.fromData(data ? denormaliseData(data, canvas) : []);
    fullscreen_signaturePad.fromData(data ? denormaliseData(data, fullscreen_canvas) : []);

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
        }
    });

    resizeObserver.observe(canvas);
    resizeObserver.observe(fullscreen_canvas);

    window.addEventListener('resize', () => {
        form.scrollTo({
            top: 0,
            left: 0,
            behavior: 'instant',
        });
        document.body.scrollTo({
            top: 0,
            left: 0,
            behavior: 'instant',
        });
    });
//})();
