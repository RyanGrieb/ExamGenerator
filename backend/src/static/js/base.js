// Make the current page bold in the navbar
function highlight_navbar() {
  const navbarUL = document.querySelector("#base-navbar ul");
  const page = document.URL.substring(document.URL.lastIndexOf("/"));

  for (const liElem of navbarUL.getElementsByTagName("li")) {
    aElem = liElem.getElementsByTagName("a")[0];

    if (aElem.getAttribute("href") === page) {
      aElem.innerHTML = `<b>${aElem.innerHTML}</b>`;
    }
  }
}

function add_to_list_cookie(cookie_name, list_object) {
  const files_cookie = Cookies.get(cookie_name);
  if (files_cookie === undefined) {
    Cookies.set(cookie_name, JSON.stringify([list_object]));
  } else {
    // get list from 'files' cookie, and append to it.
    const files = JSON.parse(files_cookie);
    files.push(list_object);
    Cookies.set(cookie_name, JSON.stringify(files));
    //console.log("NEW COOKIES:")
    //console.log(Cookies.get("files"))
  }
}

window.addEventListener("load", () => {
  highlight_navbar();
});
