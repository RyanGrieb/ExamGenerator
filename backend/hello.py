import os
import sys
import mysql.connector
from flask import Flask, render_template, flash, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import requests


UNSTRUCTUED_API_URL = "http://unstructured-api:8000/general/v0/general"
UPLOAD_FOLDER = "./pdf-uploads"
ALLOWED_EXTENSIONS = {"pdf"}


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


def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


server = Flask(__name__)
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.secret_key = "opnqpwefqewpfqweu32134j32p4n1234d"
conn = None


@server.route("/", methods=["GET", "POST"])
def home():
    print("homepage")

    global conn
    if not conn:
        conn = DBManager(password_file="/run/secrets/db-password")
        conn.populate_db()
    rec = conn.query_titles()

    if request.method == "POST":
        print("post")
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        files = request.files.getlist("file")
        # Get a list of files from request.files
        if len(files) < 1:
            flash("No selected file")
            return redirect(request.url)

        file_names = []

        for file in files:
            file_names.append(file.filename)

            if file and allowed_file(file.filename):
                print(
                    "User uploaded pdf, redirecting.. {}".format(file), file=sys.stderr
                )
                # Create /pdf-uploads directory if it doesn't exist.
                if not os.path.exists(server.config["UPLOAD_FOLDER"]):
                    os.makedirs(server.config["UPLOAD_FOLDER"])
                filename = secure_filename(file.filename)
                file.save(os.path.join(server.config["UPLOAD_FOLDER"], filename))

        session["files"] = file_names
        return redirect("results")

    return render_template("index.html", rec=rec)


@server.route("/results")
def results():
    # Get the list of files we are to process (these are already uploaded in storage)

    # Start the conversion process

    # 1. Convert the pdf to text
    files = session["files"]
    session.pop("files")

    for file in files:
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

        print(response, file=sys.stderr)
        print(response.status_code, file=sys.stderr)
        print(response.text, file=sys.stderr)

        file_data["files"].close()

    # 2. Break apart these text blocks into 'tokens', so we can use the chatgpt api

    # 3. Call the chatgpt api and wait for the response

    # 4. Take output & print it out to the user.

    return render_template("results.html")


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
