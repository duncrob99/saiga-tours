(function () {
    for (let instanceName in CKEDITOR.instances) {
        customiseCK(CKEDITOR.instances[name]);
    }

    CKEDITOR.disableAutoInline = true;

    CKEDITOR.stylesSet.add('styles', [
        {name: 'Above', element: 'img', attributes: {'class': 'above-img'}},
        {name: 'Below', element: 'img', attributes: {'class': 'below-img'}},
        {name: 'Bordered', element: 'img', attributes: {'class': 'bordered'}},
        {name: 'Shadow', element: 'img', attributes: {'class': 'shadow'}},
        {name: 'Saiga Border', element: 'img', attributes: {'class': 'saiga-border'}},
        {name: 'Angle Right', element: 'img', attributes: {'class': 'angle-right'}},
        {name: 'Angle Left', element: 'img', attributes: {'class': 'angle-left'}},
        {name: 'Underlined Title', element: 'h3', attributes: {'class': 'underlined-title'}},
        {name: 'Faded', element: 'p', attributes: {'class': 'faded'}},
        {name: 'Text block', element: 'p', attributes: {'class': 'block'}},
        {name: 'Styled table', element: 'table', attributes: {'class': 'styled-table'}}
    ])
})();

function createEditor(id, config) {
    let default_config = {
        extraPlugins: 'sourcedialog, uploadimage, sharedspace, splitsection, imagefan, tableresize',
        removePlugins: 'exportpdf',
        filebrowserImageBrowseUrl: '/ckeditor/browse/?csrfmiddlewaretoken=' + csrf_token,
        filebrowserImageUploadUrl: "/ckeditor/upload/?csrfmiddlewaretoken=" + csrf_token,
        image: {
            styles: {
                options: [{
                    name: 'cool',
                    title: 'Cool image',
                    className: 'cool-img',
                    modelElements: ['imageInline']
                }]
            }
        },
        stylesSet: 'styles',
        sharedSpaces: {
            top: 'editor-toolbar'
        }
    }
    config = {
        ...default_config,
        ...config
    }

    let editor = CKEDITOR.inline(id, config);
    customiseCK(editor);

    return editor;
}

function customiseCK(instance) {
    // instance.config.allowedContent = true;
    // instance.ui.addToolbarGroup('layout', 'insert');
    //
    // instance.addCommand("split", {
    //     exec: function (edt) {
    //         edt.insertHtml(`
    //             <div class="row">
    //                 <div class="col-md-6 d-flex justify-content-center flex-column py-5"><p>left</p></div>
    //                 <div class="col-md-6 d-flex justify-content-center flex-column py-5"><p>right</p></div>
    //             </div>
    //         `);
    //     }
    // });
    // instance.ui.addButton('split', {
    //     label: "split section",
    //     command: "split",
    //     toolbar: "layout",
    //     icon: ckeditor_icon_urls.split
    // });
    //
    // instance.addCommand('image_fan', {
    //     exec: function (edt) {
    //         edt.insertHtml(`<div><div class='image-fan'><img class="above-img" style="width: 300px; height: 200px;"/><img class="below-img" style="width: 300px; height: 200px;"/></div></div>`);
    //     }
    // });
    // instance.ui.addButton('image_fan', {
    //     label: 'image fan',
    //     command: 'image_fan',
    //     toolbar: 'layout',
    //     icon: ckeditor_icon_urls.image_fan
    // });
    if (instance !== undefined) {
        instance.on('instanceReady', () => {
            document.querySelectorAll('.cke_combo_button').forEach(fixScroll);
            document.querySelectorAll('.cke_button_expandable').forEach(fixScroll);

            function fixScroll(dropdown) {
                dropdown.addEventListener('click', function () {
                    let scroll_pos = document.body.scrollTop;

                    function resetScroll() {
                        document.body.scrollTop = scroll_pos;
                        document.body.removeEventListener('scroll', resetScroll);
                    }

                    document.body.addEventListener('scroll', resetScroll);
                });
            }
        });
    }
}