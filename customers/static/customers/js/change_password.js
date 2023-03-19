(function() {
  let old_password_input = document.querySelector('#id_old_password');
  let new_password1_input = document.querySelector('#id_new_password1');
  let new_password2_input = document.querySelector('#id_new_password2');
  let strength_indicator = document.querySelector('.strength-indicator');
  let password_suggestions = document.querySelector('.password-suggestions');
  let email_input = document.querySelector('#email');

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function validate_password() {

    let password_strength = zxcvbn(new_password1_input.value, [email_input.value]);

    let score = clamp(password_strength.guesses_log10 * 10, 0, 100);

    strength_indicator.style.setProperty('--strength', score);
    password_suggestions.innerHTML = '';

    if (password_strength.feedback.warning != '') {
      let el = document.createElement('li');
      el.innerText = password_strength.feedback.warning;
      el.classList.add('warning');
      password_suggestions.appendChild(el);
    }

    let el = document.createElement('li');
    el.innerText = `Crackable in ${password_strength.crack_times_display.offline_slow_hashing_1e4_per_second}`;
    password_suggestions.appendChild(el);
    
    password_strength.feedback.suggestions.forEach(suggestion => {
      let el = document.createElement('li');
      el.innerText = suggestion;
      password_suggestions.appendChild(el);
    });

    if (new_password1_input.value.length == 0) {
      new_password1_input.closest('.field').classList.remove('has-suggestions');
    } else {
      new_password1_input.closest('.field').classList.add('has-suggestions');
    }

    return score;
  }

  function validate_equality() {
    if (new_password1_input.value != new_password2_input.value) {
      new_password2_input.setCustomValidity("Passwords don't match");
    } else {
      new_password2_input.setCustomValidity('');
    }
  }

  function validate_signup() {
    console.log('validating');
    if (validate_password() >= 75 && new_password1_input.value == new_password2_input.value && old_password_input.value.length > 0) {
      document.querySelector('#submit').disabled = false;
    } else {
      document.querySelector('#submit').disabled = true;
    }
  }

  old_password_input.addEventListener('input', validate_signup);
  new_password1_input.addEventListener('input', validate_signup);
  new_password1_input.addEventListener('input', () => {
    let password_parent_field = new_password1_input.closest('.field');
    if (new_password1_input.value.length > 0) {
      password_parent_field.classList.remove('empty_input');
    } else {
      password_parent_field.classList.add('empty_input');
    }
  });
  new_password2_input.addEventListener('input', validate_signup);

  document.body.scrollTo(0, 0);

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
