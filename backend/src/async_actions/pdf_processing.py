import json
from quart import Quart
import tiktoken
import sys
import os, sys
import aiohttp
import asyncio
import openai
import logging
import traceback
from .async_task import set_task_status, set_task_progress, set_task_attribute
import re
from filelock import FileLock

GPT_MODEL = "gpt-3.5-turbo-1106"
pdf2json_processes = 0


def text_has_table_expression(text):
    """
    Check if the text has the pattern: 'Table xx.xx'.
    """
    pattern = r"Table \d+\.\d+"
    return bool(re.search(pattern, text))


def text_has_multiple_choice(text: str) -> bool:
    """
    Check if text has A) B) C) D) options
    """
    open_p_count = 0
    # FIXME: Check letter prefix.
    for i in range(0, len(text)):
        character = text[i]
        if character == "(":
            open_p_count += 1
        if character == ")":
            open_p_count -= 1

    return open_p_count < 0


def get_logger_for_file(server: Quart, md5_name: str) -> logging.Logger:
    if not os.path.exists(server.config["LOG_FOLDER"]):
        os.makedirs(server.config["LOG_FOLDER"])

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    logger_file = logging.FileHandler(f'{server.config["LOG_FOLDER"]}/{md5_name}.txt')
    logger_file.setLevel(logging.DEBUG)
    logger_file.setFormatter(formatter)

    logger = logging.getLogger(f"pdf-logs")
    new_logger = False
    if logger.hasHandlers():
        logger.handlers.clear()
    else:
        new_logger = True

    logger.setLevel(logging.DEBUG)
    logger.addHandler(logger_file)

    if new_logger:
        logger.info("================================= BEGINNING OF LOGGING SESSION =================================")

    return logger


def truncate2gpt_tokens(server: Quart, md5_name: str, pdf_text: str, just_split_pages=False):
    """
    Given a pdf_text string (Has the formatted page numbers), return a list of text under the 4096 token limit for chat-gpt
    """
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: truncate2gpt_tokens")

    # Split the input string into sections based on "===page:" pattern
    sections = pdf_text.split("===Page:")
    current_page = -1
    page_sections = []
    # Iterate through the sections
    for section in sections[1:]:  # Start from index 1 to skip the first empty section
        page = int(section.split("=")[0])
        # print(page)
        # print(repr(f"{section}"))
        # If were onto a new page, increment our page sections list.
        if current_page != page:
            current_page = page
            page_sections.append("")

        section = "===Page:" + section

        page_sections[-1] += section

    logger.debug(f"Page sections w/ length of: {len(page_sections)}")
    logger.debug(page_sections)

    if just_split_pages:
        return page_sections

    # Count the number of tokens for each page. Include what can be fit into our 4096 context for each string in the list.
    # FIXME: ACCOUNT FOR PDFs WHERE A SINGLE PAGE > 4096 TOKENS!!!!!!!!!!!!!!!
    # NOTE: Right now we use 1000 tokens to keep gpt accurate and consise for our information provided.
    truncated_pdf_text = []
    current_tokens = 0
    total_tokens = 0
    encoding = tiktoken.encoding_for_model(GPT_MODEL)
    for section in page_sections:
        num_tokens = len(encoding.encode(section))

        if num_tokens + current_tokens >= 1000 or len(truncated_pdf_text) < 1:
            truncated_pdf_text.append("")
            total_tokens += current_tokens
            current_tokens = 0

        truncated_pdf_text[-1] += section
        current_tokens += num_tokens

    logger.debug(f"Number of tokens used for pdf text: {total_tokens}")
    return truncated_pdf_text


# Get tokens from pdf elements and merge them onto a single line.
def merge_pdf_json_elements(elements):
    # List of all elements with an expanded bounding box.
    formatted_text = ""
    for element in elements:
        text = element["text"]
        if text[0].isupper():
            formatted_text += f"\n{text}"  # FIXME: Dont add newline if this is our first element on the page!
        else:
            formatted_text += f"{text} "

    return formatted_text.rstrip()


