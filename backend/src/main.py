import sys
import os
import openai
import hashlib
import uuid
import json
import stripe
from .async_actions import exporter
from .async_actions import document_processing, pdf_processing, pptx_processing
from .async_actions.async_task import set_task_status, set_task_attribute, running_tasks
from quart import (
    Quart,
    Request,
    render_template,
    flash,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file,
    abort,
)
from quart_session import Session
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from .database import DBManager

import traceback
from datetime import datetime

UNSTRUCTUED_API_URL = "http://unstructured-api:8000/general/v0/general"
OPENAI_API_KEY = "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"
UPLOAD_FOLDER = "./data/file-upload"
JSON_FOLDER = "./data/file-json"
PROCESSED_FOLDER = "./data/file-processed"
LOG_FOLDER = "./data/file-log"
METADATA_FOLDER = "./data/file-metadata"
EXPORT_FOLDER = "./data/exports"
ALLOWED_EXTENSIONS = {"pdf", "pptx"}
CONCURRENT_TEXT_PROCESS_LIMIT = (
    2  # How many files unstructured API can handle at a time.
)
SUPPORT_EMAIL = "???@???.com"


# Configure quart
server = Quart(__name__)
server.config["UNSTRUCTUED_API_URL"] = UNSTRUCTUED_API_URL
server.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
server.config["JSON_FOLDER"] = JSON_FOLDER
server.config["PROCESSED_FOLDER"] = PROCESSED_FOLDER
server.config["LOG_FOLDER"] = LOG_FOLDER
server.config["EXPORT_FOLDER"] = EXPORT_FOLDER
server.config["METADATA_FOLDER"] = METADATA_FOLDER
server.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15mb
server.config["CONCURRENT_TEXT_PROCESS_LIMIT"] = CONCURRENT_TEXT_PROCESS_LIMIT
server.config["SUPPORT_EMAIL"] = SUPPORT_EMAIL
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
        max(
            os.path.getmtime(os.path.join(root_path, f))
            for root_path, _, files in os.walk(folder)
            for f in files
        )
    )


def get_file_extension(filename: str):
    return filename.rsplit(".", 1)[-1].lower()


def allowed_file(filename: str):
    return "." in filename and get_file_extension(filename) in ALLOWED_EXTENSIONS


# Returns account type (guest, free, paid)
def get_acount_type() -> str:
    if session.get("logged_in"):
        if session.get("card_connected"):
            return "paid"
        else:
            return "free"

    return "guest"


def get_file_metadata(md5_name, key):
    metadata_folder = server.config["METADATA_FOLDER"]

    metadata_file_path = os.path.join(metadata_folder, f"{md5_name}.json")

    if os.path.exists(metadata_file_path):
        with open(metadata_file_path, "r") as metadata_file:
            metadata = json.load(metadata_file)
            return metadata.get(key, None)
    else:
        return None


# Returns the invoice amount and due date.
def get_customer_invoice():
    print(f"{session.get('card_connected')} !!!!!!!!!!!!!!!", file=sys.stderr)
    if not session.get("card_connected"):
        return (None, None)

    database = DBManager(pass_file="/run/secrets/db-password")
    customer_id = database.get_stripe_user_id(session.get("email"))

    # response = database.run_query(f"SELECT subscription_item_id FROM stripe_users WHERE user_id = '{customer_id}'")
    # subscription_item_id = response[0]

    response = database.run_query(
        f"SELECT subscription_id FROM stripe_users WHERE user_id = '{customer_id}'"
    )
    subscription_id = response[0]

    if not subscription_id:
        return (None, None)

    subscription = stripe.Subscription.retrieve(subscription_id)

    # Retrieve upcoming invoice
    upcoming_invoice = stripe.Invoice.upcoming(subscription=subscription_id)

    # Calculate the next charge date based on the current period end date
    current_period_end = subscription.current_period_end
    next_charge_date = datetime.fromtimestamp(current_period_end)

    # Format the next charge date
    next_charge_date_str = next_charge_date.strftime("%m/%d/%Y")

    print(upcoming_invoice, file=sys.stderr)
    return (next_charge_date_str, upcoming_invoice.amount_due)


