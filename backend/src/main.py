import sys
import os, inspect
import openai
import hashlib
import uuid
import json
import stripe
from .async_actions import pdf_processing
from .async_actions.exporter import export_files
from .async_actions.async_task import *
from quart import Quart, Request, render_template, flash, request, redirect, url_for, session, jsonify, send_file
from quart_session import Session
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from .database import DBManager
import stripe
import pypdf

UNSTRUCTUED_API_URL = "http://unstructured-api:8000/general/v0/general"
OPENAI_API_KEY = "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"
UPLOAD_FOLDER = "./data/file-upload"
JSON_FOLDER = "./data/file-json"
PROCESSED_FOLDER = "./data/file-processed"
LOG_FOLDER = "./data/file-log"
EXPORT_FOLDER = "./data/exports"
ALLOWED_EXTENSIONS = {"pdf"}
CONCURRENT_TEXT_PROCESS_LIMIT = 2  # How many files unstructured API can handle at a time.


# Configure quart
server = Quart(__name__)
server.config["UNSTRUCTUED_API_URL"] = UNSTRUCTUED_API_URL
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.config["JSON_FOLDER"] = JSON_FOLDER
server.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER
server.config["LOG_FOLDER"] = LOG_FOLDER
server.config["EXPORT_FOLDER"] = EXPORT_FOLDER
server.config["MAX_CONTENT_LENGTH"] = 15 * 1000 * 1024  # 15mb
server.config["CONCURRENT_TEXT_PROCESS_LIMIT"] = CONCURRENT_TEXT_PROCESS_LIMIT
server.secret_key = "opnqpwefqewpfqweu32134j32p4n1234d"

# Setup redis
server.config["SESSION_TYPE"] = "redis"
server.config["SESSION_URI"] = "redis://redis:6379"
Session(server)

# Setup stripe
# /run/secrets/stripe
stripe_keys = {}
with open("/run/secrets/stripe", "r") as file:
    for line in file:
        key, value = line.strip().split("=")
        stripe_keys[key] = value

# Set up Stripe with the API keys
stripe.api_key = stripe_keys["private"]

# server.jinja_env.globals.update(zip=zip)
# Prevent flask form emptying session variables
# server.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)

# Configure OpenAI GPT
openai.api_key = OPENAI_API_KEY


def dir_last_updated(folder):
    return str(
        max(os.path.getmtime(os.path.join(root_path, f)) for root_path, _, files in os.walk(folder) for f in files)
    )


def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Returns account type (guest, free, paid)
def get_acount_type() -> str:
    if session.get("logged_in"):
        if session.get("card_connected"):
            return "paid"
        else:
            return "free"

    return "guest"


async def upload_file(request: Request):
    files_dict = await request.files
    print(files_dict, file=sys.stderr)

    if "file" not in files_dict:
        flash("No file part")
        return redirect(request.url)

    files = [file for file in files_dict.getlist("file")]

    # Get a list of files from request.files, should always be 1 file at a time.
    if len(files) != 1:
        return jsonify({"success": False})

    file: FileStorage = files[0]

    if not file or not allowed_file(file.filename):
        return jsonify({"success": False})


    # FIXME: Account for 
    pdf_reader = pypdf.PdfReader(file)
    number_of_pages = len(pdf_reader.pages)
    account_type = get_acount_type()

    if number_of_pages > 3 and account_type == "guest":
        return jsonify({"success": False, "error_type": "page_limit"})
    if number_of_pages > 10 and account_type == "free":
        return jsonify({"success": False, "error_type": "page_limit"})

    print(
        "User uploaded pdf: {}".format(file.filename),
        file=sys.stderr,
    )
    # Create /pdf-uploads directory if it doesn't exist.
    if not os.path.exists(server.config["UPLOAD_FOLDER"]):
        os.makedirs(server.config["UPLOAD_FOLDER"])

    file_contents = file.stream.read()
    # Compute the MD5 hash of the contents
    md5_name = hashlib.md5(file_contents).hexdigest()
    filename = secure_filename(file.filename).replace(".pdf", "")

    file.filename = f"{md5_name}.pdf"

    # Release the pointer that reads the file so we can save it properly
    file.stream.seek(0)
    # FIXME: Check if file already exists, if so dont bother saving it again.
    await file.save(os.path.join(server.config["UPLOAD_FOLDER"], file.filename))

    return (
        jsonify({"success": True, "file_name": filename, "md5_name": md5_name}),
        200,
        {"ContentType": "application/json"},
    )


@server.route("/", methods=["GET", "POST"])
async def home():
    if request.method == "POST":
        return await upload_file(request)

    return await render_template("index.html", last_updated=dir_last_updated("./src/static"))


@server.route("/pdf2json-processes", methods=["GET"])
async def get_pdf2json_processes():
    return {"processes": pdf_processing.pdf2json_processes}


# @server.errorhandler(404)
# async def page_not_found(e):
#    return redirect("/")


