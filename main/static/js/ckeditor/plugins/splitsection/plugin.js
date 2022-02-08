CKEDITOR.plugins.add('splitsection', {
    requires: 'widget',
    icons: 'splitsection',
    init: function (editor) {
        editor.widgets.add('splitsection', {
            button: 'Create a split section',

            template:
                '<div class="split-section">' +
                '<div class="row">' +
                '<div class="left-col col-md-6 d-flex justify-content-center flex-column py-5"></div>' +
                '<div class="right-col col-md-6 d-flex justify-content-center flex-column py-5"></div>' +
                '</div>' +
                '</div>',

            editables: {
                left: {
                    selector: '.left-col'
                },
                right: {
                    selector: '.right-col'
                }
            },

            allowedContent: 'div(!row); div(!left-col,!col-md-6,!d-flex,justify-content-center,align-content-start,align-content-end,!flex-column,!py-5); p; svg[*]{*}(*); path[d]',

            upcast: function (element) {
                return element.name === 'div' && element.hasClass('split-section');
            },

            dialog: 'splitsection',

            init: function () {
                let left_col_classes = Array.from(this.element.$.querySelector('div.row div.left-col').classList);
                let width = parseInt(left_col_classes.filter(e => /^col-md-/g.test(e))[0].slice(-1));
                if (width)
                    this.setData('width', width);

                if (left_col_classes.includes('justify-content-start'))
                    this.setData('align', 'start');
                if (left_col_classes.includes('justify-content-center'))
                    this.setData('align', 'center');
                if (left_col_classes.includes('justify-content-end'))
                    this.setData('align', 'end');

                if (this.element.$.querySelector('div.row').classList.contains('wide-bg')) {
                    this.setData('background', getComputedStyle(this.element.$.querySelector('div.row')).getPropertyValue('--background'));
                }
            },

            data: function () {
                let cols = this.element.$.querySelectorAll('div.row div.flex-column');
                cols.forEach(col => {
                    col.classList.remove('justify-content-start');
                    col.classList.remove('justify-content-center');
                    col.classList.remove('justify-content-end');
                    Array.from(col.classList).filter(el => el.startsWith('col-md-')).forEach(cls => col.classList.remove(cls));
                });

                if (this.data.width === '' || parseInt(this.data.width) % 1 !== 0 || parseInt(this.data.width) > 12 || isNaN(parseInt(this.data.width))) {
                    cols.forEach(col => {
                        col.classList.add('col-md-6');
                    })
                } else {
                    cols[0].classList.add(`col-md-${parseInt(this.data.width)}`);
                    cols[1].classList.add(`col-md-${12 - parseInt(this.data.width)}`);
                }

                if (this.data.align) {
                    cols.forEach(col => {
                        col.classList.add(`justify-content-${this.data.align}`);
                    })
                }

                if (this.element.$.firstChild.tagName === 'svg') {
                    this.element.$.firstChild.remove();
                }
                if (this.element.$.lastChild.tagName === 'svg') {
                    this.element.$.lastChild.remove();
                }

                if (this.data.background) {
                    let pre_svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    pre_svg.classList.add('pre-separator');
                    pre_svg.classList.add('separator');
                    pre_svg.setAttribute('preserveaspectratio', "xMaxYMax meet");
                    this.element.$.insertAdjacentElement("afterbegin", pre_svg);
                    let svg = SVG(pre_svg).viewbox('0 0 100 2').fill(this.data.background);
                    svg.path('M 0 1 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 l 0 -1 L 0 0 z');

                    let post_svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    post_svg.classList.add('post-separator');
                    post_svg.classList.add('separator');
                    post_svg.setAttribute('preserveaspectratio', "xMaxYMax meet");
                    this.element.$.insertAdjacentElement('beforeend', post_svg);
                    svg = SVG(post_svg).viewbox('0 0 100 2').fill(this.data.background);
                    svg.path('M 0 1 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 c 5 3 5 -3 10 0 l 0 -1 L 0 0 z');

                    this.element.$.querySelector('div.row').classList.add('wide-bg');
                    this.element.$.querySelector('div.row').style.setProperty('--background', this.data.background);
                } else {
                    this.element.$.querySelector('div.row').classList.remove('wide-bg');
                }
            }
        })

        CKEDITOR.dialog.add('splitsection', `${this.path}/dialogs/splitsection.js`);
    }
})