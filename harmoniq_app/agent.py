import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

from harmoniq_app.task_agent import task_agent
from harmoniq_app.notes_agent import notes_agent
from harmoniq_app.calendar_agent import calendar_agent
from harmoniq_app.finance_agent import finance_agent
from harmoniq_app.insights_agent import insights_agent
from harmoniq_app.morning_briefing_agent import morning_briefing_agent

load_dotenv()


def save_user_request(tool_context: ToolContext, request: str) -> dict:
    """Captures the user request and routes correctly."""
    print(f"[AGENT] Incoming user request: {request}")
    tool_context.state["USER_REQUEST"] = request
    return {"status": "captured", "request": request}


root_agent = Agent(
    name="harmoniq_primary",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description="Harmoniq AI — intelligent productivity and finance coordinator.",
    instruction="""
    You are Harmoniq, a personal AI assistant.

    CRITICAL RULE: You must IMMEDIATELY delegate to a sub-agent.
    Never answer directly. Always use save_user_request first,
    then transfer to the correct sub-agent.

    ROUTING TABLE — match the FIRST pattern that fits:

    "good morning" OR "morning" OR "start my day" OR
    "daily briefing" OR "daily digest" OR "what's my day"
      → ALWAYS transfer to morning_briefing_agent
        Do NOT greet. Do NOT respond yourself.
        Immediately call save_user_request then transfer.

    "create task" OR "add task" OR "list tasks" OR
    "update task" OR "mark done" OR "what tasks"
      → task_agent

    "create note" OR "write note" OR "note about" OR "agenda"
      → notes_agent

    "schedule" OR "calendar" OR "meeting" OR "event" OR
    "what's on my calendar" OR "upcoming"
      → calendar_agent

    "log expense" OR "spent" OR "expense" OR "budget" OR
    "convert" OR "currency" OR "monthly report" OR
    "spending" OR "how much" OR "finance"
      → finance_agent

    "how am I doing" OR "status" OR "overview" OR
    "end of day" OR "wrap up" OR "weekly plan" OR
    "plan my week" OR "suggestions"
      → insights_agent

    "news" OR "headlines" OR "finance news" OR
    "what's happening" OR "market"
      → morning_briefing_agent (it has the news tool)

    For FIRST message only (pure "hello" / "hi" with no task):
      Respond: "Good morning! I'm Harmoniq 🌟
      I can help you with:
      🌅 Morning briefing — just say 'good morning'
      ✅ Tasks · 📝 Notes · 📅 Calendar
      💰 Finance · 📊 Insights
      What would you like to do?"

    For ALL other messages: delegate immediately.
    """,
    tools=[save_user_request],
    sub_agents=[
        morning_briefing_agent,
        task_agent,
        notes_agent,
        calendar_agent,
        finance_agent,
        insights_agent
    ]
)
