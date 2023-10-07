import os
import sys
import openai
import hashlib
import uuid
from . import pdf_processing

from quart import (
    Quart,
    render_template,
    flash,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
from werkzeug.utils import secure_filename


UNSTRUCTUED_API_URL = "http://unstructured-api:8000/general/v0/general"
OPENAI_API_KEY = "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"
UPLOAD_FOLDER = "./data/pdf-uploads"
JSON_FOLDER = "./data/pdf-json"
QA_FOLDER = "./data/pdf-qa"
ALLOWED_EXTENSIONS = {"pdf"}

# Configure quart
server = Quart(__name__)
server.config["UNSTRUCTUED_API_URL"] = UNSTRUCTUED_API_URL
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.config["JSON_FOLDER"] = JSON_FOLDER
server.config["QA_FOLDER"] = QA_FOLDER
server.config["MAX_CONTENT_LENGTH"] = 10 * 1000 * 1024  # 10mb
server.secret_key = "opnqpwefqewpfqweu32134j32p4n1234d"
conn = None
task_status = {}

# Configure OpenAI GPT
openai.api_key = OPENAI_API_KEY


def dir_last_updated(folder):
    return str(
        max(
            os.path.getmtime(os.path.join(root_path, f))
            for root_path, _, files in os.walk(folder)
            for f in files
        )
    )


def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@server.route("/", methods=["GET", "POST"])
async def home():
    print("homepage")

    # TODO: Have the files upload themselves automatically, and hide/disable the 'convert' button until all files oure uploaded.
    # Have this file upload progress displayed for the user.
    if request.method == "POST":
        files_dict = await request.files
        # check if the post request has the file part
        if "file" not in files_dict:
            flash("No file part")
            return redirect(request.url)

        files = [file for file in files_dict.getlist("file")]
        # Get a list of files from request.files
        if len(files) < 1:
            flash("No selected file")
            return redirect(request.url)

        file_names = []
        md5_names = []

        # FIXME: Check if file already exists.
        for file in files:
            if file and allowed_file(file.filename):
                print(
                    "User uploaded pdf, redirecting.. {}".format(file.filename),
                    file=sys.stderr,
                )
                # Create /pdf-uploads directory if it doesn't exist.
                if not os.path.exists(server.config["UPLOAD_FOLDER"]):
                    os.makedirs(server.config["UPLOAD_FOLDER"])

                file_contents = file.stream.read()
                # Compute the MD5 hash of the contents
                md5_name = hashlib.md5(file_contents).hexdigest()
                filename = secure_filename(file.filename).replace(".pdf", "")

                md5_names.append(md5_name)
                file_names.append(filename)
                file.filename = f"{md5_name}.pdf"

                # Release the pointer that reads the file so we can save it properly
                file.stream.seek(0)

                await file.save(
                    os.path.join(server.config["UPLOAD_FOLDER"], file.filename)
                )

        session["file_names"] = file_names
        session["md5_names"] = md5_names
        return redirect("results")

    return await render_template(
        "index.html", last_updated=dir_last_updated("./src/static")
    )


@server.route("/pdf-qa/<md5_name>", methods=["GET"])
def get_pdf_qa(md5_name):
    with open(f'{server.config["QA_FOLDER"]}/{md5_name}.txt', "r") as file:
        return file.read()


@server.route("/task_status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    # Retrieve the status of a specific task
    status = task_status.get(task_id, "not_found")
    return jsonify({"status": status})


@server.route("/pdf2json", methods=["POST"])
async def pdf2json():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Generate a unique task ID, set it as processing
        task_id = str(uuid.uuid4())
        task_status[task_id] = "processing"

        # Start the processing task asynchronously
        server.add_background_task(
            pdf_processing.async_pdf2json,
            server,
            task_status,
            filename,
            md5_name,
            task_id,
        )

        # Return the task ID to the client
        return jsonify({"task_id": task_id, "filename": filename, "md5_name": md5_name})

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"


@server.route("/json2questions", methods=["POST"])
async def json2questions():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Generate a unique task ID, set it as processing
        task_id = str(uuid.uuid4())
        task_status[task_id] = "processing"

        server.add_background_task(
            pdf_processing.async_json2questions,
            server,
            task_status,
            filename,
            md5_name,
            task_id,
        )

        # Return the task ID to the client
        return jsonify({"task_id": task_id, "filename": filename, "md5_name": md5_name})

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"
        # Have GPT pre-process these raw chunks


@server.route("/results", methods=["GET"])
async def results():
    file_names = session.get("file_names")
    md5_names = session.get("md5_names")
    if file_names is None or md5_names is None:
        return redirect("/")

    session.pop("file_names")
    session.pop("md5_names")

    return await render_template(
        "results.html",
        file_names=file_names,
        md5_names=md5_names,
        last_updated=dir_last_updated("./src/static"),
    )


if __name__ == "__main__":
    server.run()
