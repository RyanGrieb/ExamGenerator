Cookies.remove("files")

// Format our filename such that it's able to be put inside HTML tags.
function get_formatted_file_name(fileName) {
  return fileName.replace(/[/\\?%*:|"<>]/g, "-").replaceAll(" ", "-");
}

function upload_file() {
  const fileList = document.querySelector(".convert-region ul");
  const fileInput = document.getElementById("file-upload");
  const convertButton = document.querySelector(".file-convert-btn");
  let filesUploaded = 0;

  // Hide the convert button again, since were waiting on documents to upload:
  convertButton.style.display = "none";

  console.log("Uploading file...");

  // Iterate through all selected files and append them to FormData
  for (let i = 0; i < fileInput.files.length; i++) {
    // Initalize our variables associated with the current file
    const formdata = new FormData();
    const file = fileInput.files[i];
    const fileName = file.name;
    const fileSize = file.size;
    const formattedFileName = get_formatted_file_name(fileName);

    // Create an li element for each file
    const fileNameLi = document.createElement("li");
    fileNameLi.id = `upload-li-${formattedFileName}`;
    fileNameLi.textContent = fileName + " - 0%";
    fileList.appendChild(fileNameLi);

    // Create and append our file to the XMLHttpRequest.
    const request = new XMLHttpRequest();
    request.responseType = "json"
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
        console.log(response_file_name)
        const file_json = {
          file_name: response_file_name,
          md5_name: response_md5_name,
        };


        const files_cookie = Cookies.get("files")
        if(files_cookie === undefined){
          Cookies.set("files", JSON.stringify([file_json]))
        }else{
          // get list from 'files' cookie
          const files = JSON.parse(files_cookie)
          files.push(file_json)
          Cookies.set("files", JSON.stringify(files))
          //console.log("NEW COOKIES:")
          //console.log(Cookies.get("files"))
        }

        // Make the convert button visible, once all files are loaded.
        filesUploaded++;
        if (filesUploaded >= fileInput.files.length) {
          convertButton.removeAttribute("style");
        }
      }
    });

    request.open("post", "/");
    request.timeout = 45000;
    request.send(formdata);
  }
}

function convert_files() {
  console.log("?????????????")
  window.location.href = "/results";
}
