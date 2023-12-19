import time
import asyncio
import sys


# FIXME: Prevent duplicate tasks based on task type and file hash.
class AsyncTask:
    def __init__(self, task_id):
        self.task_id = task_id
        self.status = None
        self.last_checked = None

    def get_status(self):
        """
        Returns the task status, and updates the time it was last checked.
        """
        self.last_checked = time.time()
        return self.status


running_checker = False
running_tasks: dict[str, AsyncTask] = {}


def set_task_status(task_id: str, status: str):
    if task_id not in running_tasks:
        running_tasks[task_id] = AsyncTask(task_id)

    running_tasks[task_id].status = status
    running_tasks[task_id].last_checked = time.time()

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
