class UploadedFile {
  constructor(filename, md5_name) {
    this.filename = filename;
    this.md5_name = md5_name;
  }
}

let totalFilesUploaded = 0;
let uploaded_files = [];

function dropHandler(event) {
  event.preventDefault();

  if (event.dataTransfer.items) {
    // Use DataTransferItemList interface to access the file(s)
    [...event.dataTransfer.items].forEach((item, i) => {
      // Ensure dropped items are files
      if (item.kind === "file") {
        const file = item.getAsFile();
        //console.log(`… file[${i}].name = ${file.name}`);
        upload_file(file);
      }
    });
  }
}

function dragOverHandler(event) {
  //console.log("File(s) in drop zone");
  // Prevent default behavior (Prevent file from being opened)
  //FIXME: Modify the HTML css to show "drop here" in the upload div. Or something else..
  event.preventDefault();
}

// Format our filename such that it's able to be put inside HTML tags.
function get_formatted_file_name(fileName) {
  return fileName.replace(/[/\\?%*:|"<>]/g, "-").replaceAll(" ", "-");
}

function upload_file(file) {
  const convertButton = document.querySelector(".file-convert-btn");
  const fileList = document.querySelector(".convert-region ul");

  // Initalize our variables associated with the current file
  const formdata = new FormData();
  const fileName = file.name;
  const fileSize = file.size;
  const formattedFileName = get_formatted_file_name(fileName);

  // Check if file already exists, if so skip over it.
  for (const liElem of fileList.getElementsByTagName("li")) {
    if (liElem.textContent.includes(formattedFileName)) {
      //convertButton.removeAttribute("style");
      return;
    }
  }

  // Hide the convert button again, since were waiting on documents to upload:
  convertButton.classList.add("hidden");

  // Create an li element for each file
  const fileNameLi = document.createElement("li");
  fileNameLi.id = `upload-li-${formattedFileName}`;

  const liDiv = document.createElement("div");
  const fielNameP = document.createElement("p");
  fielNameP.innerHTML = fileName + " - 0%";

  liDiv.appendChild(fielNameP);
  fileNameLi.appendChild(liDiv);
  fileList.appendChild(fileNameLi);

  const progressBar = new ProgressBar.Line(liDiv, {
    strokeWidth: 4,
    easing: "easeInOut",
    duration: 500,
    color: "#aaa3f9",
    trailColor: "#eee",
    trailWidth: 1,
    svgStyle: { width: "100%", height: "100%" },
    text: {
      style: {
        // Text color.
        // Default: same as stroke color (options.color)
        color: "#999",
        position: "absolute",
        right: "0",
        top: "30px",
        padding: 0,
        margin: 0,
        transform: null,
      },
      autoStyleContainer: false,
    },
    from: { color: "#aaa3f9" },
    to: { color: "#ED6A5A" },
    step: (state, bar) => {
      //bar.setText(Math.round(bar.value() * 100) + " %");
    },
  });

  // Create and append our file to the XMLHttpRequest.
  const request = new XMLHttpRequest();
  request.responseType = "json";
  formdata.append("file", file);

  request.upload.addEventListener("progress", (event) => {
    if (event.loaded <= fileSize) {
      const percent = Math.round((event.loaded / fileSize) * 100);
      progressBar.animate(percent / 100);
      fielNameP.innerHTML = `${fileName} - ${percent}%`;
    }

    if (event.loaded == event.total) {
      progressBar.animate(0.9);
      fielNameP.innerHTML = `${fileName} - 99%`;
    }
  });

  request.addEventListener("readystatechange", function () {
    if (this.readyState === this.DONE) {
      const response_file_name = this.response["file_name"];
      const response_md5_name = this.response["md5_name"];
      fielNameP.innerHTML = `${fileName} - 100%`;
      progressBar.animate(1);

      totalFilesUploaded++;

      if (!uploaded_files.some((file) => file.md5_name === response_md5_name)) {
        uploaded_files.push(new UploadedFile(response_file_name, response_md5_name));
      }

      // Make the convert button visible, once all files are loaded.
      if (totalFilesUploaded >= fileList.getElementsByTagName("li").length) {
        convertButton.classList.remove("hidden");
      }
    }
  });

  request.open("post", "/");
  request.timeout = 45000;
  request.send(formdata);
}

function upload_files() {
  const fileInput = document.getElementById("file-upload");
  const convertButton = document.querySelector(".file-convert-btn");

  console.log("Uploading file...");

  // Iterate through all selected files and append them to FormData
  for (let i = 0; i < fileInput.files.length; i++) {
    const file = fileInput.files[i];
    upload_file(file);
  }
}

function convert_files() {
  const conversion_type = document.querySelector('input[name="convert_type"]:checked').value;
  const conversion_options = {};

  if (conversion_type === "test") {
    conversion_options["test"] = [];

    const checkboxes = document.querySelectorAll('.convert-test-options input[type="checkbox"]:checked');
    checkboxes.forEach((checkbox) => {
      conversion_options["test"].push(checkbox.value);
    });
  }

  for (const uploaded_file of uploaded_files) {
    let existing_cookie = false;
    let files_cookie = Cookies.get("files");
    const cookie_json = files_cookie ? JSON.parse(files_cookie) : undefined;

    if (files_cookie) {
      existing_cookie = cookie_json.some((file_json) => file_json["md5_name"] === uploaded_file.md5_name);
    }

    console.log(`${conversion_type} - ${conversion_options}`);

    // Create an object to store your data
    const file_json = {
      file_name: uploaded_file.filename,
      md5_name: uploaded_file.md5_name,
      conversion_types: [conversion_type],
      conversion_options: conversion_options,
    };

    if (!existing_cookie) {
      add_to_list_cookie("files", file_json);
    } else {
      // Append to existing cookies data
      const index = cookie_json.findIndex((item) => item.md5_name === file_json.md5_name);
      if (index !== -1) {
        const conversion_types = cookie_json[index].conversion_types;
        console.log(cookie_json);
        if (!conversion_types.includes(conversion_type)) {
          conversion_types.push(conversion_type);
        }
        cookie_json[index].conversion_options = {
          ...cookie_json[index].conversion_options,
          ...conversion_options,
        };
        Cookies.set("files", JSON.stringify(cookie_json));
      }
    }
  }

  window.location.href = "/results";
}

window.addEventListener("load", () => {
  // Get all radio elements and the convert-test-options div
  const radioButtons = document.querySelectorAll('input[name="convert_type"]');
  const convertTestOptions = document.querySelector(".convert-test-options");

  // Add event listeners to all radio buttons
  radioButtons.forEach((radioButton) => {
    radioButton.addEventListener("change", function () {
      if (this.id === "radio-test") {
        // Display convert-test-options for radio-test
        convertTestOptions.style.display = this.checked ? "block" : "none";
      } else {
        // Hide convert-test-options for other radio buttons
        convertTestOptions.style.display = "none";
      }
    });
  });
});
