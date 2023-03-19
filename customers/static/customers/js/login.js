(function() {
  // Activate password visibility toggles
  let toggles = document.querySelectorAll('.password-visibility');
  toggles.forEach(toggle => {
    let field = toggle.closest('.field');
    let input = field.querySelector('input');
    toggle.addEventListener('click', () => {
      if (input.type == 'password') {
        input.type = 'text';
        field.classList.add('show-password');
      } else {
        input.type = 'password';
        field.classList.remove('show-password');
      }
    });
  });

  function preload_image(src) {
    let img = new Image();
    img.src = src;
  }

  preload_image('/static/images/eye.svg');
  preload_image('/static/images/eye-slash.svg');
})();
