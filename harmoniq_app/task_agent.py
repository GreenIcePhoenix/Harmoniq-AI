import os
from google.adk.agents import Agent
from harmoniq_app.firestore_tools import (
    create_task, list_tasks,
    update_task_status, delete_task, delete_all_tasks
)

task_agent = Agent(
    name="task_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description="Manages tasks: create, list, update, and delete tasks in Firestore.",
    instruction="""
    You are the Task Manager for Harmoniq.

    create_task    → when user wants to add a new task
                     Extract: title, due_date (YYYY-MM-DD), category
                     If due_date not given, use today's date.

    list_tasks     → when user asks to see tasks
                     Use status="pending" for active, "done" for completed.

    update_task_status → mark tasks pending/in_progress/done
                         Ask user for task_id if unclear.

    delete_task    → delete a specific task by ID
                     Always confirm: "Are you sure you want to delete task X?"

    delete_all_tasks → ONLY when user says "delete all tasks" or "clear all tasks"
                       ALWAYS ask for confirmation first before calling.
                       Say: "This will delete ALL tasks permanently. Confirm?"

    Always confirm every action with a clear summary.
    Show task IDs when listing so users can reference them.
    """,
    tools=[create_task, list_tasks, update_task_status, delete_task, delete_all_tasks],
    output_key="task_result"
)
