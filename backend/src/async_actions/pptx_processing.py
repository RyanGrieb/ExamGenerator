from werkzeug.datastructures import FileStorage
from pptx import Presentation


# FIXME: Just move this into document_processing
def get_pages(file: FileStorage) -> int:
    try:
        pptx_file = Presentation(file)
        return len(pptx_file.slides)
    except Exception as e:
        print(f"Error: {e}")
        return 0
