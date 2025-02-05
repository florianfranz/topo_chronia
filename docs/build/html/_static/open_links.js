document.addEventListener("DOMContentLoaded", function() {
    let links = document.querySelectorAll("a.external");
    links.forEach(link => link.setAttribute("target", "_blank"));
});
