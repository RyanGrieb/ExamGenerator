import json
from quart import Quart
import tiktoken
import sys
import os
import aiohttp
import asyncio
import openai


def main():
    # Create a sample list of elements
    """
    sample_elements = [
        {
            "type": "Title",
            "element_id": "1627230dedcf230775f4e5c4ad436617",
            "metadata": {
                "coordinates": {
                    "points": [
                        [85.2, 61.58881599999995],
                        [85.2, 115.61281600000001],
                        [625.16988, 115.61281600000001],
                        [625.16988, 61.58881599999995],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Key Security Concepts",
        },
        {
            "type": "Title",
            "element_id": "fbe3cdfd721911e4c4456a71bd1a1d9a",
            "metadata": {
                "coordinates": {
                    "points": [
                        [63.48, 176.46231999999998],
                        [63.48, 199.50232],
                        [224.80607999999998, 199.50232],
                        [224.80607999999998, 176.46231999999998],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Confidentiality",
        },
        {
            "type": "Title",
            "element_id": "ad5ea6aae7ca18f5f3823bfd0a0f0e40",
            "metadata": {
                "coordinates": {
                    "points": [
                        [322.58, 179.012],
                        [322.58, 203.012],
                        [416.660003816, 203.012],
                        [416.660003816, 179.012],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Integrity",
        },
        {
            "type": "Title",
            "element_id": "12f67f8539c46701e62d1c50254cf025",
            "metadata": {
                "coordinates": {
                    "points": [
                        [517.9, 179.012],
                        [517.9, 203.012],
                        [646.54, 203.012],
                        [646.54, 179.012],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Availability",
        },
        {
            "type": "ListItem",
            "element_id": "478d1d6eeca99398d4f816a080acba57",
            "metadata": {
                "coordinates": {
                    "points": [
                        [36.912, 241.32367999999997],
                        [36.912, 469.956672],
                        [210.15312, 469.956672],
                        [210.15312, 241.32367999999997],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Preserving authorized restrictions on information access and disclosure, including means for protecting personal privacy and proprietary information",
        },
        {
            "type": "ListItem",
            "element_id": "fd6abb2f4cf6b150c4b6dae69a640847",
            "metadata": {
                "coordinates": {
                    "points": [
                        [262.1, 239.81367999999998],
                        [262.1, 426.56368],
                        [449.30672000000004, 426.56368],
                        [449.30672000000004, 239.81367999999998],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Guarding against improper information modification or destruction, including ensuring information nonrepudiation and authenticity",
        },
        {
            "type": "ListItem",
            "element_id": "f0028bb2ec38ed65b5682636ed2a7b6f",
            "metadata": {
                "coordinates": {
                    "points": [
                        [481.54, 245.64368000000002],
                        [481.54, 327.51368],
                        [668.310016, 327.51368],
                        [668.310016, 245.64368000000002],
                    ],
                    "system": "PixelSpace",
                    "layout_width": 720,
                    "layout_height": 540,
                },
                "filename": "cffdc390b61f3ad60efb35874f29ae21.pdf",
                "filetype": "application/pdf",
                "page_number": 5,
            },
            "text": "Ensuring timely and reliable access to and use of information",
        }
        # Add more elements as needed
    ]
    """
    pdf_text = "===page:1===\nFOOOnFOOOnFOOOnFOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOOnFOOO\n===page:1===\n===page:2===\nBAAR\n===page:2==="
    # Call the merge_pdf_json_elements function
    text_list = truncate2gpt_tokens(pdf_text)

    # Print the modified elements (for testing purposes)
    print(text_list)


# Given a pdf_text string (Has the formatted page numbers), return a list of text under the 4096 token limit for chat-gpt
def truncate2gpt_tokens(pdf_text: str, just_split_pages=False):
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

    # print("PAGE SECTIONS:")
    # print(page_sections)
    if just_split_pages:
        return page_sections

    # Count the number of tokens for each page. Include what can be fit into our 4096 context for each string in the list.
    # FIXME: ACCOUNT FOR PDFs WHERE A SINGLE PAGE > 4096 TOKENS!!!!!!!!!!!!!!!
    # NOTE: Right now we use 1000 tokens to keep gpt accurate and consise for our information provided.
    truncated_pdf_text = []
    current_tokens = 0
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    for section in page_sections:
        num_tokens = len(encoding.encode(section))
        # print(num_tokens)
        if num_tokens + current_tokens >= 1000 or len(truncated_pdf_text) < 1:
            truncated_pdf_text.append("")
            current_tokens = 0

        truncated_pdf_text[-1] += section
        current_tokens += num_tokens

    # print(f"Used tokens: {current_tokens}")
    return truncated_pdf_text


