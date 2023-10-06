import os
import sys
import json
import openai
import hashlib
import asyncio
import aiohttp
import time
import uuid
import re

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
JSON_FOLDER = "./pdf-json"
QA_FOLDER = "./pdf-qa"
ALLOWED_EXTENSIONS = {"pdf"}

# Configure quart
server = Quart(__name__)
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.config["JSON_FOLDER"] = JSON_FOLDER
server.config["QA_FOLDER"] = QA_FOLDER
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


def get_chunks_from_gpt_response(response: json):
    response_chunks: str = response["choices"][0]["message"]["content"]
    chunk1 = response_chunks.partition("Chunk1: ")[-1].partition("Chunk2:")[0].strip()
    chunk2 = response_chunks.partition("Chunk2:")[-1].strip()
    return (chunk1, chunk2)


# Remove duplicate tokens given two provided chunks.
def remove_duplicates(chunk1, chunk2):
    tokens_1 = [token for token in chunk1.split("|") if token.strip()]
    tokens_2 = [token for token in chunk2.split("|") if token.strip()]

    tokens_1_copy = tokens_1.copy()

    for token_1 in tokens_1_copy:
        if token_1 in tokens_2:
            while token_1 in tokens_1:
                tokens_1.remove(token_1)
            while token_1 in tokens_2:
                tokens_2.remove(token_1)

    formatted_chunk_1 = "|" + "|".join(tokens_1) + "|"
    formatted_chunk_2 = "|" + "|".join(tokens_2) + "|"

    return (formatted_chunk_1, formatted_chunk_2)


async def gpt_remove_token_formatting(chunk1, chunk2):
    if chunk1 is None:
        chunk1 = "[EMPTY]"
    print(f"Before removing all tokens:\n Chunk1: {chunk1}\nChunk2: {chunk2}")
    # FIXME: GPT responds with more chunks (chunk3, chunk4?)
    prompt = f"Remove the '|' characters from the following two chunks to form proper sentences with spaces, and other proper formatting you see fit. You should not respond with empty chunk(s), unless [EMPTY] is present within one.\nRespond with this only: Chunk1: [your_output] Chunk2: [your_output]\nHere are the two chunks:\nChunk1: {chunk1}\nChunk2: {chunk2}"

    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )

    chunk1, chunk2 = get_chunks_from_gpt_response(response)
    print(f"fter removing all tokens:\n Chunk1: [[{chunk1}]]\nChunk2: [[{chunk2}]]")
    return (chunk1, chunk2)


async def gpt_resize_cutoff_chunks(chunk1, chunk2):
    print("Resize chunks stop information from getting cut off:")
    prompt = f"Determine if information is cut off between Chunk1 and Chunk2, if so: Transfer the text cut off from Chunk2 to Chunk1, then remove the text used from Chunk2. This allows us to read information properly when viewing one individual chunk. Also if a chunk contains a 'learning objectives' section, remove that information.\nIf no information is cut off, dont make any changes.\nYou should not respond with empty chunks.\nRespond with this only: Chunk1: [your_output] Chunk2: [your_output]\nHere are the two chunks:\nChunk1: {chunk1}\nChunk2: {chunk2}"

    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )

    chunk1, chunk2 = get_chunks_from_gpt_response(response)
    print(
        f"After fixing cut off information:\n Chunk1: [[{chunk1}]]\nChunk2: [[{chunk2}]]"
    )
    return (chunk1, chunk2)


async def gpt_generate_qa(data):
    print(f"Generate Q&A from text chunk: {data}")
    prompt = f"From the provided data, generate flashcard questions and answers. Skip (dont read and respond to) learning objectives.\nIf you believe there is no valid Q&A to generate, respond with only: 'Q2A: None'.\nIf there is valid data, respond in this format:\nQ: ... \nA: ...\nQ: ... \nA:...\nHere is the provided data:\n{data}"

    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    response_data: str = response["choices"][0]["message"]["content"]
    # print("Q&A RESPONSE DATA:")
    # print(response_data)
    if "Q2A: None" in response_data:
        return None

    qa_sets = response_data.split("\n")
    qa_sets = [qa_set for qa_set in qa_sets if qa_set != ""]

    if len(qa_sets) % 2 != 0:
        print("!!! WARNING: UNEVEN Q&A RESPONSE (mssing q or a)!!!")
        return qa_sets

    # Remove duplicate Q&A in list (Q & A Must both be the same between duplicate pairs)
    new_qa_sets = []
    existing_questions = []
    existing_answers = []

    for i in range(0, len(qa_sets), 2):
        question = qa_sets[i]
        answer = qa_sets[i + 1]

        # We have a duplicate, remove it! (By not appending anything!)
        if question in existing_questions and answer in existing_answers:
            continue

        new_qa_sets.append(question)
        new_qa_sets.append(answer)
        existing_questions.append(question)
        existing_answers.append(answer)

    qa_sets = new_qa_sets

    return qa_sets


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
        "index.html", last_updated=dir_last_updated("./static")
    )