async def upload_file(request: Request):
    files_dict = await request.files
    # print(files_dict, file=sys.stderr)

    if "file" not in files_dict:
        flash("No file part")
        return redirect(request.url)

    files = [file for file in files_dict.getlist("file")]

    # Get a list of files from request.files, should always be 1 file at a time.
    if len(files) != 1:
        return jsonify({"success": False})

    file: FileStorage = files[0]

    if not file or not allowed_file(file.filename):
        return jsonify({"success": False, "error_type": "file_denied"})

    file_extension = get_file_extension(file.filename)
    number_of_pages = -1
    match file_extension:
        case "pdf":
            number_of_pages = pdf_processing.get_pages(file)
        case "pptx":
            number_of_pages = pptx_processing.get_pages(file)
        case _:
            None

    print(f"Extension: {file_extension}", file=sys.stderr)
    account_type = get_acount_type()

    if number_of_pages > 3 and account_type == "guest":
        return jsonify({"success": False, "error_type": "page_limit"})
    if number_of_pages > 10 and account_type == "free":
        return jsonify({"success": False, "error_type": "page_limit"})

    print(
        "User uploaded document: {}".format(file.filename),
        file=sys.stderr,
    )
    # Create /file-upload directory if it doesn't exist.
    if not os.path.exists(server.config["UPLOAD_FOLDER"]):
        os.makedirs(server.config["UPLOAD_FOLDER"])

    # Create /file-metadata directory if it doesn't exist.
    if not os.path.exists(server.config["METADATA_FOLDER"]):
        os.makedirs(server.config["METADATA_FOLDER"])

    file_contents = file.stream.read()
    # Compute the MD5 hash of the contents
    md5_name = hashlib.md5(file_contents).hexdigest()
    filename = secure_filename(file.filename).replace(f".{file_extension}", "")

    file.filename = f"{md5_name}.{file_extension}"

    # Save the file's metadata to the filesystem
    # TODO: Save IP of user who uploaded.
    metadata = {
        "file_name": filename,
        "md5_name": md5_name,
        "page_count": number_of_pages,
        "extension_type": file_extension,
    }

    metadata_file_path = os.path.join(
        server.config["METADATA_FOLDER"], f"{md5_name}.json"
    )
    with open(metadata_file_path, "w") as metadata_file:
        json.dump(metadata, metadata_file)

    # Release the pointer that reads the file so we can save it properly
    file.stream.seek(0)
    # FIXME: Check if file already exists, if so dont bother saving it again.
    await file.save(os.path.join(server.config["UPLOAD_FOLDER"], file.filename))

    return (
        jsonify({"success": True, "metadata": metadata}),
        200,
        {"ContentType": "application/json"},
    )


@server.route("/", methods=["GET", "POST"])
async def home():
    if request.method == "POST":
        return await upload_file(request)

    return await render_template(
        "index.html", last_updated=dir_last_updated("./src/static")
    )


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
                "register.html",
                last_updated=dir_last_updated("./src/static"),
                error_msg="Passwords do not match",
            )

        database = DBManager(pass_file="/run/secrets/db-password")
        response, error_msg = database.add_user(email, password)

        if response != 0:
            return await render_template(
                "register.html",
                last_updated=dir_last_updated("./src/static"),
                error_msg=error_msg,
            )

        return redirect(url_for("login"))

    return await render_template(
        "register.html", last_updated=dir_last_updated("./src/static")
    )


@server.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form_data = await request.form
        form_dict = dict(form_data)
        email = form_dict.get("email")
        password = form_dict.get("password")

        # VERY IMPORTANT FUNCTION, IF REMOVED ANYONE CAN LOG IN!!!
        if not password or len(password) < 1:
            return redirect("/")

        # Check if the email and password match a user in the database
        database = DBManager(pass_file="/run/secrets/db-password")
        db_user_obj, error_msg = database.get_user(email, password)
        # print(db_user_obj, file=sys.stderr)

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
                "login.html",
                last_updated=dir_last_updated("./src/static"),
                error_msg=error_msg,
            )
    return await render_template(
        "login.html", last_updated=dir_last_updated("./src/static")
    )


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

    # FIXME: get_customer_invoice() is slow, use cache w/ session.() and talk to our DB.
    charge_date, amount = get_customer_invoice()

    return await render_template(
        "profile.html",
        last_updated=dir_last_updated("./src/static"),
        charge_date=charge_date,
        amount=amount,
    )


