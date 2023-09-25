function set_file_status(filename, status) {
  document.getElementById(filename).innerText = filename + " - " + status;
}

function post_text2questions(filename, md5_name){
    
}

function post_pdf2text(filename, md5_name){
    // Create a FormData object to send data with the POST request
    const formData = new FormData();
    formData.append("filename", filename);
    formData.append("md5_name", md5_name);

    // Send a POST request to the server
    fetch("/pdf2text", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.ok) {
          // Handle the successful response here
          console.log(
            `Successfully converted ${filename} to text, server-side.`
          );
          set_file_status(filename, "Generating questions...");
        } else {
          // Handle errors here
          console.error(`Error sending ${filename} to the server.`);
        }
      })
      .catch((error) => {
        // Handle network or other errors here
        console.error(`Error sending ${filename} to the server: ${error}`);
      });
}

window.addEventListener("load", () => {
  // Test output to see if our variables got initalized (they usually are)
  console.log(file_names);
  console.log(md5_names);

  // Iterate through all files string array, send a post request to our server at /pdf-to-text
  // Include the filename & md5_name of the file
  // Iterate through the file names and send a POST request for each file
  for (let i = 0; i < file_names.length; i++) {
    const filename = file_names[i];
    const md5_name = md5_names[i];

    post_pdf2text(filename,md5_name)
  }
});
