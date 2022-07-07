CKEDITOR.dialog.add('splitsection', function (editor) {
    return {
        title: 'Edit Split Section',
        minWidth: 200,
        minHeight: 100,
        contents: [
            {
                id: 'info',
                elements: [
                    {
                        id: 'align',
                        type: 'select',
                        label: 'Alignment',
                        items: [
                            [editor.lang.common.notSet, ''],
                            [editor.lang.common.alignTop, 'start'],
                            [editor.lang.common.alignMiddle, 'center'],
                            [editor.lang.common.alignBottom, 'end']
                        ],
                        setup: function (widget) {
                            this.setValue(widget.data.align);
                        },
                        commit: function (widget) {
                            widget.setData('align', this.getValue());
                        }
                    },
                    {
                        id: 'height',
                        type: 'text',
                        label: 'Min Height',
                        width: '50px',
                        setup: function (widget) {
                            this.setValue(widget.data.height);
                        },
                        commit: function (widget) {
                            let val = parseInt(this.getValue());
                            if (isNaN(val)) {
                                widget.setData('height', '');
                            } else {
                                widget.setData('height', `${Math.round(val)}`)
                            }
                        }
                    },
                    {
                        id: 'width',
                        type: 'text',
                        label: 'Left Width',
                        width: '50px',
                        setup: function (widget) {
                            this.setValue(widget.data.width);
                        },
                        commit: function (widget) {
                            let val = parseInt(this.getValue());
                            if (isNaN(val)) {
                                widget.setData('width', '');
                            } else if (val < 1) {
                                widget.setData('width', '1');
                            } else if (val > 12) {
                                widget.setData('width', '12');
                            } else {
                                widget.setData('width', `${Math.round(val)}`)
                            }
                        }
                    },
                    {
                        id: 'background',
                        type: 'text',
                        label: 'Background Colour',
                        width: '100px',
                        setup: function (widget) {
                            this.getInputElement().setAttribute('data-jscolor', '{required:false}');
                            jscolor.install();
                            this.setValue(widget.data.background);
                        },
                        commit: function (widget) {
                            let val;

                            // Append leading # if it doesn't exist
                            if (this.getValue()[0] === '#') {
                                val = this.getValue();
                            } else {
                                val = `#${this.getValue()}`;
                            }

                            // Default to blank if invalid colour
                            if (!/^#([0-9a-f]{3}){1,2}$/i.test(val)) {
                                val = '';
                            }

                            widget.setData('background', val);
                        }
                    },
                    {
                        id: 'link',
                        type: 'text',
                        label: 'link',
                        width: '300px',
                        setup: function (widget) {
                            this.setValue(widget.data.link);
                        },
                        commit: function (widget) {
                            widget.setData('link', this.getValue());
                        }
                    },
                    {
                        id: 'id',
                        type: 'text',
                        label: 'id',
                        width: '300px',
                        setup: function (widget) {
                            this.setValue(widget.data.id);
                        },
                        commit: function (widget) {
                            widget.setData('id', this.getValue());
                        }
                    }
                ]
            }
        ]
    }
});