@server.route("/checkout/return", methods=["GET"])
async def handle_checkout_session():
    # Reference: https://stripe.com/docs/payments/save-and-reuse?platform=web&ui=embedded-checkout#set-up-stripe
    session_id = request.args.get("session_id")

    # print(session_id, file=sys.stderr)
    # Retrieve checkout session
    checkout_session = stripe.checkout.Session.retrieve(session_id)

    # Retrieve the setup intent
    setup_intent = stripe.SetupIntent.retrieve(checkout_session.setup_intent)

    database = DBManager(pass_file="/run/secrets/db-password")

    customer = None

    # Create/fetch stripe customer
    stripe_user_id = database.get_stripe_user_id(session.get("email"))
    if not stripe_user_id:
        customer = stripe.Customer.create(
            email=session.get("email"), description="From PDF2Flashcards backend"
        )
        database.add_stripe_customer(customer)
        stripe_user_id = customer.id
    else:
        customer = stripe.Customer.retrieve(stripe_user_id)
    # else:
    #    print("!!!!!!!! RETRIEVE", file=sys.stderr)
    #    customer = stripe.Customer.retrieve(stripe_user_id)

    # FIXME: Ensure that stripe actually has a user_id here, our DB might get fucked.

    # Remove any existing payment methods (condition where user is replacing their card)
    payment_methods_json = customer.list_payment_methods()["data"]

    for payment_method in payment_methods_json:
        stripe.PaymentMethod.detach(payment_method["id"])

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

    billing_cycle_anchor_config = {
        "day_of_month": 1,
        "hour": 12,
        "minute": 30,
        "second": 0,
    }

    # Create a new subscription for the user, if one doesn't exist already.
    existing_subscriptions = stripe.Subscription.list(customer=stripe_user_id)
    if len(existing_subscriptions["data"]) <= 0:
        subscription = stripe.Subscription.create(
            customer=stripe_user_id,
            items=[{"price": stripe_keys["product_id"]}],
            billing_cycle_anchor_config=billing_cycle_anchor_config,
        )
        # Assuming subscription is a Stripe Subscription object
        subscription_item_id = subscription["items"]["data"][0]["id"]

        # Assign the subscription_id and subscription_item_id to our stripe_users table
        database.assign_user_subscriptions(
            stripe_user_id, subscription.id, subscription_item_id
        )

    # Update users table & set card_connected to True
    database.set_card_connected(session.get("email"), True)
    session["card_connected"] = True

    # Go back to user profile
    return redirect(url_for("profile"))


@server.route("/create-checkout-session", methods=["POST"])
async def create_checkout_session():
    return_url = request.url_root + "checkout/return?session_id={CHECKOUT_SESSION_ID}"
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
    return await render_template(
        "add-payment.html",
        last_updated=dir_last_updated("./src/static"),
        stripe_pk=stripe_keys["public"],
    )


@server.route("/remove-payment", methods=["POST"])
async def remove_payment():
    database = DBManager(pass_file="/run/secrets/db-password")
    customer_id = database.get_stripe_user_id(session.get("email"))
    payment_method_json = stripe.Customer.list_payment_methods(customer_id, limit=1)
    payment_id = payment_method_json["data"][0]["id"]

    # Charge the stripe customer if they have a balance > 0.5
    _, amount = get_customer_invoice()
    print(f"Amount: {amount}")
    if amount >= 50:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            customer=customer_id,
            payment_method=payment_id,
        )
        return_url = request.url_root + "/profile"
        # Confirm the payment intent
        payment_result = stripe.PaymentIntent.confirm(
            intent["id"], return_url=return_url
        )
        print(payment_result, file=sys.stderr)

    # Cancel the subscription & detach the card from the customer.
    stripe.Subscription.cancel(database.get_user_subscription_id(customer_id))
    stripe.PaymentMethod.detach(payment_id)

    # Set our card connected to false.
    database.run_query(
        f"UPDATE users SET card_connected = 0 WHERE email='{session.get('email')}'"
    )
    session["card_connected"] = False

    return jsonify({"success": True, "return_url": return_url})


@server.route("/manage-payment", methods=["GET"])
async def manage_payment():
    # Get user card from stripe
    database = DBManager(pass_file="/run/secrets/db-password")
    customer_id = database.get_stripe_user_id(session.get("email"))

    if not customer_id:
        return redirect(url_for("profile"))

    payment_method_json = stripe.Customer.list_payment_methods(customer_id, limit=1)

    if len(payment_method_json["data"]) <= 0:
        return redirect(url_for("profile"))

    customer_card = payment_method_json["data"][0]["card"]
    _, amount_due = get_customer_invoice()

    return await render_template(
        "manage-payment.html",
        last_updated=dir_last_updated("./src/static"),
        stripe_pk=stripe_keys["public"],
        customer_card=customer_card,
        amount_due=amount_due,
    )


@server.route("/help", methods=["GET"])
async def help():
    return await render_template(
        "help.html",
        last_updated=dir_last_updated("./src/static"),
        support_email=server.config["SUPPORT_EMAIL"],
    )


@server.route("/flashcard_test", methods=["GET"])
async def flashcard_test():
    return await render_template(
        "flashcard_test.html", last_updated=dir_last_updated("./src/static")
    )


@server.route("/flashcard", methods=["GET"])
async def flashcard():
    return await render_template(
        "flashcard.html", last_updated=dir_last_updated("./src/static")
    )


@server.route("/prompt", methods=["GET"])
async def prompt():
    return await render_template(
        "prompt.html", last_updated=dir_last_updated("./src/static")
    )


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
        "export-flashcard.html",
        filename=filename,
        md5_name=md5_name,
        last_updated=dir_last_updated("./src/static"),
    )


