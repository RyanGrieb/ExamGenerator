import json
from quart import Quart
from rect_intersection import intersects
import matplotlib.pyplot as plt
import tiktoken


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
        formatted_text += f'{element["text"]} '

    return formatted_text.rstrip()


# Parses the json file & creates a formatted .txt file of the PDF for ChatGPT to read.
def json2text(server: Quart, md5_name: str):
    formatted_text = ""
    current_page = 0
    page_elements = []

    with open(f'{server.config["JSON_FOLDER"]}/{md5_name}.json', "r") as file:
        json_data = json.load(file)
        for json_item in json_data:
            # Skip any page breaks.
            if json_item["type"] == "PageBreak" or len(json_item["text"]) < 1:
                continue

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


if __name__ == "__main__":
    main()
