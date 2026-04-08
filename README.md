# ✦ Harmoniq AI

> **Your personal AI chief of staff** — tasks, finance, calendar, notes, and daily intelligence, all in one conversational interface.

[![Demo Video](https://img.shields.io/badge/▶%20Watch%20Demo-6c63ff?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/GreenIcePhoenix/Harmoniq-AI/releases/download/v1.0/Demo_Video_Harmoniq-AI_v1.0.mp4)
[![Live App](https://img.shields.io/badge/Live%20App-Cloud%20Run-4fc3f7?style=for-the-badge&logo=googlecloud&logoColor=white)](https://harmoniq-ai-912771917824.asia-south1.run.app/)
[![Built with ADK](https://img.shields.io/badge/Built%20with-Google%20ADK-43e97b?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)

---

## 📹 Demo

> Click the badge above or watch the full walkthrough:
> **[▶ Harmoniq AI — Full Demo Video](https://github.com/GreenIcePhoenix/Harmoniq-AI/releases/download/v1.0/Demo_Video_Harmoniq-AI_v1.0.mp4)**

The demo covers:
- 🌅 Morning briefing with tasks, budget pulse, and live news
- 💰 Expense logging with instant budget feedback
- 📊 Spending insights and monthly finance report
- ✅ Task management across projects
- 💱 Live currency conversion
- 📅 Calendar overview

---

## 🧠 What is Harmoniq AI?

Harmoniq AI is a **multi-agent personal assistant** built on Google's Agent Development Kit (ADK) and deployed on Cloud Run. It routes your natural language requests to specialized sub-agents, each with their own tools and Firestore-backed memory.

Instead of juggling five different apps, you talk to one interface — and the right agent handles it.

```
You: "good morning"
→ Morning briefing agent pulls tasks, budget, calendar + live news

You: "log ₹500 on groceries"
→ Finance agent writes to Firestore, checks budget, alerts if overspent

You: "create task Review PR due tomorrow"
→ Task agent creates and stores it, links to active project
```

---

## 🤖 Agent Capabilities

### 🌅 Morning Briefing Agent
Delivers a structured daily briefing every morning:
- Today's calendar events and schedule gaps
- Pending and overdue tasks with priority nudge
- Budget pulse — spent vs limit, safe daily spend
- Live news headlines (finance & productivity focused)
- Personalized tip based on your task backlog

### ✅ Task Agent
Full task lifecycle management:
- Create tasks with title, due date, and category
- List tasks by status (`pending` / `in_progress` / `done`)
- Update task status
- Delete individual tasks or bulk-clear all
- Links tasks to active projects via shared state
- Syncs all task data to BigQuery for analytics

### 📅 Calendar Agent
Google Calendar integration:
- View upcoming events and today's schedule
- Identify free slots for focused work
- Used by the morning briefing for daily schedule summary

### 💰 Finance Agent
Complete personal finance management:

| Capability | Details |
|---|---|
| **Log expense** | Amount + category required, smart defaults for date/currency |
| **Log income** | Source + amount, stored separately for net balance |
| **Budget management** | Set monthly limit, get warnings when approaching/exceeding |
| **Balance summary** | Income vs expenses, net surplus or deficit |
| **Spending insights** | Top category, daily average, projected month-end total |
| **Monthly report** | Full formatted report rendered inline in chat |
| **Currency conversion** | Live rates via open.er-api.com, no API key needed |
| **Delete expenses** | By ID or bulk clear with confirmation |

### 📊 Insights Agent
Cross-domain intelligence layer:
- Weekly and monthly performance summaries
- Combines task completion rate, budget health, and calendar utilization
- Queries BigQuery for historical trend analysis
- "How am I doing overall?" — synthesizes all agents into one view

### 📝 Notes Agent
Lightweight note-taking and documentation:
- Create and retrieve notes
- End-of-day summaries
- Agenda and planning support

---

## 🏗️ Architecture

```
Browser (Custom UI)
       │
proxy_server.py  (port 8080, Cloud Run)
       │
ADK Server  (port 9000, internal)
       │
harmoniq_primary  ← router agent
       │
  ┌────┼────────────────────────┐
  │    │                        │
task  finance  morning_briefing  calendar  insights  notes
agent  agent       agent          agent     agent    agent
  │    │
  └────┴──── Firestore ──── BigQuery
```

**Key design decisions:**
- **Stateless sessions** — new session per request, no cross-message leakage
- **Cloud-native auth** — `google.auth.default()` only, no service account keys in repo
- **Non-blocking side effects** — Sheets sync failures never surface to user; Firestore is source of truth
- **Inline reports** — Monthly finance report rendered in chat, no Google Docs dependency

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [Google ADK](https://google.github.io/adk-docs/) |
| LLM | Gemini 2.5 Flash (Vertex AI) |
| Hosting | Google Cloud Run |
| Primary database | Firestore |
| Analytics | BigQuery |
| Auth | Cloud Run Service Account (IAM) |
| Currency API | open.er-api.com (no key required) |
| Frontend | Vanilla HTML/CSS/JS (single file) |

---

## 🚀 Running Locally

### Prerequisites
- Google Cloud project with billing enabled
- `gcloud` CLI authenticated
- Python 3.11+

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/harmoniq-ai-nm.git
cd harmoniq-ai-nm

# Install dependencies
pip install -r requirements.txt

# Authenticate
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Set environment variables
export PROJECT_ID=your-project-id
export MODEL=gemini-2.5-flash
export MONTHLY_BUDGET_INR=10000

# Start
python proxy_server.py
```

Open `http://localhost:8080`

---

## ☁️ Deploy to Cloud Run

```bash
gcloud run deploy harmoniq-ai \
  --source . \
  --region=asia-south1 \
  --set-env-vars PROJECT_ID=your-project-id,MODEL=gemini-2.5-flash,MONTHLY_BUDGET_INR=10000 \
  --allow-unauthenticated
```

---

## 📁 Project Structure

```
harmoniq-ai-nm/
├── harmoniq_app/
│   ├── agent.py                 # Primary router agent
│   ├── task_agent.py            # Task management
│   ├── finance_agent.py         # Finance + budget tools
│   ├── calendar_agent.py        # Google Calendar
│   ├── insights_agent.py        # Cross-domain insights
│   ├── morning_briefing_agent.py # Daily briefing
│   ├── notes_agent.py           # Notes and docs
│   ├── firestore_tools.py       # All Firestore + BigQuery ops
│   └── google_api_client.py     # Google API auth helpers
├── ui/
│   ├── index.html               # Main chat UI
│   └── dashboard.html           # Finance dashboard
├── proxy_server.py              # HTTP proxy + static server
├── Dockerfile
├── requirements.txt
└── start.sh
```

---

## 💬 Example Prompts

```
good morning
log ₹1200 electricity bill
what's my budget status?
create task Prepare slides due Friday
convert ₹10000 to USD
show my pending tasks
generate my monthly finance report
how am I doing overall?
log income 50000 salary
give me an end of day summary
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">
  <sub>Built with ✦ by Harmoniq AI — powered by Google ADK + Gemini</sub>
</div>