@server.route("/export-keyword", methods=["GET"])
async def export_keyword():
    filename = request.args.get("filename")
    md5_name = request.args.get("md5_name")
    return await render_template(
        "export-keyword.html",
        filename=filename,
        md5_name=md5_name,
        last_updated=dir_last_updated("./src/static"),
    )


@server.route("/export-test", methods=["GET"])
async def export_test():
    filename = request.args.get("filename")
    md5_name = request.args.get("md5_name")
    return await render_template(
        "export-test.html",
        filename=filename,
        md5_name=md5_name,
        last_updated=dir_last_updated("./src/static"),
    )


# Get the export file of the associated <file> name.
@server.route("/export/<file>", methods=["GET"])
async def get_exported_document(file):
    export_folder = server.config["EXPORT_FOLDER"]
    file_path = f"{export_folder}/{file}"
    try:
        return await send_file(file_path, as_attachment=False)
    except FileNotFoundError:
        abort(404, f"File {file} not found")


@server.route("/export", methods=["POST"])
async def export_results():
    request_form = await request.form
    try:
        # file_name = request_form.get("file_name")
        md5_name = request_form.get("md5_name")
        conversion_type = request_form.get("conversion_type")
        export_type = request_form.get("export_type")
        flashcard_sets_str = request_form.get("flashcard_sets")

        if len(flashcard_sets_str) <= 0:
            return {"error": "Empty flashcard sets"}

        flashcard_sets = [int(item) for item in flashcard_sets_str.split(",")]

        # Generate a unique task ID, set it as processing
        task_id = str(uuid.uuid4())
        # Generate a unique  file_id, this will be the name of the exported file.
        file_id = str(uuid.uuid4())
        set_task_status(task_id, "processing")

        # Begin the export process
        match conversion_type:
            case "flashcards":
                server.add_background_task(
                    exporter.export_flashcard,
                    server,
                    task_id,
                    file_id,
                    md5_name,
                    export_type,
                    flashcard_sets,
                )
            case _:
                set_task_status(task_id, "error")
                return {"error": "No export option for conversion type"}

        return jsonify(
            {"task_id": task_id, "file_id": file_id, "export_type": export_type}
        )
    except Exception as e:
        error_message = (
            f"Error: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0].lineno}"
        )
        print(error_message, file=sys.stderr)
        set_task_status(task_id, "error")
        return {"error": error_message}


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
                            {
                                "error": f"Conversion type '{conversion_type}' not found",
                                "error_type": "no_conversion",
                            }
                        ),
                        400,
                    )
        except FileNotFoundError:
            return jsonify(
                {"error": f"File '{file_path}' not found", "error_type": "no_file"}
            ), 404
        except Exception as e:
            return jsonify({"error": f"Error: {str(e)}", "error_type": "unknown"}), 500
    else:
        return jsonify(
            {"error": "Missing parameters", "error_type": "missing_params"}
        ), 400


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

        # FIXME: Get extension_type from md5 metadata
        extension_type: str = get_file_metadata(md5_name, "extension_type")

        match convert_type:
            case "text":
                server.add_background_task(
                    document_processing.async_document2json,
                    server,
                    filename,
                    md5_name,
                    extension_type,
                    task_id,
                    request.remote_addr,
                )
            case "flashcards":
                server.add_background_task(
                    document_processing.async_json2flashcards,
                    server,
                    filename,
                    md5_name,
                    task_id,
                )
            case "keywords":
                server.add_background_task(
                    document_processing.async_json2keywords,
                    server,
                    filename,
                    md5_name,
                    task_id,
                )
            case "test":
                server.add_background_task(
                    document_processing.async_json2test,
                    server,
                    filename,
                    md5_name,
                    task_id,
                    conversion_options,
                )
            case _:
                set_task_status(task_id, "error")
                return {"error:": "No convert_type found."}

        # Update the pages_processed for the user, if they exist
        page_count: int = get_file_metadata(md5_name, "page_count")
        if page_count > 10 and convert_type != "text" and session.get("logged_in"):
            pages_processed = (
                page_count - 10
            )  # Numbers of pages we are to charge the user (first 10 are free)
            database = DBManager(pass_file="/run/secrets/db-password")
            database.add_pages_processed(session.get("email"), pages_processed)

        # Return the task ID to the client
        return jsonify({"task_id": task_id})

    except Exception as e:
        error_message = (
            f"Error: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0].lineno}"
        )
        print(error_message, file=sys.stderr)
        return {"error:": error_message}


@server.route("/results", methods=["GET"])
async def results():
    return await render_template(
        "results.html",
        last_updated=dir_last_updated("./src/static"),
    )


# Retrieve the status of a specific task
@server.route("/task_status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    task = running_tasks.get(task_id)

    if task is None:
        return {}

    return task.get_status_json()


if __name__ == "__main__":
    server.run()
