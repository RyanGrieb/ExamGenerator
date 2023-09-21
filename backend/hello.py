import os
from flask import Flask, render_template, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
import mysql.connector

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


@server.route("/upload", methods=["POST"])
def upload_file():
    if "file" in request.files:
        print("WORKING?")
        file = request.files["file"]
        if file.filename != "":
            # The file field was triggered, and a file was uploaded
            # You can now process the uploaded file
            # For example, you can save it to a specific directory
            # file.save("uploads/" + file.filename)
            return "File uploaded successfully!"

    # If 'file' not in request.files or no file selected, handle accordingly
    return "No file selected or field not triggered."


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
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            print("User uploaded pdf, redirecting..")
            filename = secure_filename(file.filename)
            file.save(os.path.join(server.config["UPLOAD_FOLDER"], filename))
            # TODO: Indicate the file is uploaded.
            # return redirect(url_for("download_file", name=filename))

    return render_template("index.html", rec=rec)


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
