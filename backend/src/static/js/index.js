window.addEventListener("load", () => {
  // Get the file input element
  const fileInput = document.getElementById("file-upload");

  // Add an event listener to the file input field
  fileInput.addEventListener("change", () => {
    // Check if files were selected
    if (fileInput.files.length > 0) {
      // TODO: Change the .upload-area <div> to display list of uploaded files.

      // Iterate through the selected files and display their names
      const fileList = document.querySelector(".convert-region ul");

      for (let i = 0; i < fileInput.files.length; i++) {
        const fileName = fileInput.files[i].name;
        console.log("Selected File Name:", fileName);
        const fileNameLi = document.createElement("li");
        fileNameLi.textContent = fileName;
        fileList.appendChild(fileNameLi);
      }

      // Make the convert button visible
      const convertButton = document.querySelector(".file-convert-btn");
      convertButton.removeAttribute("style");

    }
  });
});
