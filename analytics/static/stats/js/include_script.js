(function () {
    let cookie = document.cookie;
    // Transfer user id from cookie to localStorage if it exists
    if (cookie.indexOf('userID=') > -1) {
        console.log("Migrating cookie to local storage");
        let user_id = cookie.split('userID=')[1].split(';')[0];
        localStorage.setItem('user_id', user_id);
    }
    document.cookie = 'userID=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    let userId = localStorage.getItem('user_id');
    let sessionId = localStorage.getItem('session_id');
    let reportInterval = 5000;

    let time_visible = 0;
    let became_visible;
    Visibility.onVisible(() => {
        became_visible = new Date().getTime();
    });

    $.ajax({
        type: "POST",
        url: django_urls.view,
        data: {
            'path': window.location.pathname,
            'interval': reportInterval,
            'referer': "{{ request.META.HTTP_REFERER }}",
            'user_id': userId,
            'session_id': sessionId,
        },
        success: data => {
            localStorage.setItem('user_id', data.user_id);
            localStorage.setItem('session_id', data.session_id);
            userId = data.user_id;
            sessionId = data.session_id;
            console.log('success data: ', data);

            Visibility.change((ev, state) => {
                if (state === 'visible') {
                    became_visible = new Date().getTime();
                } else {
                    time_visible += new Date().getTime() - became_visible;
                }
            })

            if (!data.accepted_cookies) {
                document.querySelector('#cookie-banner').classList.remove('hidden');
            }

            if (data.show_subscription) {
                let sub_modal = new bootstrap.Modal(document.getElementById('subscription-request'));
                sub_modal.show();
            }

            let view_id = data.pageview;

            setInterval(() => {
                if (!Visibility.hidden()) {
                    time_visible += new Date().getTime() - became_visible;
                    became_visible = new Date().getTime();
                }
                $.ajax({
                    type: "POST",
                    url: django_urls.heartbeat,
                    data: {
                        'path': window.location.pathname,
                        'interval': reportInterval,
                        'time_visible': time_visible,
                        'pageview': view_id,
                        'user_id': userId
                    },
                    success: function (data) {
                        if (data.success) {
                            time_visible = 0;
                        }
                    },
                    error: () => {
                        console.log("You're not being tracked anymore");
                    }
                })
            }, reportInterval)

            window.addEventListener('beforeunload', () => {
                if (!Visibility.hidden()) {
                    time_visible += new Date().getTime() - became_visible;
                    became_visible = new Date().getTime();
                }
                $.ajax({
                    type: "POST",
                    url: django_urls.close,
                    data: {
                        'path': window.location.pathname,
                        'time_visible': time_visible,
                        'pageview': view_id,
                        'user_id': userId
                    },
                    success: function () {
                        console.log("You're still being tracked");
                    },
                    error: () => {
                        console.log("You're not being tracked anymore");
                    }
                })
            })

            let last_pos;
            let distance_trigger = 50;
            window.addEventListener('mousemove', (ev) => {
                if (last_pos === undefined || Math.sqrt((last_pos.x - ev.x) ** 2 + (last_pos.y - ev.y) ** 2) > distance_trigger) {
                    last_pos = {x: ev.x, y: ev.y};
                    if (ev.x && ev.y) {
                        $.ajax({
                            type: "POST",
                            url: django_urls.mouse_action,
                            data: {
                                'path': window.location.pathname,
                                'x': ev.x,
                                'y': ev.y,
                                'pageview': view_id,
                                'user_id': userId
                            },
                            success: function () {
                            },
                            error: () => {
                            }
                        })
                    }
                }
            })

            window.addEventListener('mousedown', (ev) => {
                if (ev.x && ev.y) {
                    $.ajax({
                        type: "POST",
                        url: django_urls.mouse_action,
                        data: {
                            'path': window.location.pathname,
                            'x': ev.x,
                            'y': ev.y,
                            'clicked': ev.button,
                            'pageview': view_id,
                            'user_id': userId
                        },
                        success: function () {
                        },
                        error: () => {
                        }
                    })
                }
            })
        },
        error: () => {
            console.log("You're not being tracked");
        }
    })

})();
