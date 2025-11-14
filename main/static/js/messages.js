(function () {
    let message_container = document.getElementById('messages-container');
    const alert = (message, type, timeout, fadeDuration) => {
        type = type ?? "info";
        timeout = (timeout ?? 30)*1000;
        fadeDuration = (fadeDuration ?? 10)*1000;
        const wrapper = document.createElement('div');
        wrapper.innerHTML = [
            `<div class="alert alert-${type.toLowerCase()} alert-dismissible" role="alert">`,
            `   <div>${message}</div>`,
            '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
            '</div>'
        ].join('');

        const alert_el = message_container.appendChild(wrapper);
        alert_el.style.setProperty("--fade-duration", `${fadeDuration/1000}s`);
        let remove_timeout;
        let fadeTimeout;

        let fade_canceled = timeout === 0;
        function startTimeouts() {
            if (fade_canceled) return;

            fadeTimeout = window.setTimeout(() => {
                alert_el.classList.add("fadeout");

                remove_timeout = window.setTimeout(() => {
                    alert_el.remove();
                }, fadeDuration);
            }, timeout - fadeDuration);
        }

        function clearTimeouts() {
            window.clearTimeout(fadeTimeout);
            window.clearTimeout(remove_timeout);
            alert_el.classList.remove("fadeout");
        }

        function cancelFade() {
            fade_canceled = true;
            clearTimeouts();
        }

        alert_el.addEventListener("mouseenter", clearTimeouts);
        alert_el.addEventListener("mouseleave", startTimeouts);
        alert_el.addEventListener("click", cancelFade);

        startTimeouts();
    }
    window.show_message = alert;


    // Fetch messages from the server
    fetch('/messages/').then(response => response.json()).then(data => {
        console.log("Data: ", data);
        let messages = data.messages;
        let message_html = '';
        if (messages.length > 0) {
            messages.forEach(message => {
                alert(message.message, message.level);
            });
        }
    });

})();
