import os
import sys
import json
import openai
import hashlib
import asyncio
import aiohttp
import time
import uuid
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
import requests


UNSTRUCTUED_API_URL = "http://unstructured-api:8000/general/v0/general"
OPENAI_API_KEY = "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"
UPLOAD_FOLDER = "./pdf-uploads"
TEXT_FOLDER = "./pdf-text"
ALLOWED_EXTENSIONS = {"pdf"}

# Configure quart
server = Quart(__name__)
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.config["TEXT_FOLDER"] = TEXT_FOLDER
server.config["MAX_CONTENT_LENGTH"] = 10 * 1000 * 1024  # 10mb
server.secret_key = "opnqpwefqewpfqweu32134j32p4n1234d"
conn = None
task_status = {}

# Configure OpenAI GPT
openai.api_key = OPENAI_API_KEY


"""
class DBManager:
    def __init__(self, database="example", host="db", user="root", password_file=None):
        pf = open(password_file, "r")
        self.connection = mysql.connector.connect(
            user=user,
            password=pf.read(),
            host=host,  # name of the mysql service as set in the docker compose file
            database=database,
            auth_plugin="mysql_native_password",
        )
        pf.close()
        self.cursor = self.connection.cursor()

    def populate_db(self):
        self.cursor.execute("DROP TABLE IF EXISTS blog")
        self.cursor.execute(
            "CREATE TABLE blog (id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(255))"
        )
        self.cursor.executemany(
            "INSERT INTO blog (id, title) VALUES (%s, %s);",
            [(i, "Blog post #%d" % i) for i in range(1, 5)],
        )
        self.connection.commit()

    def query_titles(self):
        self.cursor.execute("SELECT title FROM blog")
        rec = []
        for c in self.cursor:
            rec.append(c[0])
        return rec
"""


