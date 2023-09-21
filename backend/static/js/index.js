window.addEventListener("load", () => {

// Get the file input element
const fileInput = document.getElementById("file-upload");

// Add an event listener to the file input field
fileInput.addEventListener("change", () => {
  // Check if files were selected
  if (fileInput.files.length > 0) {
    // TODO: Change the .upload-area <div> to display list of uploaded files.
    
    // Iterate through the selected files and display their names
    for (let i = 0; i < fileInput.files.length; i++) {
      console.log("Selected File Name:", fileInput.files[i].name);
    }
  }
});

});