# Parses the json file & creates a formatted .txt file of the PDF for ChatGPT to read.
def json2text(server: Quart, md5_name: str):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: json2text")

    with open(f'{server.config["JSON_FOLDER"]}/{md5_name}.json', "r") as file:
        json_data = json.load(file)

        # 1. Skip any uncessary json_items (page breaks, empty text, duplicate tokens)
        truncated_json_data = []
        existing_text_tokens = []
        for json_item in json_data:
            # Skip any page breaks, empty text, or duplicate text tokens.
            if json_item["type"] == "PageBreak":
                continue

            item_text: str = json_item["text"]

            if len(item_text) < 1:
                continue

            # FIXME: TEST IF THIS STATEMENT MESS UP OUR RESPONSES!! (MIGHT REMOVE IMPORTANT DATA??)
            if item_text in existing_text_tokens:
                continue

            truncated_json_data.append(json_item)
            existing_text_tokens.append(json_item["text"])

        # 2.  Remove page numbers from our data (But not the other important ones!)
        # List of json_items that are numbers. We check theses lists against each other & remove page numbers
        prev_numbers_on_page = []
        numbers_on_page = []

        # List of all json_items that we suspect are page numbers
        page_number_json_items = []
        current_page = 0
        for index, json_item in enumerate(truncated_json_data):
            item_page_number = json_item["metadata"]["page_number"]
            item_text = json_item["text"]

            # Ensure we check the last json_item number before going into that if-conditon below
            if index == len(truncated_json_data) - 1 and item_text.isdigit():
                numbers_on_page.append(json_item)

            if item_page_number != current_page or index == len(truncated_json_data) - 1:
                current_page = item_page_number

                # Compare prev_numbers_on_page w/ numbers_on_page, if we see a +1 increment b/w them, append both to page_number_json_items
                for prev_json_digit_item in prev_numbers_on_page:
                    for json_digit_item in numbers_on_page:
                        if int(json_digit_item["text"]) - 1 == int(prev_json_digit_item["text"]):
                            if prev_json_digit_item not in page_number_json_items:
                                page_number_json_items.append(prev_json_digit_item)
                            if json_digit_item not in page_number_json_items:
                                page_number_json_items.append(json_digit_item)

                prev_numbers_on_page = list(numbers_on_page)
                numbers_on_page.clear()

            # Add any digits found to numbers_on_page
            if item_text.isdigit():
                numbers_on_page.append(json_item)

        logger.debug(f"Page number elements found (and to remove): {len(page_number_json_items)}")
        logger.debug(f"Removing page #'s: Length of BEFORE json_data: {len(truncated_json_data)}")
        truncated_json_data = [
            json_item for json_item in truncated_json_data if json_item not in page_number_json_items
        ]
        logger.debug(f"Removing page #'s:  Length of AFTER json_data: {len(truncated_json_data)}")

        # 3.  Generate formatted text from our pre-processed json-elements
        formatted_text = ""
        current_page = 0
        page_elements = []
        for json_item in truncated_json_data:
            item_page_number = json_item["metadata"]["page_number"]

            if item_page_number != current_page:
                # End the current page block
                if current_page != 0:
                    # Before ending the page block, format our page elements and append them to the page.
                    formatted_text += merge_pdf_json_elements(page_elements)
                    formatted_text += f"\n===Page:{current_page}===\n"
                    page_elements.clear()

                # Start the new page block
                formatted_text += f"===Page:{item_page_number}===\n"
                current_page = item_page_number

            # Append json_item elements to the current page
            page_elements.append(json_item)

    # End the current page block since were finished parsing, along with it's json elements.
    formatted_text += merge_pdf_json_elements(page_elements)
    formatted_text += f"\n===Page:{current_page}===\n"

    return formatted_text


