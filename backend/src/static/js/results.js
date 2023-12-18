class FileData {
  constructor(filename, md5_name, conversion_types, conversion_options) {
    this.filename = filename;
    this.md5_name = md5_name;
    this.conversion_types = conversion_types;
    this.conversion_options = conversion_options; //Dictonary
    this.data = {};
  }
}

let md5_files = [];
let files_data = {};

const delay = (ms) => new Promise((res) => setTimeout(res, ms));

async function display_file_data(filename, md5_name, conversion_type) {
  const file_data = files_data[md5_name];
  const results_output = document.querySelector(".results-output");

  if (!file_data) {
    return;
  }

  results_output.innerHTML = "";

  const title_elem = document.createElement("h2");

  if (conversion_type == "test") {
    title_elem.innerHTML = `${filename} Test/Quiz Questions:`;
    results_output.appendChild(title_elem);

    // Construct Test Question/Answer pairs
    const test_questions_set_div = document.createElement("div");
    for (const [index, test_question_set] of file_data.data[conversion_type].entries()) {
      const p_element = document.createElement("p");
      const question = test_question_set[1].replace(/([A-Za-z]\)\s)/g, "<br>$1");
      const answer = test_question_set[2];
      p_element.innerHTML = `<b>${index + 1}.</b> ${question}<br><br>${answer}`;
      test_questions_set_div.appendChild(p_element);
    }
    results_output.appendChild(test_questions_set_div);
  }

  if (conversion_type == "keywords") {
    title_elem.innerHTML = `${filename} Keyword/Definition Pair:`;
    results_output.appendChild(title_elem);

    // Construct Keyword/Definition pairs
    const keywords_sets_div = document.createElement("div");
    for (const keyword_set of file_data.data[conversion_type]) {
      const p_element = document.createElement("p");
      p_element.innerHTML = `<u>${keyword_set[0]}</u>: ${keyword_set[1]}`;
      keywords_sets_div.appendChild(p_element);
    }
    results_output.appendChild(keywords_sets_div);
  }

  if (conversion_type == "flashcards") {
    title_elem.innerHTML = `${filename} Flashcard Set:`;
    results_output.appendChild(title_elem);

    try {
      // Fetch the flashcard HTML
      const response = await fetch("/flashcard"); // Update with the correct endpoint

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const flashcardHTML = await response.text();

      // Append the fetched flashcard HTML to qaSetDiv
      const flashcardDiv = document.createElement("div");
      flashcardDiv.style = "display: flex; justify-content: center;";
      flashcardDiv.innerHTML = flashcardHTML;
      results_output.appendChild(flashcardDiv);
      set_flashcard(file_data, 0, 0);

      // Construct Q&A sets
      const qa_sets_div = document.createElement("div");
      for (const qa_set of file_data.data["flashcards"]) {
        const p_element = document.createElement("p");
        p_element.innerHTML = `${qa_set[0]} | ${qa_set[1]}`;
        qa_sets_div.appendChild(p_element);
      }
      results_output.appendChild(qa_sets_div);
    } catch (error) {
      console.error("There was a problem fetching the flashcard HTML:", error);
    }
  }
}

function set_flashcard(file_data, side, page) {
  // Set flashcard title
  const flashcard_text = file_data.data["flashcards"][page][side];
  const total_pages = file_data.data["flashcards"].length;
  document.querySelector(".flashcard-text p").innerHTML = flashcard_text;
  // Set flashcard page
  document.querySelector(".flashcard-count p").innerHTML = `${page + 1} / ${total_pages}`;
  // Map buttons to naviagate pages, if not defined already.
  document.querySelector(".flashcard-forward").onclick = () => {
    set_flashcard(file_data, 0, Math.min(page + 1, total_pages - 1));
  };
  document.querySelector(".flashcard-back").onclick = () => {
    set_flashcard(file_data, 0, Math.max(page - 1, 0));
  };
  document.querySelector(".flashcard-flip").onclick = () => {
    set_flashcard(file_data, side == 0 ? 1 : 0, page);
  };
}

function get_logs(md5_name) {
  console.log("Getting logs for " + md5_name);
  window.open(`/logs/${md5_name}`);
}

function add_qa_set_to_page(filename, md5_name, qa_set, final_generation = false) {
  const qaSetDiv = document.querySelector(`#qa-set-${md5_name}`);

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

function on_export_click() {
  post_export_results(file_names, md5_names, "pdf");
}

// Tell the server to convert specific files to a specific export_type
async function post_export_results(file_names, md5_names, export_type) {
  try {
    // Create a FormData object to send data with the POST request
    const formData = new FormData();
    formData.append("file_names", JSON.stringify(file_names));
    formData.append("md5_names", JSON.stringify(md5_names));
    formData.append("export_type", export_type);

    // Send a POST request to the server and wait for the response
    const response = await fetch("/export_results", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      console.log("GOT OK FROM post_export_results");

      const responseData = await response.json();
      const task_id = responseData.task_id;
      const file_id = responseData.file_id;

      checkTaskStatus(
        task_id,
        () => {
          window.open(`/exports/${file_id}.${export_type}`);
          //console.log("Export complete");
          // FIXME: Send a get request to see what our results are!
        },
        () => {
          //FIXME: Tell the user an error occured when exporting!
        },
      );
    } else {
      // Handle network or other errors here
      console.error(`Error sending export request to the server: ${error}`);
    }
  } catch (error) {
    // Handle network or other errors here
    console.error(`Error sending export request to the server: ${error}`);
  }
}

async function checkTaskStatus(task_id, completedCallback, errorCallback) {
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
        completedCallback();
        // You can perform further actions here
      } else if (statusData.status === "processing") {
        console.log(`Task with ID ${task_id} is still processing.`);
      } else {
        clearInterval(interval); // Stop checking on error
        console.error(`Unknown status for task with ID ${task_id}: ${statusData.status}`);
        errorCallback();
      }
    } else {
      clearInterval(interval); // Stop checking on error
      console.error(`Error checking task status for task ID ${task_id}: ${statusResponse.status}`);
      errorCallback();
    }
  }, 2000); // Check every 2 seconds (adjust this as needed)
}

