(function () {
    let message_container = document.getElementById('messages-container');
    const alert = (message, type) => {
        const wrapper = document.createElement('div')
        wrapper.innerHTML = [
            `<div class="alert alert-${type.toLowerCase()} alert-dismissible" role="alert">`,
            `   <div>${message}</div>`,
            '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
            '</div>'
        ].join('')

        message_container.append(wrapper)
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
