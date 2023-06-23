const DatePicker = tui.DatePicker;


document.querySelectorAll('.datepicker').forEach((element) => {
    const datePicker = new DatePicker(element.querySelector('.datepicker-container'), {
        input: {
            element: element.querySelector('.datepicker-input > input'),
            format: 'dd/MM/yyyy',
        },
    });
});