async function get_converted_file(file_data, conversion_type) {
  console.log("Fetch generated file set from server:");

  const params = new URLSearchParams({
    filename: file_data.filename,
    md5_name: file_data.md5_name,
    conversion_type: conversion_type,
  });
  const url = `/convertfile/?${params}`;
  console.log(url);
  const response = await fetch(url, {
    method: "GET",
  });

  if (response.ok) {
    // Print the plaintext string here:
    let json_data = JSON.parse(await response.text());
    console.log(json_data);
    file_data.data[conversion_type] = json_data;
    set_file_status(file_data.md5_name, conversion_type, "checkmark-done");
  }
}

// Convert the file to flashcards, keyword/definition, test questions, ect.
async function post_convert_file(file_data, conversion_type, conversion_options, completeCallback, errorCallback) {
  console.log("POST: Convert file to:" + conversion_type);

  try {
    // Create a FormData object to send data with the POST request
    const formData = new FormData();
    formData.append("filename", file_data.filename);
    formData.append("md5_name", file_data.md5_name);
    formData.append("conversion_type", conversion_type);
    formData.append("conversion_options", JSON.stringify(conversion_options));

    // Send a POST request to the server and wait for the response
    const response = await fetch("/convertfile", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const responseData = await response.json();
      const task_id = responseData.task_id;

      checkTaskStatus(
        task_id,
        () => completeCallback(task_id),
        () => errorCallback(task_id),
      );
    } else {
      // Handle network or other errors here
      console.error(`Error sending ${file_data.filename} to the server: ${error}`);
    }
  } catch (error) {
    // Handle network or other errors here
    console.error(`Error sending ${file_data.filename} to the server: ${error}`);
  }
}

function set_file_status(md5_name, conversion_type, iconName) {
  const list_element = document.getElementById(`li-${md5_name}-${conversion_type}`);

  //Remove existing <i> elements
  const existing_i_elem = list_element.querySelector("i");
  if (existing_i_elem) list_element.removeChild(existing_i_elem);

  const loader = document.createElement("i");
  loader.className = iconName;
  loader.id = md5_name;
  list_element.appendChild(loader);
}

window.addEventListener("load", async () => {
  files_cookie = Cookies.get("files");

  if (!files_cookie) {
    return;
  }

  for (const file_json of JSON.parse(files_cookie)) {
    files_data[file_json["md5_name"]] = new FileData(
      file_json["file_name"],
      file_json["md5_name"],
      file_json["conversion_types"],
      file_json["conversion_options"],
    );
    md5_files.push(file_json["md5_name"]);
  }

  // Populate HTML with the associated files

  for (let i = 0; i < md5_files.length; i++) {
    // Iterate through all files string array, send a post request to our server at /pdf-to-text
    // Include the filename & md5_name of the file
    // Iterate through the file names and send a POST request for each file
    const md5_name = md5_files[i];
    const filename = files_data[md5_name].filename;
    for (const conversion_type of files_data[md5_name].conversion_types) {
      const file_list = document.querySelector(`.results-${conversion_type} ul`);

      const file_p = document.createElement("p");
      file_p.innerHTML = filename;

      const list_item = document.createElement("li");
      list_item.id = `li-${md5_name}-${conversion_type}`;
      list_item.appendChild(file_p);

      list_item.onclick = () => {
        display_file_data(filename, md5_name, conversion_type);
      };
      file_list.appendChild(list_item);

      set_file_status(md5_name, conversion_type, "loader");
    }
  }

  //TODO: Check our existing conversion_types with GET, to speed up files that might already be processed.

  for (let i = 0; i < md5_files.length; i++) {
    const md5_name = md5_files[i];
    const file_data = files_data[md5_name];

    await new Promise((resolve) => {
      const completeCallback = (task_id) => {
        console.log("pfd2text callback done: " + task_id + " | " + file_data.filename);
        for (const conversion_type of file_data.conversion_types) {
          post_convert_file(
            file_data,
            conversion_type,
            file_data.conversion_options,
            () => {
              //Completion callback
              console.log("Completed file conversion");
              get_converted_file(file_data, conversion_type);
            },
            () => {
              //Error callback
              console.log("Error occurred when converting file");
            },
          );
        }
        resolve();
      };

      const errorCallback = async (task_id) => {
        console.log("PDF2JSON callback error:");
        // The task was unsuccessful and an error occured! Tell that to the user..
        await delay(3000);
        i--;
        resolve();
      };

      post_convert_file(file_data, "text", {}, completeCallback, errorCallback);
    });
  }
});
