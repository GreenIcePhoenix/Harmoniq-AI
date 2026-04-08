import os
from datetime import datetime, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from harmoniq_app.google_api_client import get_calendar_service

# The shared calendar ID = your email
CALENDAR_ID = os.getenv('CALENDAR_OWNER', 'future.mathur@gmail.com')

def schedule_event(
    tool_context: ToolContext,
    title: str,
    date: str,
    time: str = "10:00",
    duration_minutes: int = 60,
    description: str = ""
) -> dict:
    """Creates a real event in your Google Calendar via service account."""
    try:
        service = get_calendar_service()
        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            'summary': title,
            'description': description or tool_context.state.get("USER_REQUEST", ""),
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end':   {'dateTime': end_dt.isoformat(),   'timeZone': 'Asia/Kolkata'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup',  'minutes': 30},
                    {'method': 'email',  'minutes': 60},
                ]
            }
        }

        event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event_body
        ).execute()

        tool_context.state["last_event_id"] = event.get("id")
        return {
            "status": "success",
            "event_id": event.get("id"),
            "event_url": event.get("htmlLink"),
            "message": (
                f"📅 '{title}' scheduled for {date} at {time} IST. "
                f"Reminder set 30 mins before."
            )
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_upcoming_events(tool_context: ToolContext, days_ahead: int = 7) -> dict:
    """Fetches upcoming events from your shared Google Calendar."""
    try:
        service   = get_calendar_service()
        now       = datetime.utcnow().isoformat() + 'Z'
        future    = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now,
            timeMax=future,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = [
            {
                "title": e.get("summary", "Untitled"),
                "start": e.get("start", {}).get("dateTime",
                         e.get("start", {}).get("date")),
                "link":  e.get("htmlLink")
            }
            for e in result.get('items', [])
        ]
        return {
            "status": "success",
            "count": len(events),
            "events": events,
            "message": f"Found {len(events)} event(s) in the next {days_ahead} days."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


calendar_agent = Agent(
    name="calendar_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description="Schedules and retrieves real Google Calendar events with reminders.",
    instruction="""
    You are the Calendar Manager for Harmoniq.
    - Use schedule_event to create real Google Calendar events.
      Extract: title, date (YYYY-MM-DD), time (HH:MM 24h), duration.
      Default time: 10:00. Default duration: 60 minutes.
    - Use get_upcoming_events to show the user's real schedule.
    - Always share the event link in your response.
    - Timezone is Asia/Kolkata (IST).
    """,
    tools=[schedule_event, get_upcoming_events],
    output_key="calendar_result"
)
