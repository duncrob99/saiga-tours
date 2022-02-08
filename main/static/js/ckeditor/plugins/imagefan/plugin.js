CKEDITOR.plugins.add('imagefan', {
    requires: 'widget',
    icons: 'imagefan',
    init: function (editor) {
        let placeholder_src = '/static/images/blank-image-placeholder.png/';

        editor.widgets.add('imagefan', {
            button: 'Create an image fan',

            template:
                '<div class="image-fan">' +
                `<div class="above-img"><img src="${placeholder_src}" style="width: 400px; height: 250px;" /></div>` +
                `<div class="below-img"><img src="${placeholder_src}" style="width: 400px; height: 250px;" /></div>` +
                '</div>',

            editables: {
                above: {
                    selector: '.above-img',
                    allowedContent: 'img[alt,src]{width,height}'
                },
                below: {
                    selector: '.below-img',
                    allowedContent: 'img[alt,src]{width,height}'
                }
            },

            allowedContent: 'div(!image-fan); div(!above-img); div(!below-img); img[alt,src]{width,height}',

            upcast: function (element) {
                return element.name === 'div' && element.hasClass('image-fan');
            }
        })
    }
})