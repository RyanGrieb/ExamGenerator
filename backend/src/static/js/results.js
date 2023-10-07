// Dictionary that associates the task_id with the filename
task_id_filename_dict = {};
task_id_md5_name_dict = {};

function set_file_status(filename, status) {
  p_element = document.querySelector(`#${filename} p`);
  p_element.textContent = status;
}

function add_qa_set_to_page(
  filename,
  md5_name,
  qa_set,
  final_generation = false
) {
  const qaSetDiv = document.querySelector(".qa-set");
  set_file_status(filename, "Finished.");
  
  document.querySelector(".status-text").innerHTML = "Generated Q&As:";

  if (final_generation) {
    document.querySelector(".converting-div").remove();
  }

  // FIXME: JUST PUT A \n before each Q: element. (except the 1st one)
  qa_set.split("\n").forEach((line, index) => {
    const paragraph = document.createElement("p");

    // Add newline space between each Q&A set
    if (index != 0 && index % 2 == 0) {
      //qaSetDiv.appendChild(document.createElement("br"))
    }

    paragraph.textContent = line;
    qaSetDiv.appendChild(paragraph);
  });
}

// Function to periodically check task status
async function checkTaskStatus(task_id, callback) {
  // Define your logic to check task status here
  // You can use setInterval or any other mechanism to check status periodically
  // Example:
  const interval = setInterval(async () => {
    // Send a GET request to check the task status using the task_id
    const statusResponse = await fetch(`/task_status/${task_id}`, {
      method: "GET",
    });

    if (statusResponse.ok) {
      const statusData = await statusResponse.json();
      // Check if the task is complete
      if (statusData.status === "completed") {
        clearInterval(interval); // Stop checking once it's complete
        console.log(`Task with ID ${task_id} is complete.`);
        callback(
          task_id,
          task_id_filename_dict[task_id],
          task_id_md5_name_dict[task_id]
        );
        delete task_id_filename_dict[task_id];
        delete task_id_md5_name_dict[task_id];
        // You can perform further actions here
      } else if (statusData.status === "processing") {
        console.log(`Task with ID ${task_id} is still processing.`);
        // Handle ongoing processing if needed
      } else {
        console.error(
          `Unknown status for task with ID ${task_id}: ${statusData.status}`
        );
        clearInterval(interval); // Stop checking on error
      }
    } else {
      console.error(
        `Error checking task status for task ID ${task_id}: ${statusResponse.status}`
      );
      clearInterval(interval); // Stop checking on error
    }
  }, 5000); // Check every 5 seconds (adjust this as needed)
}

async function get_json2questions(filename, md5_name) {
  // Send a GET request to the server and wait for the response
  console.log("Fetch generated q&a set from server:");
  const formData = new FormData();
  formData.append("filename", filename);
  formData.append("md5_name", md5_name);

  const response = await fetch(`/pdf-qa/${md5_name}`, {
    method: "GET",
  });

  if (response.ok) {
    // Print the plaintext string here:
    const qa_set = await response.text(); // Extract the plaintext content
    add_qa_set_to_page(filename, md5_name, qa_set);
  }
}

async function post_json2questions(filename, md5_name) {
  try {
    // Create a FormData object to send data with the POST request
    const formData = new FormData();
    formData.append("filename", filename);
    formData.append("md5_name", md5_name);

    // Send a POST request to the server and wait for the response
    const response = await fetch("/json2questions", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const responseData = await response.json();
      const task_id = responseData.task_id;

      task_id_filename_dict[task_id] = filename;
      task_id_md5_name_dict[task_id] = md5_name;

      // Send a task_status get request every 5-10 seconds until complete. (Timeout at 5 mins?)
      checkTaskStatus(task_id, (task_id, filename, md5_name) => {
        console.log(
          "JSON2Questions callback done: " + task_id + " | " + filename
        );
        // Send a GET request for the questions generated server-side
        get_json2questions(filename, md5_name);
      });
    } else {
      // Handle network or other errors here
      console.error(`Error sending ${filename} to the server: ${error}`);
    }
  } catch (error) {
    // Handle network or other errors here
    console.error(`Error sending ${filename} to the server: ${error}`);
  }
}

async function post_pdf2json(filename, md5_name) {
  try {
    // Create a FormData object to send data with the POST request
    const formData = new FormData();
    formData.append("filename", filename);
    formData.append("md5_name", md5_name);

    // Send a POST request to the server and wait for the response
    const response = await fetch("/pdf2json", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const responseData = await response.json();
      const task_id = responseData.task_id;

      task_id_filename_dict[task_id] = filename;
      task_id_md5_name_dict[task_id] = md5_name;

      // Send a task_status get request every 5-10 seconds until complete. (Timeout at 5 mins?)
      checkTaskStatus(task_id, (task_id, filename, md5_name) => {
        console.log("pfd2json callback done: " + task_id + " | " + filename);
        set_file_status(filename, "Generating questions and answers...");
        post_json2questions(filename, md5_name);
      });
      // TOOD: Handle the completion response for checkTaskStatus here....
    } else {
      // Handle errors here
      console.error(`Error sending ${filename} to the server.`);
    }
  } catch (error) {
    // Handle network or other errors here
    console.error(`Error sending ${filename} to the server: ${error}`);
  }
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

    post_pdf2json(filename, md5_name);
  }
});
