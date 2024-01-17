window.addEventListener("load", async () => {
  // Get data list from flashcard.

  const params = new URLSearchParams({
    filename: filename,
    md5_name: md5_name,
    conversion_type: "flashcards",
  });

  const url = `/convertfile/?${params}`;
  console.log(url);
  const response = await fetch(url, {
    method: "GET",
  });

  if (response.ok) {
    const json_data = JSON.parse(await response.text());
    console.log(json_data);
    // Take json_list and display it to the user.
    const export_data_list = document.querySelector(".export-data-list");
    document.createEle;
    // Generate HTML for the list with checkboxes
    const ul_element = document.createElement("ul");
    json_data.forEach((qa_pair, index) => {
      // Create list item
      const li_element = document.createElement("li");

      // Create checkbox
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = `checkbox-${index}`;
      checkbox.name = "qa-checkbox";
      checkbox.value = index;

      // Create div where text is stored
      const text_div = document.createElement("div");
      text_div.classList.add("data-text");

      // Create label for the checkbox
      const label = document.createElement("label");
      label.htmlFor = `checkbox-${index}`;
      label.textContent = qa_pair[0];

      // Create paragraph for the answer
      const answer_paragraph = document.createElement("label");
      answer_paragraph.textContent = qa_pair[1];

      // Append checkbox, label, and answer paragraph to the list item
      li_element.appendChild(checkbox);
      text_div.appendChild(label);
      text_div.appendChild(answer_paragraph);
      li_element.appendChild(text_div);

      // Append list item to the unordered list
      ul_element.appendChild(li_element);
    });

    export_data_list.appendChild(ul_element);
  } else {
    // Extract error type from JSON response
    const error_data = await response.json();
    console.log(error_data);
  }
});
