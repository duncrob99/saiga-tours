document.querySelectorAll('.separator path').forEach(sep => {
    sep.style.transform = `translateX(${-Math.random()*50}px)`;
});