async def gpt_generate_test_questions(server, md5_name, data, conversion_options: dict):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: gpt_generate_test_questions")

    # print(f"*********************** Generate Test Questions from text chunk:\n{data}")
    logger.debug(f"*********************** Generate Test Questions from text chunk:\n{data}")

    prompt_values = {
        "test_multiple_choice": "Multiple Choice (Include letter options in questions or DEATH happens!!!). Multiple Choice Strict Format Example:\nWhich of the following is not a primary color? A) Red B) Yellow C) Green D) Purple -- Answer: D) Purple",
        "test_true_false": "True/False Questions",
        "test_free_response": "Free Response",
    }

    prompt_options = ""
    for index, conversion_option in enumerate(conversion_options["test"]):
        prompt_options += f"{prompt_values[conversion_option]}\n"

    prompt = f"Create a very large amount test/quiz questions from data using the following question type(s):\n{prompt_options}\nYour responses should strictly follow this format:\n** [question_type] -- Question: [question] -- Answer: [answer]\nThe provided data is as follows:\n{data}"

    response = await openai.ChatCompletion.acreate(
        model=GPT_MODEL,
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    response_data: str = response["choices"][0]["message"]["content"]
    # print(response_data, file=sys.stderr)

    test_questions = response_data.split("\n")
    # Remove empty lines
    test_questions = [test_question for test_question in test_questions if test_question != ""]

    new_test_questions = []
    existing_questions = []
    existing_answers = []

    # FIXME: Respones can be in like respeonse-scenario-a.txt, account for that before splitting our questions here.#
    # Solution: Correct the formatting such that the code below works as intended.
    # question = split_question[1].strip() throws an out of bound error in this scenario.

    for test_question in test_questions:
        # print(f"TEST QUESTION: {test_question}", file=sys.stderr)
        split_question = test_question.split("--")
        question_type = split_question[0].split("**", 1)[1].strip()
        question = split_question[1].strip()
        answer = split_question[2].strip()

        # Edgecase: Remove trailing ** if it exists. It's an artifact from GPT.
        if answer.endswith("**"):
            answer = answer.rstrip("*")

        if question_type.endswith("**"):
            question_type = question_type.rstrip("*")

        if question in existing_questions or answer in existing_answers:
            continue

        # Edgecase: Remove example Q&A if present, it somtimes gets generated by the GPT prompt.
        if "a primary color" in question:
            continue

        # Edgecase: If the question references a table (e.g. Table 4.12), remove it since we cant see it.
        # FIXME: Somehow get a screenshot of the table in the future?
        if text_has_table_expression(question):
            continue

        # Edgecase: Correct question_type if answer is of true false, yet question_type is multiple choice.
        if (answer == "Answer: False" or answer == "Answer: True") and "Multiple Choice" in question_type:
            if not text_has_multiple_choice(question):
                question_type = "True/False"

        # Edgecase: Include letter options for True/False if not present.
        if "True/False" in question_type and "A) True" not in question:
            question += "\nA) True\nB) False"
            if "True" in answer:
                answer = "Answer: A) True"
            elif "False" in answer:
                answer = "Answer: B) False"

        # Edgecase: Add newline fomatting for multiple choice questions after each letter option
        if "Multiple Choice" in question_type:
            string_list = list(question)
            string_list_copy = list(string_list)
            opened_p_count = 0
            added_characters = 0
            for i in range(0, len(string_list_copy)):
                character = string_list_copy[i]

                if character == "(":
                    opened_p_count += 1

                if character == ")" and opened_p_count <= 0:
                    string_list.insert(i - 1 + added_characters, "\n")
                    added_characters += 1
                elif character == ")" and opened_p_count > 0:
                    opened_p_count -= 1

            question = "".join(string_list)

        # Edgecase: Remove 'Question:' 'Answer:' substrings - They can be implemented clientside.
        question = question.replace("Question: ", "", 1)
        answer = answer.replace("Answer: ", "", 1)

        new_test_questions.append([question_type, question, answer])
        existing_questions.append(question)
        existing_answers.append(answer)

    return new_test_questions


async def gpt_generate_definitions(server, md5_name, data):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: gpt_generate_definitions")

    # print(f"*********************** Generate Definitions from text chunk:\n{data}")
    logger.debug(f"*********************** Generate Definitions from text chunk:\n{data}")

    prompt = f"Please analyze the data and provide 'keyword: definition' pairs relevant for study. Your responses should strictly follow this format without numbering:\nKeyword: Definition\nDo NOT include the words 'Keyword' or 'Definition' in the output. The provided data is as follows:\n{data}"

    response = await openai.ChatCompletion.acreate(
        model=GPT_MODEL,
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    response_data: str = response["choices"][0]["message"]["content"]
    definition_pairs = response_data.split("\n")
    definition_pairs = [definition for definition in definition_pairs if definition != ""]

    new_definition_pairs = []
    existing_definitions = []
    existing_keywords = []

    for definition_pair in definition_pairs:
        if ":" not in definition_pair:
            continue
        keyword = definition_pair.split(":", 1)[0].strip()
        definition = definition_pair.split(":", 1)[1].strip()

        if keyword in existing_keywords or definition in existing_definitions:
            continue

        # Edgecase: If definition references a table (e.g. Table 4.12), remove it since we can't see it.
        if text_has_table_expression(definition):
            continue

        existing_definitions.append(definition)
        existing_keywords.append(keyword)
        new_definition_pairs.append([keyword, definition])
        # print(f"Keyword: '{keyword}' - Definition: '{definition}'", file=sys.stderr)

    definition_pairs = new_definition_pairs

    return definition_pairs


async def gpt_generate_qa(server, md5_name, data):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: gpt_generate_qa")

    # print(f"*********************** Generate Q&A from text chunk:\n{data}")
    logger.debug(f"*********************** Generate Q&A from text chunk:\n{data}")

    prompt = f"Generate brief, clever Q&A flashcards each page from the following UNORDERED tokens. Generate very short questions and answers, as these are meant to be flashcards. Only respond with: 'Q: ... [NEWLINE] A: ...' Here is the provided data:\n{data}"

    response = await openai.ChatCompletion.acreate(
        model=GPT_MODEL,
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    response_data: str = response["choices"][0]["message"]["content"]

    # Edgecase: Sometimes GPT returns Q&A set with [NEWLINE] instead of '\n'. Handle it accordingly.
    response_data = response_data.replace("[NEWLINE]", "\n")

    # print("*********************** GPT Q&A RESPONSE DATA:")
    logger.debug("*********************** GPT Q&A RESPONSE DATA:")

    # print(response_data)
    logger.debug(response_data)

    # Edgecase: ??? Forgot. my bad.
    if "Q2A: None" in response_data:
        return None

    qa_sets = response_data.split("\n")
    qa_sets = [qa_set for qa_set in qa_sets if qa_set != ""]

    if len(qa_sets) % 2 != 0:
        print("!!! WARNING: UNEVEN Q&A RESPONSE (mssing q or a, or additional output.)!!!", file=sys.stderr)
        logger.warn("UNEVEN Q&A RESPONSE (mssing q or a)!!")

    # Remove any lines not containing Q: or A:.
    qa_sets = [line for line in qa_sets if "Q:" in line or "A:" in line]

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

        # Edgecase: If the question references a table (e.g. Table 4.12), remove it since we cant see it.
        # FIXME: Somehow get a screenshot of the table in the future?
        if text_has_table_expression(question):
            continue

        # Edgecase: Remove any 'Q: ' 'A: ' substrings. We want to append these client-side.
        question = question.replace("Q: ", "")
        answer = answer.replace("A: ", "")

        new_qa_sets.append([question, answer])
        existing_questions.append(question)
        existing_answers.append(answer)

    qa_sets = new_qa_sets

    # Return a list with a nested list of two elements (Q/A)
    return qa_sets


async def async_pdf2json(
    server: Quart,
    filename: str,
    md5_name: str,
    task_id: str,
    ip_address: str,
):
    global pdf2json_processes

    logger: logging.Logger = get_logger_for_file(server, md5_name)
    process_limit = server.config["CONCURRENT_TEXT_PROCESS_LIMIT"]
    try:
        # Check if the variables are received correctly
        logger.info("Function: async_pdf2json")
        print(f"Uploader: {ip_address}", file=sys.stderr)
        # logger.debug(f"Uploader: {ip_address}")
        logger.debug(f"Received filename: {filename}")
        logger.debug(f"Received md5_name: {md5_name}")

        pdf_file_path = f'{server.config["UPLOAD_FOLDER"]}/{md5_name}.pdf'
        json_file_path = f'{server.config["JSON_FOLDER"]}/{md5_name}.json'

        # Check if the pdf file exists, if not return and set the task status to 'error':
        if not os.path.isfile(pdf_file_path):
            logger.debug(f"Error: PDF file does not exist: {filename}")
            set_task_status(task_id, "error")
            set_task_attribute(
                task_id, "error_msg", "Error: Unable to find uploaded PDF file. Try uploading the file again."
            )
            set_task_attribute(task_id, "error_type", "no_file")
            return

        # Check if file already exists, if so, set the task status as completed:
        if os.path.isfile(json_file_path):
            logger.debug(f"JSON already exists for {filename}, returning...")
            set_task_status(task_id, "completed")
            return

        form_data = aiohttp.FormData()
        form_data.add_field("files", open(pdf_file_path, "rb"))
        form_data.add_field("encoding", "utf_8")
        form_data.add_field("include_page_breaks", "true")  # FIXME: Not needed?
        form_data.add_field("coordinates", "false")
        # form_data.add_field("strategy", "auto")
        # form_data.add_field("hi_res_model_name", "detectron2_onnx")

        headers = {"accept": "application/json"}

        # Wait until process_limit goes back down
        while pdf2json_processes >= process_limit:
            await asyncio.sleep(1)

        pdf2json_processes += 1

        async with aiohttp.ClientSession() as session:
            async with session.post(server.config["UNSTRUCTUED_API_URL"], headers=headers, data=form_data) as response:
                if response.status == 200:
                    response_text = await response.text()
                    # TODO: Implement a keep-alive loop & cancel these post requests if terminated.
                    # FIXME: Handle any errors thrown by unstructured api.

                    # Create /pdf-json directory if it doesn't exist.
                    if not os.path.exists(server.config["JSON_FOLDER"]):
                        os.makedirs(server.config["JSON_FOLDER"])

                    with open(f'{server.config["JSON_FOLDER"]}/{md5_name}.json', "w") as file:
                        file.write(response_text)
                        set_task_status(task_id, "completed")
                        pdf2json_processes -= 1
                else:
                    await asyncio.sleep(1)
                    logger.error(response.text)
                    print(response.text, file=sys.stderr)
                    set_task_status(task_id, "error")
                    pdf2json_processes -= 1

    except Exception as e:
        # Handle exceptions or errors here
        print("Error:", str(e), file=sys.stderr)
        logger.error(str(e))
        logger.error(traceback.format_exc())
        set_task_status(task_id, "error")


async def async_json2test(server: Quart, filename: str, md5_name: str, task_id: str, conversion_options: dict):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: async_json2test")

    try:
        # Create directory if it doesn't exist.
        os.makedirs(server.config["PROCESSED_FOLDER"], exist_ok=True)
        processed_file = f'{server.config["PROCESSED_FOLDER"]}/{md5_name}.json'

        with FileLock(f"{processed_file}.lock"):
            # Check if file already exists and test questions for it was generated, if so, set the task status as completed
            if os.path.isfile(processed_file):
                with open(processed_file, "r") as file:
                    if "test" in json.load(file):
                        # TODO: Apply conversion_options in the JSON, check if they match and re-do it if not.
                        logger.debug(f"Test already exists for {filename}, returning...")
                        set_task_status(task_id, "completed")
                        return

        pdf_text = json2text(server, md5_name)

        logger.debug("JSON text (converted from JSON): ")
        logger.debug(pdf_text)

        truncated_pdf_text = truncate2gpt_tokens(server, md5_name, pdf_text, just_split_pages=False)
        logger.debug(f"Length of truncated_pdf_text: {len(truncated_pdf_text)}")

        generated_test_questions = []
        for index, text_chunk in enumerate(truncated_pdf_text):
            test_questions = await gpt_generate_test_questions(server, md5_name, text_chunk, conversion_options)
            if test_questions is None:
                continue
            generated_test_questions = generated_test_questions + test_questions
            set_task_progress(task_id, float(index + 1) / float(len(truncated_pdf_text)))

        append_json_value_to_file(processed_file, "test", generated_test_questions)
        set_task_status(task_id, "completed")
        logger.debug("Test Generation Successful.")

    except Exception as e:
        error_message = f"Error: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0].lineno}"
        print(error_message, file=sys.stderr)
        logger.error(error_message)
        logger.error(traceback.format_exc())
        set_task_status(task_id, "error")


async def async_json2keywords(server: Quart, filename: str, md5_name: str, task_id: str):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: async_json2keywords")

    try:
        # Create directory if it doesn't exist.
        os.makedirs(server.config["PROCESSED_FOLDER"], exist_ok=True)
        processed_file = f'{server.config["PROCESSED_FOLDER"]}/{md5_name}.json'

        with FileLock(f"{processed_file}.lock"):
            # Check if file already exists and q&a for it was generated, if so, set the task status as completed
            if os.path.isfile(processed_file):
                with open(processed_file, "r") as file:
                    if "keywords" in json.load(file):
                        logger.debug(f"Definition already exists for {filename}, returning...")
                        set_task_status(task_id, "completed")
                        return

        pdf_text = json2text(server, md5_name)

        logger.debug("JSON text (converted from JSON): ")
        logger.debug(pdf_text)

        truncated_pdf_text = truncate2gpt_tokens(server, md5_name, pdf_text, just_split_pages=False)
        logger.debug(f"Length of truncated_pdf_text: {len(truncated_pdf_text)}")

        generated_definitions = []
        for index, text_chunk in enumerate(truncated_pdf_text):
            definitions = await gpt_generate_definitions(server, md5_name, text_chunk)
            if definitions is None:
                continue
            generated_definitions = generated_definitions + definitions
            set_task_progress(task_id, float(index + 1) / float(len(truncated_pdf_text)))

        append_json_value_to_file(processed_file, "keywords", generated_definitions)
        set_task_status(task_id, "completed")
        logger.debug("Definition Generation Successful.")

    except Exception as e:
        error_message = f"Error: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0].lineno}"
        print(error_message, file=sys.stderr)
        logger.error(error_message)
        logger.error(traceback.format_exc())
        set_task_status(task_id, "error")


async def async_json2flashcards(server: Quart, filename: str, md5_name: str, task_id: str):
    logger: logging.Logger = get_logger_for_file(server, md5_name)
    logger.info("Function: async_json2flashcard")

    try:
        # Create directory if it doesn't exist.
        os.makedirs(server.config["PROCESSED_FOLDER"], exist_ok=True)
        processed_file = f'{server.config["PROCESSED_FOLDER"]}/{md5_name}.json'

        with FileLock(f"{processed_file}.lock"):
            # Check if file already exists and q&a for it was generated, if so, set the task status as completed
            if os.path.isfile(processed_file):
                with open(processed_file, "r") as file:
                    if "flashcards" in json.load(file):
                        logger.debug(f"Flashcards already exists for {filename}, returning...")
                        set_task_status(task_id, "completed")
                        return

        pdf_text = json2text(server, md5_name)

        logger.debug("JSON text (converted from JSON): ")
        logger.debug(pdf_text)

        truncated_pdf_text = truncate2gpt_tokens(server, md5_name, pdf_text, just_split_pages=False)
        logger.debug(f"Length of truncated_pdf_text: {len(truncated_pdf_text)}")

        generated_qa = []
        for index, text_chunk in enumerate(truncated_pdf_text):
            qa = await gpt_generate_qa(server, md5_name, text_chunk)
            if qa is None:
                continue
            generated_qa = generated_qa + qa
            set_task_progress(task_id, float(index + 1) / float(len(truncated_pdf_text)))

        append_json_value_to_file(processed_file, "flashcards", generated_qa)
        set_task_status(task_id, "completed")
        logger.debug("Flashcard Generation Successful.")

    except Exception as e:
        error_message = f"Error: {str(e)} at line {traceback.extract_tb(e.__traceback__)[0].lineno}"
        print(error_message, file=sys.stderr)
        logger.error(error_message)
        logger.error(traceback.format_exc())
        set_task_status(task_id, "error")


def append_json_value_to_file(filename: str, key: str, value: object):
    processed_json = {}

    with FileLock(f"{filename}.lock"):
        if os.path.isfile(filename):
            with open(filename, "r") as file:
                processed_json = json.load(file)

        processed_json[key] = value

        # Save Q&A set to filesystem
        with open(filename, "w") as file:
            json.dump(processed_json, file)
