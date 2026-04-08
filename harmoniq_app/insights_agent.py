import os
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.cloud import firestore
from datetime import datetime, timedelta, date
import calendar


# ── CROSS DOMAIN SUMMARY ─────────────────────────────────────

def get_cross_domain_summary(tool_context: ToolContext) -> dict:
    """Pulls tasks, expenses, and state for a unified health check."""
    try:
        db            = firestore.Client()
        current_month = datetime.utcnow().strftime("%Y-%m")
        today         = date.today().isoformat()

        # Tasks
        all_tasks = [d.to_dict() for d in db.collection("tasks").stream()]
        pending   = [t for t in all_tasks if t.get("status") == "pending"]
        overdue   = [t for t in pending if t.get("due_date", "9999") < today]
        due_today = [t for t in pending if t.get("due_date", "") == today]

        # Expenses
        expenses    = [
            d.to_dict() for d in db.collection("expenses").stream()
            if d.to_dict().get("date", "").startswith(current_month)
        ]
        total_spent = sum(e.get("amount", 0) for e in expenses)
        remaining   = float(os.getenv("MONTHLY_BUDGET_INR", "10000")) - total_spent

        # Projection
        days_elapsed  = date.today().day
        daily_avg     = total_spent / days_elapsed if days_elapsed else 0
        days_in_month = calendar.monthrange(
            date.today().year, date.today().month
        )[1]
        projected = daily_avg * days_in_month

        suggestions = []
        if overdue:
            suggestions.append(
                f"⚠️ {len(overdue)} overdue task(s): "
                f"{', '.join(t.get('title','') for t in overdue[:3])}"
            )
        if due_today:
            suggestions.append(
                f"📌 Due today: "
                f"{', '.join(t.get('title','') for t in due_today[:3])}"
            )
        if projected > float(os.getenv("MONTHLY_BUDGET_INR", "10000")):
            suggestions.append(
                f"💸 Projected to spend ₹{projected:.0f} this month — "
                f"over your ₹{os.getenv('MONTHLY_BUDGET_INR','10000')} limit!"
            )
        if remaining < 2000:
            suggestions.append(
                f"🔴 Only ₹{remaining:.0f} left in budget this month."
            )
        if not suggestions:
            suggestions.append(
                "✅ Everything looks great! Tasks on track, budget healthy."
            )

        summary = {
            "pending_tasks":   len(pending),
            "overdue_tasks":   len(overdue),
            "due_today":       len(due_today),
            "total_spent":     f"₹{total_spent:.0f}",
            "budget_remaining": f"₹{remaining:.0f}",
            "projected_spend": f"₹{projected:.0f}",
            "suggestions":     suggestions
        }

        tool_context.state["cross_summary"] = summary
        return {
            "status":      "success",
            "summary":     summary,
            "suggestions": suggestions
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── END OF DAY SUMMARY ───────────────────────────────────────

def get_end_of_day_summary(tool_context: ToolContext) -> dict:
    """Generates a complete end-of-day summary across all domains."""
    try:
        db            = firestore.Client()
        today         = date.today().isoformat()
        tomorrow      = (date.today() + timedelta(days=1)).isoformat()
        current_month = datetime.utcnow().strftime("%Y-%m")

        # Tasks
        all_tasks   = [d.to_dict() for d in db.collection("tasks").stream()]
        done_today  = [t for t in all_tasks if t.get("status") == "done"]
        pending     = [t for t in all_tasks if t.get("status") == "pending"]
        due_tomorrow = [t for t in pending if t.get("due_date", "") == tomorrow]

        # Expenses today
        expenses_today = [
            d.to_dict() for d in db.collection("expenses").stream()
            if d.to_dict().get("date", "") == today
        ]
        spent_today = sum(e.get("amount", 0) for e in expenses_today)

        # Month total
        month_expenses = [
            d.to_dict() for d in db.collection("expenses").stream()
            if d.to_dict().get("date", "").startswith(current_month)
        ]
        month_total = sum(e.get("amount", 0) for e in month_expenses)

        summary = {
            "date":             today,
            "tasks_completed":  len(done_today),
            "tasks_pending":    len(pending),
            "due_tomorrow":     [t.get("title") for t in due_tomorrow],
            "spent_today":      f"₹{spent_today:.0f}",
            "month_total":      f"₹{month_total:.0f}",
            "today_breakdown":  [
                f"{e.get('category')}: ₹{e.get('amount')}"
                for e in expenses_today
            ],
            "last_event": tool_context.state.get(
                "last_event", {}
            ).get("title", "No events today")
        }

        tool_context.state["eod_summary"] = summary
        return {
            "status":  "success",
            "summary": summary,
            "message": f"📋 End of day summary for {today} ready."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── WEEKLY PLAN SUMMARY ──────────────────────────────────────

def get_weekly_overview(tool_context: ToolContext) -> dict:
    """Summarizes the week ahead — tasks due, budget headroom, suggestions."""
    try:
        db      = firestore.Client()
        today   = date.today()
        week_end = (today + timedelta(days=7)).isoformat()
        today_s  = today.isoformat()

        all_tasks = [d.to_dict() for d in db.collection("tasks").stream()]
        due_week  = [
            t for t in all_tasks
            if t.get("status") == "pending"
            and today_s <= t.get("due_date", "9999") <= week_end
        ]
        overdue = [
            t for t in all_tasks
            if t.get("status") == "pending"
            and t.get("due_date", "9999") < today_s
        ]

        current_month = datetime.utcnow().strftime("%Y-%m")
        month_expenses = [
            d.to_dict() for d in db.collection("expenses").stream()
            if d.to_dict().get("date", "").startswith(current_month)
        ]
        total_spent = sum(e.get("amount", 0) for e in month_expenses)
        budget      = float(os.getenv("MONTHLY_BUDGET_INR", "10000"))
        remaining   = budget - total_spent
        daily_budget = remaining / max(
            (date(today.year, today.month,
             calendar.monthrange(today.year, today.month)[1])
             - today).days, 1
        )

        plan = {
            "week_start":       today_s,
            "week_end":         week_end,
            "tasks_due_week":   len(due_week),
            "task_list":        [t.get("title") for t in due_week[:5]],
            "overdue_tasks":    len(overdue),
            "budget_remaining": f"₹{remaining:.0f}",
            "safe_daily_spend": f"₹{daily_budget:.0f}/day",
            "tip": (
                "Focus on clearing overdue tasks first."
                if overdue else
                "Good standing — stay consistent this week!"
            )
        }

        tool_context.state["weekly_plan"] = plan
        return {
            "status": "success",
            "plan":   plan,
            "message": f"📅 Weekly overview for {today_s} → {week_end} ready."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── AGENT DEFINITION ─────────────────────────────────────────

insights_agent = Agent(
    name="insights_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description=(
        "Cross-domain intelligence — correlates tasks, calendar, "
        "and spending to give proactive summaries and suggestions."
    ),
    instruction="""
    You are the Insights Agent for Harmoniq.
    You see the full picture across tasks, calendar, and finances.

    For END OF DAY / DAILY SUMMARY requests:
      1. get_end_of_day_summary
      Present: tasks completed, spent today, due tomorrow, month total.

    For "HOW AM I DOING" / GENERAL HEALTH CHECK:
      1. get_cross_domain_summary
      Present: overdue tasks, budget status, all suggestions clearly.

    For WEEKLY PLAN / PLAN MY WEEK:
      1. get_weekly_overview
      Present: tasks due this week, safe daily spend, tip.

    Always lead with the most urgent item.
    Use emojis to make the summary scannable.
    Be concise, specific, and actionable.
    End with one clear next action the user should take.
    """,
    tools=[
        get_cross_domain_summary,
        get_end_of_day_summary,
        get_weekly_overview
    ],
    output_key="insights_result"
)
