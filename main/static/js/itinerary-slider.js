let slideIndex = 1;
showSlides(slideIndex);

// Next/previous controls
function plusSlides(n) {
    showSlides(slideIndex += n);
}

// Thumbnail image controls
function currentSlide(n) {
    showSlides(slideIndex = n);
}

function get_max_height() {
    let max_height = 0;
    let slides = document.querySelectorAll('.mySlides');
    slides.forEach(function (slide) {
        slide.style.height = 'min-content';
        if (slide.getBoundingClientRect().height > max_height) {
            max_height = slide.getBoundingClientRect().height;
        }
    })
    return max_height
}

function showSlides(n) {
    let i;
    let slides = document.getElementsByClassName("mySlides");
    let dots = document.getElementsByClassName("dot");
    if (n > slides.length) {
        slideIndex = 1;
    } else if (n < 1) {
        slideIndex = slides.length;
    } else {
        slideIndex = n;
    }
    for (i = 0; i < slides.length; i++) {
        slides[i].style.left = ((i - slideIndex + 1) * 85 + 10) + "%";
    }
    for (i = 0; i < dots.length; i++) {
        dots[i].className = dots[i].className.replace(" active", "");
    }
    slides[slideIndex - 1].style.display = "block";
    slides[slideIndex - 1].classList.add('active');
    dots[slideIndex - 1].className += " active";
}

function setVerticalHeight() {
    let slides = document.getElementsByClassName('mySlides');
    let tot_height = 0;
    let max_height = get_max_height();
    for (let i = 0; i < slides.length; i++) {
        slides[i].style.top = -1 * tot_height + "px";
        slides[i].style.height = max_height + "px";
        tot_height += slides[i].getBoundingClientRect().height;
    }
    document.querySelector('.slideshow-container').style.height = max_height + 15 + 'px';
    document.querySelector('.slides').style.height = max_height + 15 + 'px';
}

window.addEventListener('resize', setVerticalHeight);
window.addEventListener('load', setVerticalHeight);
document.querySelectorAll('.dot').forEach((el, index) => {
    el.addEventListener('click', () => {
        currentSlide(index + 1);
    })
})