def dir_last_updated(folder):
    return str(
        max(
            os.path.getmtime(os.path.join(root_path, f))
            for root_path, dirs, files in os.walk(folder)
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

    # global conn
    # if not conn:
    #    conn = DBManager(password_file="/run/secrets/db-password")
    #    conn.populate_db()
    # rec = conn.query_titles()

    if request.method == "POST":
        files_dict = await request.files
        print(files_dict)
        # check if the post request has the file part
        if "file" not in files_dict:
            flash("No file part")
            return redirect(request.url)

        files = [file for file in files_dict.getlist("file")]
        print(files)
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
        "index.html", last_updated=dir_last_updated("./static")
    )


async def async_text2questions(filename, md5_name, task_id):
    json_data = None
    with open(f"./pdf-text/{md5_name}.txt", "r") as file:
        json_data = json.load(file)

        text_chunks: list[str] = []
        chunk_index = 0

        for item in json_data:
            title = None

            if "text" in item:
                text = item["text"]

                if len(text) < 1:
                    continue
                if len(text_chunks) <= chunk_index:
                    text_chunks.append("")

                if title is not None:
                    text_chunks[chunk_index] += f"|TITLE: {title}|"

                text_chunks[chunk_index] += f"|{text}|"

                if len(text_chunks[chunk_index]) > 1000:
                    chunk_index += 1

        for chunk in text_chunks:
            print(f"{chunk}\n", file=sys.stderr)


async def async_pdf2text(filename, md5_name, task_id):
    request_form = await request.form
    try:
        # Get the filename and md5_name from the POST request
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Check if the variables are received correctly
        print("Received filename:", filename, file=sys.stderr)
        print("Received md5_name:", md5_name, file=sys.stderr)

        file_path = f"./pdf-uploads/{md5_name}.pdf"

        # file_data = {"files": open(file_path, "rb")}
        form_data = aiohttp.FormData()
        form_data.add_field("files", open(file_path, "rb"))
        form_data.add_field("encoding", "utf_8")
        form_data.add_field("include_page_breaks", "true")
        form_data.add_field("coordinates", "false")

        headers = {"accept": "application/json"}

        # fix session.post(...)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                UNSTRUCTUED_API_URL, headers=headers, data=form_data
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    # TODO: Implement a keep-alive loop & cancel these post requests if terminated.
                    # FIXME: Handle any errors thrown by unstructured api.
                    # FIXME: Parse the JSON from respose.text and create a semi-formatted text-output from it.

                    # Create /pdf-text directory if it doesn't exist.
                    if not os.path.exists(server.config["TEXT_FOLDER"]):
                        os.makedirs(server.config["TEXT_FOLDER"])

                    with open(
                        f'{server.config["TEXT_FOLDER"]}/{md5_name}.txt', "w"
                    ) as file:
                        file.write(response_text)

                    task_status[task_id] = "completed"
                else:
                    await asyncio.sleep(1)
                    task_status[task_id] = "error"

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        task_status[task_id] = "error"


@server.route("/task_status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    # Retrieve the status of a specific task
    status = task_status.get(task_id, "not_found")
    return jsonify({"status": status})


@server.route("/pdf2text", methods=["POST"])
async def pdf2text():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Store task status as 'processing'
        task_status[task_id] = "processing"

        # Start the processing task asynchronously
        server.add_background_task(async_pdf2text, filename, md5_name, task_id)

        # Return the task ID to the client
        return jsonify({"task_id": task_id, "filename": filename, "md5_name": md5_name})

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"


@server.route("/text2questions", methods=["GET", "POST"])
async def text2questions():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Store task status as 'processing'
        task_status[task_id] = "processing"

        if request.method == "POST":
            server.add_background_task(
                async_text2questions, filename, md5_name, task_id
            )

        # Return the task ID to the client
        return jsonify({"task_id": task_id, "filename": filename, "md5_name": md5_name})

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"
        # Have GPT pre-process these raw chunks


@server.route("/results", methods=["GET", "POST"])
async def results():
    file_names = session.get("file_names")
    md5_names = session.get("md5_names")
    if file_names is None or md5_names is None:
        return redirect("/")

    session.pop("file_names")
    session.pop("md5_names")

    # Get the list of files we are to process (these are already uploaded in storage)

    # Start the conversion process

    # 1. Convert the pdf to text
    if request.method == "POST":
        for file in file_names:
            file_path = f"./pdf-uploads/{file}"
            file_data = {"files": open(file_path, "rb")}

            headers = {"accept": "application/json"}
            data = {
                "encoding": "utf_8",
                "include_page_breaks": "true",
                "coordinates": "false",
            }

            response = requests.post(
                UNSTRUCTUED_API_URL, headers=headers, data=data, files=file_data
            )

            file_data["files"].close()
            # print(response, file=sys.stderr)
            # print(response.status_code, file=sys.stderr)
            print(response.text, file=sys.stderr)

            # 2. Break apart these text blocks into 'chunks'. We keep 1K character space so
            # we can add onto these chunks if there split between sentences or important sections.

            # FIXME: INDICATE PAGE NUMBERS WHEN SEPERATING.

            text_chunks: list[str] = []
            chunk_index = 0
            json_data = json.loads(response.text)

            for item in json_data:
                title = None

                if "text" in item:
                    text = item["text"]

                    if len(text) < 1:
                        continue
                    if len(text_chunks) <= chunk_index:
                        text_chunks.append("")

                    if title is not None:
                        text_chunks[chunk_index] += f"|TITLE: {title}|"

                    text_chunks[chunk_index] += f"|{text}|"

                    if len(text_chunks[chunk_index]) > 1000:
                        chunk_index += 1

            # for chunk in text_chunks:
            #    print(f"{chunk}\n", file=sys.stderr)

            print(f"Raw chunks length:{len(text_chunks)}", file=sys.stderr)

            print(
                f"Pre-Chunk #1: \n{text_chunks[0]} \n Pre-Chunk #2: \n{text_chunks[1]}",
                file=sys.stderr,
            )
            # 3. Get ChatGPT to compare two 1K chunks, and pick a new index to split the two. This way we
            # can create new chunks that don't cut off sentences or paragraphs.
            # We also perform formatting like |...text...| => ...text...
            # create a chat completion

            """
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Format the following information into a structured text block: {text_chunks[0]}",
                    }
                ],
            )
        
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Separate the following raw chunks into two distinct chunks, preserving the data in between. Keep the raw formatting of |text|, we'll process it later.: \nChunk #1:{text_chunks[0]} \nChunk # 2: {text_chunks[1]}",
                    }
                ],
            )

            # print the chat completion
            print(chat_completion.choices[0].message.content, file=sys.stderr)
    """
            # 4. After formatting and getting the chunks to not cut off important information,
            # get ChatGPT to process these chunks into multiple Q&A responses.

            # 4. Take final output from ChatGPT & print it out to the user.

    return await render_template(
        "results.html",
        file_names=file_names,
        md5_names=md5_names,
        last_updated=dir_last_updated("./static"),
    )


@server.route("/dbtest")
def listBlog():
    global conn
    if not conn:
        conn = DBManager(password_file="/run/secrets/db-password")
        conn.populate_db()
    rec = conn.query_titles()

    response = ""
    for c in rec:
        response = response + "<div>   yeah we still got it:  " + c + "</div>"
    return response


if __name__ == "__main__":
    server.run()
