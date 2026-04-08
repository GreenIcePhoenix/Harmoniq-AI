import os
from harmoniq_app.firestore_tools import list_tasks, get_monthly_expenses
from datetime import datetime, date, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.langchain_tool import LangchainTool
from google.cloud import bigquery, firestore
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import calendar as cal_lib

PROJECT_ID   = os.getenv("PROJECT_ID", "harmoniq-ai-nm")
BUDGET_LIMIT = float(os.getenv("MONTHLY_BUDGET_INR", "10000"))


# ── LANGCHAIN WIKIPEDIA ───────────────────────────────────────

wikipedia_tool = LangchainTool(
    tool=WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(
            top_k_results=1,
            doc_content_chars_max=400
        )
    )
)


# ── RSS NEWS TOOL ─────────────────────────────────────────────

def get_financial_news(tool_context: ToolContext) -> dict:
    """
    Fetches latest Indian finance news via free RSS feeds.
    No API key, no rate limits — works from Cloud Shell and Cloud Run.
    """
    import feedparser
    import urllib.request
    import html
    import re as _re

    FEEDS = [
        {
            "name": "Google Finance India",
            "url":  "https://news.google.com/rss/search?q=personal+finance+India&hl=en-IN&gl=IN&ceid=IN:en"
        },
        {
            "name": "NDTV Profit",
            "url":  "https://feeds.feedburner.com/ndtvprofit-latest"
        },
        {
            "name": "India Today Money",
            "url":  "https://www.indiatoday.in/rss/1206514"
        },
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36"
        )
    }

    KEYWORDS = [
        "budget", "saving", "invest", "tax", "rupee", "inr", "expense",
        "finance", "money", "mutual fund", "sip", "inflation", "rbi",
        "salary", "income", "loan", "emi", "insurance", "credit"
    ]

    headlines = []

    for feed_info in FEEDS:
        try:
            req = urllib.request.Request(feed_info["url"], headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()

            feed = feedparser.parse(raw)

            for entry in feed.entries[:20]:
                title   = html.unescape(entry.get("title", "")).strip()
                summary = html.unescape(
                    _re.sub(r"<[^>]+>", "", entry.get("summary", ""))
                ).strip()[:150]
                link    = entry.get("link", "")

                if title and any(k in title.lower() for k in KEYWORDS):
                    headlines.append({
                        "source":  feed_info["name"],
                        "title":   title,
                        "summary": summary,
                        "link":    link
                    })
                    if len(headlines) >= 4:
                        break

        except Exception:
            continue

        if len(headlines) >= 4:
            break

    # Fallback: take first 3 from Google regardless of keywords
    if not headlines:
        try:
            req = urllib.request.Request(FEEDS[0]["url"], headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                feed = feedparser.parse(resp.read())
            for entry in feed.entries[:3]:
                title = html.unescape(entry.get("title", "")).strip()
                if title:
                    headlines.append({
                        "source":  "Google Finance India",
                        "title":   title,
                        "summary": "",
                        "link":    entry.get("link", "")
                    })
        except Exception:
            pass

    # Static fallback — always useful
    if not headlines:
        headlines = [
            {
                "source":  "Harmoniq Tips",
                "title":   "Track every expense — small daily spends add up fast",
                "summary": "Most overspending comes from purchases under ₹200",
                "link":    ""
            },
            {
                "source":  "Harmoniq Tips",
                "title":   "Use the 50-30-20 rule: needs, wants, savings",
                "summary": "50% needs, 30% wants, 20% savings for financial health",
                "link":    ""
            }
        ]

    tool_context.state["news_headlines"] = headlines
    return {
        "status":    "success",
        "headlines": headlines[:3],
        "count":     len(headlines),
        "message":   f"✅ Fetched {len(headlines)} headlines"
    }


# ── BIGQUERY ANALYTICS ────────────────────────────────────────

def get_bigquery_spending_analytics(tool_context: ToolContext) -> dict:
    """
    Runs BigQuery SQL for spending trends, 7-day average,
    top category, and budget projection.
    Falls back to Firestore if BigQuery has no data yet.
    """
    try:
        bq = bigquery.Client(project=PROJECT_ID)

        q1 = f"""
        SELECT
            category,
            ROUND(SUM(amount), 2) AS total,
            COUNT(*)              AS txn_count
        FROM `{PROJECT_ID}.harmoniq_analytics.expenses`
        WHERE DATE(date) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY category
        ORDER BY total DESC
        """

        q2 = f"""
        SELECT
            CAST(date AS STRING)  AS day,
            ROUND(SUM(amount), 2) AS daily_total
        FROM `{PROJECT_ID}.harmoniq_analytics.expenses`
        WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        GROUP BY date
        ORDER BY date
        """

        q3 = f"""
        SELECT ROUND(IFNULL(SUM(amount), 0), 2) AS today_total
        FROM `{PROJECT_ID}.harmoniq_analytics.expenses`
        WHERE DATE(date) = CURRENT_DATE()
        """

        results = {}

        try:
            rows        = list(bq.query(q1).result())
            by_cat      = {r.category: float(r.total) for r in rows}
            month_total = sum(by_cat.values())
            top_cat     = max(by_cat, key=by_cat.get) if by_cat else "none"
            results["month_total"]  = month_total
            results["by_category"]  = by_cat
            results["top_category"] = (
                f"{top_cat} (₹{by_cat.get(top_cat, 0):.0f})"
            )
        except Exception:
            results["month_total"]  = 0
            results["by_category"]  = {}
            results["top_category"] = "No data yet"

        try:
            rows      = list(bq.query(q2).result())
            trend     = {r.day: float(r.daily_total) for r in rows}
            avg_daily = sum(trend.values()) / len(trend) if trend else 0
            results["seven_day_avg_daily"] = f"₹{avg_daily:.0f}/day"
        except Exception:
            results["seven_day_avg_daily"] = "₹0/day"

        try:
            rows        = list(bq.query(q3).result())
            today_total = float(rows[0].today_total) if rows else 0
            results["today_spent"] = f"₹{today_total:.0f}"
        except Exception:
            results["today_spent"] = "₹0"

        today_date    = date.today()
        days_elapsed  = today_date.day
        days_in_month = cal_lib.monthrange(
            today_date.year, today_date.month
        )[1]
        days_left     = days_in_month - days_elapsed
        daily_avg     = (
            results["month_total"] / days_elapsed if days_elapsed else 0
        )
        projected     = daily_avg * days_in_month
        remaining     = BUDGET_LIMIT - results["month_total"]
        safe_daily    = remaining / max(days_left, 1)

        results["budget_remaining"] = f"₹{remaining:.0f}"
        results["projected_spend"]  = f"₹{projected:.0f}"
        results["safe_daily_spend"] = f"₹{safe_daily:.0f}/day"
        results["on_track"]         = projected <= BUDGET_LIMIT
        results["budget_status"]    = (
            "✅ On track"
            if projected <= BUDGET_LIMIT
            else f"⚠️ Projected to overspend by ₹{projected - BUDGET_LIMIT:.0f}"
        )
        results["data_source"] = "bigquery"

        tool_context.state["bq_analytics"] = results
        return {"status": "success", "analytics": results}

    except Exception as e:
        return _firestore_fallback(tool_context, str(e))


def _firestore_fallback(tool_context: ToolContext, reason: str) -> dict:
    """Falls back to Firestore when BigQuery has no data yet."""
    try:
        db            = firestore.Client()
        current_month = datetime.utcnow().strftime("%Y-%m")
        expenses      = [
            d.to_dict() for d in db.collection("expenses").stream()
            if d.to_dict().get("date", "").startswith(current_month)
        ]
        total  = sum(e.get("amount", 0) for e in expenses)
        by_cat = {}
        for e in expenses:
            cat         = e.get("category", "other")
            by_cat[cat] = by_cat.get(cat, 0) + e["amount"]

        top_cat   = max(by_cat, key=by_cat.get) if by_cat else "none"
        remaining = BUDGET_LIMIT - total

        today_date    = date.today()
        days_in_month = cal_lib.monthrange(
            today_date.year, today_date.month
        )[1]
        days_left  = days_in_month - today_date.day
        safe_daily = remaining / max(days_left, 1)

        results = {
            "month_total":         total,
            "by_category":         by_cat,
            "top_category":        (
                f"{top_cat} (₹{by_cat.get(top_cat,0):.0f})"
                if by_cat else "none"
            ),
            "budget_remaining":    f"₹{remaining:.0f}",
            "safe_daily_spend":    f"₹{safe_daily:.0f}/day",
            "today_spent":         "₹0",
            "seven_day_avg_daily": "₹0/day",
            "budget_status":       (
                "✅ On track"
                if total <= BUDGET_LIMIT
                else "⚠️ Over budget"
            ),
            "data_source": "firestore_fallback"
        }

        tool_context.state["bq_analytics"] = results
        return {
            "status":    "success",
            "analytics": results,
            "note":      "Using Firestore (BQ syncs on next expense)"
        }
    except Exception as e2:
        return {"status": "error", "message": str(e2)}


# ── TODAY'S AGENDA ────────────────────────────────────────────

def get_todays_agenda(tool_context: ToolContext) -> dict:
    """Pulls today's tasks and Google Calendar events."""
    try:
        db    = firestore.Client()
        today = date.today().isoformat()
        now   = datetime.utcnow()

        all_tasks    = [d.to_dict() for d in db.collection("tasks").stream()]
        pending      = [t for t in all_tasks if t.get("status") == "pending"]
        due_today    = [t for t in pending if t.get("due_date", "") == today]
        overdue      = [
            t for t in pending
            if t.get("due_date", "9999") < today
        ]
        due_tomorrow = [
            t for t in pending
            if t.get("due_date", "") ==
            (date.today() + timedelta(days=1)).isoformat()
        ]

        calendar_events = []
        try:
            from harmoniq_app.google_api_client import get_calendar_service
            svc   = get_calendar_service()
            start = (
                datetime(now.year, now.month, now.day).isoformat()
                + "+05:30"
            )
            end   = (
                datetime(now.year, now.month, now.day, 23, 59).isoformat()
                + "+05:30"
            )
            result = svc.events().list(
                calendarId=os.getenv(
                    "CALENDAR_OWNER", "future.mathur@gmail.com"
                ),
                timeMin=start,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            calendar_events = [
                {
                    "title": e.get("summary", "Untitled"),
                    "time":  e.get("start", {}).get(
                        "dateTime", "All day"
                    )[:16].replace("T", " ")
                }
                for e in result.get("items", [])
            ]
        except Exception:
            pass

        agenda = {
            "date":             today,
            "day_of_week":      date.today().strftime("%A"),
            "tasks_due_today":  [t.get("title") for t in due_today],
            "overdue_tasks":    [t.get("title") for t in overdue[:3]],
            "due_tomorrow":     [t.get("title") for t in due_tomorrow[:3]],
            "calendar_events":  calendar_events,
            "total_pending":    len(pending)
        }

        tool_context.state["todays_agenda"] = agenda
        return {"status": "success", "agenda": agenda}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── AGENT DEFINITION ─────────────────────────────────────────

morning_briefing_agent = Agent(
    name="morning_briefing_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description=(
        "Generates a personalised morning briefing combining "
        "BigQuery analytics, calendar, tasks, and live news."
    ),
    instruction="""
    You are Harmoniq's Morning Briefing Agent.
    When triggered run ALL four steps in order:

    STEP 1 — get_todays_agenda
    STEP 2 — list_tasks
    STEP 3 — get_bigquery_spending_analytics
    STEP 4 — get_monthly_expenses
    STEP 5 — get_financial_news
    STEP 6 — wikipedia_tool (optional — only if a headline contains a term worth a 1-line explanation)

    Then synthesize into this exact format
    (fill in actual values from the tool results — do not use placeholder text):

    Start with a divider line of dashes.
    Then: "Good Morning! — " followed by the actual day of week and date from agenda.
    Then another divider.

    Section 1 — TODAY'S SCHEDULE
    List each calendar event with its time.
    If no events: write "Clear schedule — great for deep work!"

    Section 2 — TASKS
    Due today: list the task titles, or "None — enjoy the day!"
    Overdue: list overdue task titles, or "None — all caught up!"
    Due tomorrow: list titles or "None"

    Section 3 — BUDGET PULSE
    Show: spent this month vs 10000 limit
    Show: remaining amount and safe daily spend from analytics
    Show: top spending category from analytics
    Show: 7-day daily average from analytics
    Show: budget forecast status

    Section 4 — MORNING READ
    List 2-3 headlines with their source name.

    Section 5 — TODAY'S TIP
    Write ONE personalised actionable tip based on the actual data:
    - If overdue tasks exist: name the oldest task to tackle first
    - If budget is tight (under 2000 remaining): name the category to cut
    - If calendar is empty: suggest scheduling a focus block
    - If all looks good: give a proactive savings or productivity tip

    End with a divider line.
    """,
    tools=[
        get_financial_news,
        list_tasks,
        get_bigquery_spending_analytics,
        get_monthly_expenses, 
        get_todays_agenda,
        wikipedia_tool,
    ],
    output_key="morning_briefing"
)