@server.route("/register", methods=["GET", "POST"])
async def register():
    if request.method == "POST":
        form_data = await request.form
        form_dict = dict(form_data)

        email = form_dict.get("email")
        password = form_dict.get("password")
        confirm_password = form_dict.get("confirm_password")

        if password != confirm_password:
            return await render_template(
                "register.html", last_updated=dir_last_updated("./src/static"), error_msg="Passwords do not match"
            )

        database = DBManager(pass_file="/run/secrets/db-password")
        response, error_msg = database.add_user(email, password)

        if response != 0:
            return await render_template(
                "register.html", last_updated=dir_last_updated("./src/static"), error_msg=error_msg
            )

        return redirect(url_for("login"))

    return await render_template("register.html", last_updated=dir_last_updated("./src/static"))


@server.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form_data = await request.form
        form_dict = dict(form_data)
        email = form_dict.get("email")
        password = form_dict.get("password")

        # Check if the email and password match a user in the database
        database = DBManager(pass_file="/run/secrets/db-password")
        db_user_obj, error_msg = database.get_user(email, password)
        print(db_user_obj, file=sys.stderr)
        if db_user_obj:
            print(db_user_obj, file=sys.stderr)
            session["logged_in"] = True
            session["email"] = email
            session["card_connected"] = db_user_obj.card_connected
            session.modified = True
            return redirect("/")
        else:
            # User doesn't exist or password is incorrect
            return await render_template(
                "login.html", last_updated=dir_last_updated("./src/static"), error_msg=error_msg
            )
    return await render_template("login.html", last_updated=dir_last_updated("./src/static"))


@server.route("/logout", methods=["POST"])
async def logout():
    session.clear()
    return redirect("/")


@server.route(
    "/profile",
    methods=[
        "GET",
    ],
)
async def profile():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return await render_template("profile.html", last_updated=dir_last_updated("./src/static"))


@server.route("/checkout/return", methods=["GET"])
async def handle_checkout_session():
    # Reference: https://stripe.com/docs/payments/save-and-reuse?platform=web&ui=embedded-checkout#set-up-stripe
    session_id = request.args.get("session_id")

    print(session_id, file=sys.stderr)
    # Retrieve checkout session
    checkout_session = stripe.checkout.Session.retrieve(session_id)

    # Retrieve the setup intent
    setup_intent = stripe.SetupIntent.retrieve(checkout_session.setup_intent)

    database = DBManager(pass_file="/run/secrets/db-password")

    customer = None

    # Create/fetch stripe customer
    stripe_user_id = database.get_stripe_user_id(session.get("email"))
    if not stripe_user_id:
        customer = stripe.Customer.create(email=session.get("email"), description="From PDF2Flashcards backend")
        database.add_stripe_customer(customer)
        stripe_user_id = customer.id
    # else:
    #    print("!!!!!!!! RETRIEVE", file=sys.stderr)
    #    customer = stripe.Customer.retrieve(stripe_user_id)

    # FIXME: Ensure that stripe actually has a user_id here, our DB might get fucked.

    # Attach payment method from the SetupIntent to the Stripe customer
    stripe.PaymentMethod.attach(
        setup_intent.payment_method,
        customer=stripe_user_id,
    )

    # Update customer's default payment method
    stripe.Customer.modify(
        # setup_intent.customer,
        id=stripe_user_id,
        invoice_settings={
            "default_payment_method": setup_intent.payment_method,
        },
    )

    # Update users table & set card_connected to True
    database.set_card_connected(session.get("email"), True)
    session["card_connected"] = True

    # Go back to user profile
    return redirect(url_for("profile"))


@server.route("/create-checkout-session", methods=["POST"])
async def create_checkout_session():
    base_url = request.url_root
    return_url = base_url + "checkout/return?session_id={CHECKOUT_SESSION_ID}"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="setup",
        ui_mode="embedded",
        return_url=return_url,
    )

    # Reference: https://stripe.com/docs/payments/save-and-reuse?platform=web&ui=embedded-checkout#set-up-stripe
    return jsonify(clientSecret=session.client_secret)


@server.route("/add-payment", methods=["GET"])
async def add_payment():
    return await render_template("add-payment.html", last_updated=dir_last_updated("./src/static"))


@server.route("/help", methods=["GET"])
async def help():
    return await render_template("help.html", last_updated=dir_last_updated("./src/static"))


@server.route("/flashcard_test", methods=["GET"])
async def flashcard_test():
    return await render_template("flashcard_test.html", last_updated=dir_last_updated("./src/static"))


@server.route("/flashcard", methods=["GET"])
async def flashcard():
    return await render_template("flashcard.html", last_updated=dir_last_updated("./src/static"))


# Get the Q&A set of the associated file.
@server.route("/pdf-qa/<md5_name>", methods=["GET"])
def get_pdf_qa(md5_name):
    with open(f'{server.config["PROCESSED_FOLDER"]}/{md5_name}.json', "r") as file:
        return json.load(file)["qa_set"]