# Get tokens from pdf elements and merge them onto a single line.
def merge_pdf_json_elements(elements):
    # List of all elements with an expanded bounding box.
    formatted_text = ""
    for element in elements:
        text = element["text"]
        if text[0].isupper():
            formatted_text += f"\n{text}"
        else:
            formatted_text += f"{text} "

    return formatted_text.rstrip()


# Parses the json file & creates a formatted .txt file of the PDF for ChatGPT to read.
def json2text(server: Quart, md5_name: str):
    formatted_text = ""
    current_page = 0
    page_elements = []

    with open(f'{server.config["JSON_FOLDER"]}/{md5_name}.json', "r") as file:
        json_data = json.load(file)

        # Do formatting on the following JSON data:
        # 1. Remove page number tokens (text of just a number)
        # 2. Remove duplicate tokens (e.g. The copyright footer at the bottom of some slides)
        # 3. Skip any uncessary json_items (page breaks, empty text)
        truncated_json_data = []
        existing_text_tokens = []
        for json_item in json_data:
            # Skip any page breaks, empty text, or duplicate text tokens.
            if json_item["type"] == "PageBreak":
                continue

            item_text: str = json_item["text"]

            if len(item_text) < 1:
                continue

            # FIXME: TEST IF THESE TWO STATEMENTS MESS UP OUR RESPONSES!! (MIGHT REMOVE IMPORTANT DATA??)
            if item_text in existing_text_tokens:
                continue
            if item_text.isnumeric():
                continue

            truncated_json_data.append(json_item)
            existing_text_tokens.append(json_item["text"])

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


async def gpt_generate_qa(data):
    print(f"Generate Q&A from text chunk: {data}")
    prompt = f"Generate clever Q&A flashcards each page from the following UNORDERED tokens. Make sure to cleverly answer the question generated. Only respond with: 'Q: ... [NEWLINE] A: ...' Here is the provided data:\n{data}"

    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[
            # {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    response_data: str = response["choices"][0]["message"]["content"]
    print("Q&A RESPONSE DATA:")
    print(response_data)
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


async def async_pdf2json(
    server: Quart, task_status, filename: str, md5_name: str, task_id: str
):
    try:
        # Check if the variables are received correctly
        print("Received filename:", filename, file=sys.stderr)
        print("Received md5_name:", md5_name, file=sys.stderr)

        pdf_file_path = f'{server.config["UPLOAD_FOLDER"]}/{md5_name}.pdf'
        json_file_path = f'{server.config["JSON_FOLDER"]}/{md5_name}.json'

        # Check if file already exists, if so, set the task status as completed:
        if os.path.isfile(json_file_path):
            print(f"JSON already exists for {filename}, returning...")
            task_status[task_id] = "completed"
            return

        form_data = aiohttp.FormData()
        form_data.add_field("files", open(pdf_file_path, "rb"))
        form_data.add_field("encoding", "utf_8")
        form_data.add_field("include_page_breaks", "true")  # FIXME: Not needed?
        form_data.add_field("coordinates", "false")
        # form_data.add_field("strategy", "auto")
        # form_data.add_field("hi_res_model_name", "detectron2_onnx")

        headers = {"accept": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                server.config["UNSTRUCTUED_API_URL"], headers=headers, data=form_data
            ) as response:
                if response.status == 200:
                    response_text = await response.text()
                    # TODO: Implement a keep-alive loop & cancel these post requests if terminated.
                    # FIXME: Handle any errors thrown by unstructured api.

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


async def async_json2questions(
    server: Quart, task_status, filename: str, md5_name: str, task_id: str
):
    qa_filepath = f'{server.config["QA_FOLDER"]}/{md5_name}.txt'

    # Check if file already exists, if so, set the task status as completed
    if os.path.isfile(qa_filepath):
        print(f"Q&A already exists for {filename}, returning...")
        task_status[task_id] = "completed"
        return

    pdf_text = json2text(server, md5_name)
    # print("Raw pdf_text: ")
    # print(pdf_text)
    truncated_pdf_text = truncate2gpt_tokens(pdf_text, just_split_pages=False)
    print("Truncated text_list::")
    print(truncated_pdf_text)
    print(len(truncated_pdf_text))
    generated_qa = []
    for text_chunk in truncated_pdf_text:
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

    with open(qa_filepath, "w") as file:
        file.write(qa_text)

    task_status[task_id] = "completed"


if __name__ == "__main__":
    main()
