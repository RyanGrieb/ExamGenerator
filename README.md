# PDF2Flashcards

An AI web-app that scans PDFs and generates associated questions and answers.

## Features

1. Automated Question Generation: Use AI to automatically create quiz and test
   questions and answers from PDF content.
2. Multiple Question Types: It generates various question formats, including
   multiple-choice, true/false, multiple-selection.
3. Rest API: Other developers or companies can utilize our tool in their own projects
   or applications.
4. PDF Compatibility: Works seamlessly with PDF documents, making it easy to
   convert existing materials.
5. User-Friendly Interface: The website should be easy to use for the user.
6. Bulk Processing: It supports batch processing for efficient handling of multiple
   PDF files at once.
7. Accuracy: After generating questions, we can use AI again to validate our
   questions and answers that we created.
8. Export Options: Users can export generated questions in various formats for use
   in different learning management systems or assessment tools. This can include
   Anki, BlackBoard, a new PDF, or more.

## Developer Software Requirements

1. Docker
2. Python3
3. Visual Studio Code

## Build Instructions

1. Install Docker, VSCode, Git, and Python3
2. Clone the repository using `git clone https://github.com/RyanGrieb/PDF2Flashcards.git` in the terminal
3. `cd` into the cloned repository.
4. `cd` into the `./backend` file, and run `pip install -r requirements.txt` (You might need to restart VSCode for the imports to load properly)
5. Go back to the parent directory, `cd ..`
6. Create the docker containers: `docker compose up -d` (Check if these docker images exist already)
7. Find `./data/api-keys/open_ai.txt` and enter your API key there.
8. Re-build the containers with `docker compose up -d --build`
9. To navigate to the webpage at `localhost:8000`

To re-build the all the containers after you make changes, run `docker compose up -d --build`.

**Note:** You don't need to rebuild any containers if you just modified the python files inside the `backend` directory. It's updated for you automatically.
