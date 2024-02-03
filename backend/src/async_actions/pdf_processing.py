from quart import Quart
import sys
import os, sys
import aiohttp
import asyncio
import logging
import traceback
from .async_task import set_task_status, set_task_progress, set_task_attribute
from .document_processing import get_logger_for_file, running_unstructured_processes
from werkzeug.datastructures import FileStorage
import pypdf


def get_pages(file: FileStorage):
    pdf_reader = pypdf.PdfReader(file)
    return len(pdf_reader.pages)
