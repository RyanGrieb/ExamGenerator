// Dictionary that associates the task_id with the filename
task_id_filename_dict = {};
task_id_md5_name_dict = {};

function set_file_status(filename, md5_name, status) {
  p_element = document.querySelector(`#converting-status-${md5_name}`);
  p_element.textContent = status;

  // Remove loading element if status is 'Finshed.'
  if (status === "Finished.") {
    loading_element = document.querySelector(`#loader-${md5_name}`);
    loading_element.classList.remove("loader");
    loading_element.classList.add("checkmark-done");

    qa_set_title = document.querySelector(`#qa-set-title-${md5_name}`);
    qa_set_title.innerHTML = `<b>${filename}</b> - Generated Questions & Answers:`;
  }
}

function add_qa_set_to_page(
  filename,
  md5_name,
  qa_set,
  final_generation = false
) {
  const qaSetDiv = document.querySelector(`#qa-set-${md5_name}`);
  set_file_status(filename, md5_name, "Finished.");

  document.querySelector(".status-text").innerHTML = "Generated Q&As:";

  // FIXME: JUST PUT A \n before each Q: element. (except the 1st one)
  qa_set.split("\n").forEach((line, index) => {
    const paragraph = document.createElement("p");

    // Add newline space between each Q&A set
    if (index != 0 && index % 2 == 0) {
      //qaSetDiv.appendChild(document.createElement("br"))
    }

    paragraph.innerHTML = line;
    qaSetDiv.appendChild(paragraph);
  });
}

// Make our q&a set look prettier. Remove any empty answers, and format [NEWLINE] strings with an actual \n.
// Number our q&a set too.
function post_process_qa_set(qa_set) {
  qa_set = qa_set.replaceAll("[NEWLINE]", "\n");
  // Split the input string into lines
  const lines = qa_set.trim().split("\n");

  // Create a new string with numbers before each Q&A set
  let modifiedString = "";
  let questionNumber = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith("Q:")) {
      // Add the question with the number to the modified string
      questionNumber++;
      modifiedString += `<br><b>${questionNumber}.</b> ${lines[i].trim()}\n`;
    } else {
      // Add answers without modification
      modifiedString += `${lines[i].trim()}\n`;
    }
  }
  qa_set = modifiedString;
  console.log(qa_set);

  // Output the modified string
  return qa_set;
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
  }, 2000); // Check every 2 seconds (adjust this as needed)
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
    let qa_set = await response.text(); // Extract the plaintext content
    qa_set = post_process_qa_set(qa_set);
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
        set_file_status(
          filename,
          md5_name,
          "Generating questions and answers..."
        );
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
  files_cookie = Cookies.get("files");
  Cookies.remove("files");

  const files = JSON.parse(files_cookie);

  console.log(files);

  var file_names = [];
  var md5_names = [];

  for (const file_json of files) {
    file_names.push(file_json["file_name"]);
    md5_names.push(file_json["md5_name"]);
  }

  // Test output to see if our variables got initalized (they usually are)
  console.log(file_names);
  console.log(md5_names);

  // Populate HTML with the associated files

  for (let i = 0; i < file_names.length; i++) {
    const filename = file_names[i];
    const md5_name = md5_names[i];

    // ============== Create converting-files-list (li) elements ==============
    const converting_files_list = document.getElementById(
      "converting-files-list"
    );

    const file_list_elem = document.createElement("li");
    file_list_elem.id = `file-list-elm-${md5_name}`;

    // Create the loader div, b, p elements
    const div = document.createElement("div");
    div.id = `loader-${md5_name}`;
    div.className = "loader";

    const b = document.createElement("b");
    b.textContent = filename;

    const p = document.createElement("p");
    p.id = `converting-status-${md5_name}`;
    p.textContent = "Converting to text...";

    // Append the elements to file_list_elem
    file_list_elem.appendChild(div);
    file_list_elem.appendChild(b);
    file_list_elem.appendChild(document.createTextNode(" - "));
    file_list_elem.appendChild(p);

    converting_files_list.appendChild(file_list_elem);

    // ============== Create qa-set elements (div) ==============
    const qaSetsDiv = document.querySelector(".qa-sets");

    // Create the qa-set div
    const qaSetDiv = document.createElement("div");
    qaSetDiv.id = `qa-set-${md5_name}`;
    qaSetDiv.className = "qa-set";

    // Create the qa-set-title paragraph
    const qaSetTitleParagraph = document.createElement("p");
    qaSetTitleParagraph.id = `qa-set-title-${md5_name}`;
    qaSetTitleParagraph.className = "qa-set-title";

    // Create the b element
    const bElement = document.createElement("b");
    bElement.textContent = filename;

    // Set the text content of the paragraph
    qaSetTitleParagraph.appendChild(bElement);
    qaSetTitleParagraph.appendChild(
      document.createTextNode(" - Processing....")
    );

    // Append the paragraph to the qa-set div
    qaSetDiv.appendChild(qaSetTitleParagraph);

    // Append the qa-set div to the qa-sets div
    qaSetsDiv.appendChild(qaSetDiv);
  }

  // Iterate through all files string array, send a post request to our server at /pdf-to-text
  // Include the filename & md5_name of the file
  // Iterate through the file names and send a POST request for each file
  for (let i = 0; i < file_names.length; i++) {
    const filename = file_names[i];
    const md5_name = md5_names[i];

    post_pdf2json(filename, md5_name);
  }
});
