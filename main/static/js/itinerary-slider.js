let slideIndex = 1;

// Next/previous controls
function plusSlides(n) {
    showSlides(slideIndex += n);
}

// Thumbnail image controls
function currentSlide(n, shouldScrollToTop) {
    showSlides(slideIndex = n, shouldScrollToTop);
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

function showSlides(n, shouldScrollToTop, dontScroll) {
    let i;
    let slides = document.getElementsByClassName("mySlides");
    let dots = document.getElementsByClassName("dot");
    if (slides.length > 0) {
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

        if (!dontScroll) {
            scrollToView(slides[slideIndex - 1], shouldScrollToTop);
        }
    }
}

function scrollToView(elem, shouldScrollToTop, margin) {
    if (margin === undefined) {
        margin = 20;
    }

    function scrollTo(x, y) {
        document.body.scroll({left: x, top: y, behavior: 'smooth'});
    }

    let bbox = elem.getBoundingClientRect();
    let windowBox = {
        top: document.body.scrollTop,
        bottom: document.body.scrollTop + window.innerHeight,
        left: document.body.scrollLeft,
        right: document.body.scrollLeft + window.innerWidth,
        navbar: parseInt(getComputedStyle(document.documentElement).getPropertyValue('--navbar-height'))
    }

    if (bbox.top <= windowBox.navbar + margin && bbox.bottom <= window.innerHeight - margin) {
        if (bbox.height < window.innerHeight ? !shouldScrollToTop : shouldScrollToTop) {
            scrollTo(windowBox.left, windowBox.top + bbox.top - windowBox.navbar - margin);
        } else {
            scrollTo(windowBox.left, windowBox.top + (bbox.top + bbox.height - window.innerHeight + margin));
        }
    } else if (bbox.top + bbox.height >= window.innerHeight - margin && bbox.top >= windowBox.navbar + margin) {
        if (bbox.height > window.innerHeight) {
            scrollTo(windowBox.left, windowBox.top + bbox.top - windowBox.navbar - margin);
        } else {
            scrollTo(windowBox.left, windowBox.top + (bbox.top + bbox.height - window.innerHeight + margin));
        }
    }
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

function minimiseSlides() {
    let slides = document.getElementsByClassName('mySlides');
    let max_height = window.innerHeight * 0.8;
    console.log('minimising')
    for (let i = 0; i < slides.length; i++) {
        let slide = slides[i];
        let style = getComputedStyle(slide);
        let height = parseInt(style.height);
        if (height > max_height) {
            slide.classList.add('compact');
        }
    }
}

function expandSlide(day) {
    let slide = document.getElementById(`day-${day}`);
    slide.classList.remove('compact');
    slide.classList.add('expanded');
    setVerticalHeight();
    scrollToView(slide);
}

function contractSlide(day) {
    let slide = document.getElementById(`day-${day}`);
    slide.classList.add('compact');
    slide.classList.remove('expanded');
    setVerticalHeight();
    scrollToView(slide);
}

window.addEventListener('resize', setVerticalHeight);
window.addEventListener('load', () => {
    minimiseSlides();
    setVerticalHeight();
});
document.querySelectorAll('.dot').forEach((el, index) => {
    el.addEventListener('click', () => {
        currentSlide(index + 1);
    })
})
document.querySelectorAll('.mySlides').forEach(el => {
    el.addEventListener('input', setVerticalHeight);
});

showSlides(slideIndex, false, true);
