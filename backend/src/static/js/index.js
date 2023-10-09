Cookies.remove("files");
let totalFilesUploaded = 0;

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
  convertButton.style.display = "none";

  // Create an li element for each file
  const fileNameLi = document.createElement("li");
  fileNameLi.id = `upload-li-${formattedFileName}`;
  fileNameLi.textContent = fileName + " - 0%";
  fileList.appendChild(fileNameLi);

  // Create and append our file to the XMLHttpRequest.
  const request = new XMLHttpRequest();
  request.responseType = "json";
  formdata.append("file", file);

  request.upload.addEventListener("progress", (event) => {
    if (event.loaded <= fileSize) {
      const percent = Math.round((event.loaded / fileSize) * 100);
      fileNameLi.textContent = `${fileName} - ${percent}%`;
    }

    if (event.loaded == event.total) {
      fileNameLi.textContent = `${fileName} - 99%`;
    }
  });

  request.addEventListener("readystatechange", function () {
    if (this.readyState === this.DONE) {
      const response_file_name = this.response["file_name"];
      const response_md5_name = this.response["md5_name"];
      fileNameLi.textContent = `${fileName} - 100%`;

      // Create an object to store your data
      const file_json = {
        file_name: response_file_name,
        md5_name: response_md5_name,
      };
      add_to_list_cookie("files", file_json)

      totalFilesUploaded++;
      //console.log(`${totalFilesUploaded} - ${fileList.getElementsByTagName("li").length}`)
      // Make the convert button visible, once all files are loaded.
      if (totalFilesUploaded >= fileList.getElementsByTagName("li").length) {
        convertButton.removeAttribute("style");
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
  window.location.href = "/results";
}
