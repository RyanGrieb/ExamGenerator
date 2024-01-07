import time
import asyncio
import sys
from quart import jsonify


# FIXME: Prevent duplicate tasks based on task type and file hash.
class AsyncTask:
    def __init__(self, task_id):
        self.task_id = task_id
        self.status = None
        self.last_checked = None
        self.progress = 0.0
        self.attributes = {}

    def get_status_json(self):
        """
        Returns the task status, and updates the time it was last checked.
        """
        self.last_checked = time.time()

        return jsonify({"status": self.status, "progress": self.progress, "attributes": self.attributes})


running_checker = False
running_tasks: dict[str, AsyncTask] = {}

"""Write a function that allows us to await fun() if there is a running task with attribute key x and value y"""


"""
Async function that waits until a task with a specified attribute key & value is completed.
"""


async def await_task(task_id):
    task = running_tasks[task_id]
    while task.status != "completed":
        await asyncio.sleep(1)
        task = running_tasks[task_id]


def set_task_attribute(task_id: str, key: str, value: object):
    if task_id not in running_tasks:
        return

    running_tasks[task_id].attributes[key] = value


def set_task_progress(task_id: str, progress: float):
    if task_id not in running_tasks:
        print(f"Error: Setting task progress when task not created: {task_id}", file=sys.stderr)
        return

    if progress > 1 or progress < 0:
        print(f"Error: Setting task progress out of bounds (0-1): {progress}", file=sys.stderr)
        return

    print(f"Setting progress of task {task_id} to {progress}", file=sys.stderr)
    running_tasks[task_id].progress = progress


def set_task_status(task_id: str, status: str):
    if task_id not in running_tasks:
        running_tasks[task_id] = AsyncTask(task_id)

    running_tasks[task_id].status = status
    running_tasks[task_id].last_checked = time.time()

    if status == "completed":
        running_tasks[task_id].progress = 1

    # Begin the task checker once we have created a task.
    if not running_checker:
        start_task_checker()


# Clear any unsued, or tasks with errors.
def start_task_checker():
    global running_checker

    async def check():
        while True:
            print(f"Checking for stale tasks of current: {len(running_tasks.items())} tasks.", file=sys.stderr)
            now = time.time()

            tasks_to_remove = []

            for task_id, task in running_tasks.items():
                if task.status == "error" or now - task.last_checked > 10:
                    tasks_to_remove.append(task_id)

            if len(tasks_to_remove) > 0:
                print(f"Found {len(tasks_to_remove)} stale tasks. Removing...", file=sys.stderr)

            for task_id in tasks_to_remove:
                del running_tasks[task_id]

            await asyncio.sleep(10)

    asyncio.create_task(check())
    running_checker = True
