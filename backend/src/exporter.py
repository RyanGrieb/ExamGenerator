import os
from quart import Quart
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
import reportlab.graphics.shapes

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]
styles = getSampleStyleSheet()


def myLaterPages(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawString(inch, 0.75 * inch, "Page %d %s" % (doc.page, "- PDF2Flashcards.com"))
    canvas.restoreState()


def main():
    with open(
        "C:\\Users\\Ryan\\Documents\\Coding\\PDF2Questions\\backend\\data\\pdf-qa\\9aa583f663f566ac9401e0507368987d.txt",
        mode="r",
        encoding="utf-8",
    ) as file:
        qa_sets = []
        curret_qa_set = []
        lines = file.read().splitlines()
        print(lines)
        for index, line in enumerate(lines):
            if (line.startswith("Q:") and len(curret_qa_set) > 0) or index >= len(lines) - 1:
                # If were the last element, append it to the current_qa_set before we add the lest set.
                if index >= len(lines) - 1:
                    curret_qa_set.append(line)

                qa_sets.append(list(curret_qa_set))
                curret_qa_set.clear()

            curret_qa_set.append(line)

        print(qa_sets)
    # filename = f"f850a63bfc307a9a2f44293a497052b4.pdf"
    canvas = Canvas("./backend/data/exports/doc.pdf")
    styleSheet = getSampleStyleSheet()
    style = styleSheet["BodyText"]

    availableWidth = PAGE_WIDTH - 40
    availableHeight = PAGE_HEIGHT - 20
    # y_axis = availableHeight
    last_answer_y = 0

    for set in qa_sets:
        question = set[0]
        answers = set[1:]

        question_paragraph = Paragraph(question, style)

        width, question_height = question_paragraph.wrap(availableWidth, availableHeight)

        if availableHeight - question_height <= 40:
            canvas.showPage()
            availableHeight = PAGE_HEIGHT - 20

        # print(f"w: {width}, h: {question_height}")

        canvas.line(0, availableHeight, PAGE_WIDTH, availableHeight)
        availableHeight -= question_height
        question_paragraph.drawOn(canvas, 20, availableHeight)

        for answer in answers:
            answer_paragraph = Paragraph(answer, style)
            width, answer_height = answer_paragraph.wrap(availableWidth, availableHeight)
            answer_paragraph.drawOn(canvas, 20, availableHeight - (answer_height))
            last_answer_y = availableHeight - (answer_height) - 10
            availableHeight -= answer_height + 20
        # index += 1
        # if index > 2:
        #    break

    canvas.save()


if __name__ == "__main__":
    main()


def export_files(server: Quart, task_status, task_id, file_id, md5_names: list[str], export_type):
    function_dict = {"excel": export_excel, "pdf": export_pdf, "text": export_text}
    # FIXME: Check if export_type doesn't exist, and return false if so

    # Create the export folder if needed
    if not os.path.exists(server.config["EXPORT_FOLDER"]):
        os.makedirs(server.config["EXPORT_FOLDER"])

    if function_dict[export_type](server, md5_names, file_id):
        task_status[task_id] = "completed"
    else:
        task_status[task_id] = "error"


def get_qa_sets(server: Quart, md5_name: str) -> list[str]:
    """
    Loads the Q&A sets from a file and returns it as a variable.
    """

    qa_sets = []
    with open(f'{server.config["QA_FOLDER"]}/{md5_name}.txt', "r") as file:
        curret_qa_set = []
        lines = file.read().splitlines()
        for index, line in enumerate(lines):
            if (line.startswith("Q:") and len(curret_qa_set) > 0) or index >= len(lines) - 1:
                # If were the last element, append it to the current_qa_set before we add the lest set.
                if index >= len(lines) - 1:
                    curret_qa_set.append(line)

                qa_sets.append(list(curret_qa_set))
                curret_qa_set.clear()

            curret_qa_set.append(line)

    return qa_sets


def export_pdf(server: Quart, md5_names: list[str], file_id: str):
    """
    Generates a pdf file of all Q&A sets from the provided files.
    """
    canvas = Canvas(f"./data/exports/{file_id}.pdf")
    styleSheet = getSampleStyleSheet()
    style = styleSheet["BodyText"]

    availableWidth = PAGE_WIDTH - 40
    availableHeight = PAGE_HEIGHT - 20

    for md5_name in md5_names:
        qa_sets = get_qa_sets(server, md5_name)

        for set in qa_sets:
            question = set[0]
            answers = set[1:]

            question_paragraph = Paragraph(question, style)

            _, question_height = question_paragraph.wrap(availableWidth, availableHeight)

            if availableHeight - question_height <= 80:
                canvas.showPage()
                availableHeight = PAGE_HEIGHT - 20

            # print(f"w: {width}, h: {question_height}")
            canvas.line(0, availableHeight, PAGE_WIDTH, availableHeight)
            availableHeight -= 20  # Slap on some padding at the top after we draw the line.
            availableHeight -= question_height
            question_paragraph.drawOn(canvas, 20, availableHeight)

            for answer in answers:
                answer_paragraph = Paragraph(answer, style)
                _, answer_height = answer_paragraph.wrap(availableWidth, availableHeight)
                answer_paragraph.drawOn(canvas, 20, availableHeight - (answer_height))
                availableHeight -= answer_height + 20

            canvas.line(0, availableHeight, PAGE_WIDTH, availableHeight)

    canvas.save()
    return True


def export_excel(md5_names: list[str], file_id: str):
    """
    Generates a excel file of all Q&A sets from the provided files.

    Args:
        md5_names (list[str]): The md5 values for the files we want to use.
    """
    return True


def export_text(md5_names: list[str], file_id: str):
    """
    Generates a txt file of all Q&A sets from the provided files.

    Args:
        md5_names (list[str]): The md5 values for the files we want to use.
    """

    return True
