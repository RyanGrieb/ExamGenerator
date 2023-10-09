  // Make the current page bold in the navbar
function highlight_navbar() {
    const navbarUL = document.querySelector("#base-navbar ul")
    const page = document.URL.substring(document.URL.lastIndexOf("/"))

    for (const liElem of navbarUL.getElementsByTagName("li")) {
        aElem = liElem.getElementsByTagName("a")[0];

        if(aElem.getAttribute("href") === page){
            aElem.innerHTML = `<b>${aElem.innerHTML}</b>`
        }
    }
}

window.addEventListener("load", () => {
    highlight_navbar();
});