async def async_text2questions(filename, md5_name, task_id):
    with open(f"./pdf-json/{md5_name}.json", "r") as file:
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

        # Send two chunks to gpt, and have it parse the data between them.
        print(f"CHUNK SIZE: {len(text_chunks)}")
        new_text_chunks = []
        i = 0

        # FIXME: ACCOUNT FOR A SINGLE CHUNK!!!!!
        # if len(text_chunks) <= 1:
        #    new_text_chunks.append(text_chunks[0] + " - NEW")

        while i < len(text_chunks) - 1:
            chunk1 = text_chunks[i]
            chunk2 = text_chunks[i + 1]

            # If we are re-using the 2nd to last chunk (for odd number of chunks), utilize the updated 2nd to last chunk done previously.
            processed_chunk1 = None
            if len(text_chunks) % 2 != 0 and i >= len(text_chunks) - 2:
                processed_chunk1 = new_text_chunks.pop()

            # 1. Remove page number tokens
            chunk1 = re.sub(r"\|\d+\|", "", chunk1)
            chunk2 = re.sub(r"\|\d+\|", "", chunk2)
            # 2. Remove duplicate tokens (Note how we still use the old chunk1 here, it's important)
            chunk1, chunk2 = remove_duplicates(chunk1, chunk2)

            # FIXME: REMOVE COPYRIGHT TOKENS!!!!!!!!!!

            # If chunk1 was already processed (happens with odd number of chunks),
            # set chunk1 to None for step #3, since removing token formatting was already done
            if processed_chunk1:
                chunk1 = None

            # 3. Remove tokens & create normal sentences:
            chunk1, chunk2 = await gpt_remove_token_formatting(chunk1, chunk2)

            # 4. Resize chunks to prevent cut-off information
            # Set chunk1 to our processed chunk, since it might need to accept cut-off information.
            if processed_chunk1:
                chunk1 = processed_chunk1

            chunk1, chunk2 = await gpt_resize_cutoff_chunks(chunk1, chunk2)

            new_text_chunks.append(chunk1)
            new_text_chunks.append(chunk2)

            # Increment this loop by 2, or if we have odd text_chunks, re-use the 2nd to last chunk at the end.
            if len(text_chunks) % 2 != 0 and (i + 2) >= len(text_chunks) - 1:
                i += 1
            else:
                i += 2

        print("DONE!!!!! FORMATTED TEXT CHUNKS: ")
        new_text_chunks = [chunk for chunk in new_text_chunks if chunk != ""]
        print(new_text_chunks)

        generated_qa = []
        text_chunks = new_text_chunks
        for text_chunk in new_text_chunks:
            qa = await gpt_generate_qa(text_chunk)
            if qa is None:
                continue
            generated_qa = generated_qa + qa

        qa_text = ""
        for qa in generated_qa:
            qa_text += f"{qa}\n"

        # Save Q&A set to filesystem
        # Create /pdf-qa directory if it doesn't exist.
        if not os.path.exists(server.config["QA_FOLDER"]):
            os.makedirs(server.config["QA_FOLDER"])

        with open(f'{server.config["QA_FOLDER"]}/{md5_name}.txt', "w") as file:
            file.write(qa_text)

        task_status[task_id] = "completed"


async def async_pdf2json(filename, md5_name, task_id):
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

                    # Create /pdf-json directory if it doesn't exist.
                    if not os.path.exists(server.config["JSON_FOLDER"]):
                        os.makedirs(server.config["JSON_FOLDER"])

                    with open(
                        f'{server.config["JSON_FOLDER"]}/{md5_name}.json', "w"
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


@server.route("/pdf-qa/<md5_name>", methods=["GET"])
def get_pdf_qa(md5_name):
    with open(f"./pdf-qa/{md5_name}.txt", "r") as file:
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

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Store task status as 'processing'
        task_status[task_id] = "processing"

        # Start the processing task asynchronously
        server.add_background_task(async_pdf2json, filename, md5_name, task_id)

        # Return the task ID to the client
        return jsonify({"task_id": task_id, "filename": filename, "md5_name": md5_name})

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"


@server.route("/text2questions", methods=["POST"])
async def text2questions():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())

        # Store task status as 'processing'
        task_status[task_id] = "processing"

        server.add_background_task(async_text2questions, filename, md5_name, task_id)

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
        last_updated=dir_last_updated("./static"),
    )


"""
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
"""

if __name__ == "__main__":
    server.run()