# Get the logs of the associated file.
@server.route("/logs/<md5_name>", methods=["GET"])
async def get_logs(md5_name):
    with open(f'{server.config["LOG_FOLDER"]}/{md5_name}.txt', "r") as file:
        return await render_template(
            "log_info.html",
            log_data=file.read(),
            last_updated=dir_last_updated("./src/static"),
        )


@server.route("/export-flashcard", methods=["GET"])
async def export_flashcard():
    filename = request.args.get("filename")
    md5_name = request.args.get("md5_name")
    return await render_template(
        "export-flashcard.html", filename=filename, md5_name=md5_name, last_updated=dir_last_updated("./src/static")
    )


# Get the export file of the associated <file> name.
@server.route("/exports/<file>", methods=["GET"])
async def get_exported_document(file):
    export_folder = server.config["EXPORT_FOLDER"]
    return await send_file(f"{export_folder}/{file}", as_attachment=False)


# Retrieve the status of a specific task
@server.route("/task_status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    task = running_tasks.get(task_id)

    if task == None:
        return {}

    return task.get_status_json()


@server.route("/export_results", methods=["POST"])
async def export_results():
    request_form = await request.form
    try:
        file_names = request_form.get("file_names")
        md5_names = json.loads(request_form.get("md5_names"))
        export_type = request_form.get("export_type")

        # Generate a unique task ID, set it as processing
        task_id = str(uuid.uuid4())
        # Generate a unique  file_id, this will be the name of the exported file.
        file_id = str(uuid.uuid4())
        set_task_status(task_id, "processing")

        # Begin the export process
        server.add_background_task(
            export_files,
            server,
            task_id,
            file_id,
            md5_names,
            export_type,
        )

        # Return the task ID & file ID to the client
        # FIXME: Return file extension associated with our export_type
        # file_extension = exporter.get_file_extension(export_type)
        return jsonify({"task_id": task_id, "file_id": file_id})
    except Exception as e:
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"

    return None


@server.route("/convertfile/", methods=["GET"])
def get_convert_file():
    filename = request.args.get("filename")
    md5_name = request.args.get("md5_name")
    conversion_type = request.args.get("conversion_type")
    print(f"Convertfile GET - Get {conversion_type} of {filename}", file=sys.stderr)

    if filename and md5_name and conversion_type:
        file_path = f'{server.config["PROCESSED_FOLDER"]}/{md5_name}.json'
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
                if conversion_type in data:
                    return data[conversion_type]
                else:
                    return (
                        jsonify(
                            {"error": f"Conversion type '{conversion_type}' not found", "error_type": "no_conversion"}
                        ),
                        400,
                    )
        except FileNotFoundError:
            return jsonify({"error": f"File '{file_path}' not found", "error_type": "no_file"}), 404
        except Exception as e:
            return jsonify({"error": f"Error: {str(e)}", "error_type": "unknown"}), 500
    else:
        return jsonify({"error": "Missing parameters", "error_type": "missing_params"}), 400


@server.route("/convertfile", methods=["POST"])
async def post_convert_file():
    request_form = await request.form
    try:
        filename = request_form.get("filename")
        md5_name = request_form.get("md5_name")
        convert_type = request_form.get("conversion_type")
        conversion_options = json.loads(request_form.get("conversion_options"))
        print("*** CONVERSION OPTIONS: ***", file=sys.stderr)
        print(conversion_options, file=sys.stderr)

        # Generate a unique task ID, set it as processing
        task_id = str(uuid.uuid4())
        set_task_status(task_id, "processing")
        set_task_attribute(task_id, "md5_name", md5_name)
        set_task_attribute(task_id, "convert_type", convert_type)

        print(f"*** Converting {filename} to {convert_type} ***", file=sys.stderr)

        match convert_type:
            case "text":
                server.add_background_task(
                    pdf_processing.async_pdf2json,
                    server,
                    filename,
                    md5_name,
                    task_id,
                    request.remote_addr,
                )
            case "flashcards":
                server.add_background_task(
                    pdf_processing.async_json2flashcards,
                    server,
                    filename,
                    md5_name,
                    task_id,
                )
            case "keywords":
                server.add_background_task(
                    pdf_processing.async_json2keywords,
                    server,
                    filename,
                    md5_name,
                    task_id,
                )
            case "test":
                server.add_background_task(
                    pdf_processing.async_json2test,
                    server,
                    filename,
                    md5_name,
                    task_id,
                    conversion_options,
                )
            case _:
                set_task_status("error")
                return "Error processing the request"

        # Return the task ID to the client
        return jsonify({"task_id": task_id})

    except Exception as e:
        print("Error:", str(e), file=sys.stderr)
        return "Error processing the request"


@server.route("/results", methods=["GET"])
async def results():
    return await render_template(
        "results.html",
        last_updated=dir_last_updated("./src/static"),
    )


if __name__ == "__main__":
    server.run()
