from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID", "harmoniq-ai-nm")
DATASET    = "harmoniq_analytics"

client = bigquery.Client(project=PROJECT_ID)

# ── Expenses table ────────────────────────────────────────────
expenses_schema = [
    bigquery.SchemaField("id",          "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("date",        "DATE",      mode="REQUIRED"),
    bigquery.SchemaField("category",    "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("description", "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("amount",      "FLOAT64",   mode="REQUIRED"),
    bigquery.SchemaField("currency",    "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("user_id",     "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("project_id",  "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("created_at",  "TIMESTAMP", mode="NULLABLE"),
]

expenses_table = bigquery.Table(
    f"{PROJECT_ID}.{DATASET}.expenses",
    schema=expenses_schema
)
expenses_table.time_partitioning = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.DAY,
    field="date"
)

try:
    client.create_table(expenses_table)
    print("✅ BigQuery expenses table created")
except Exception as e:
    print(f"⚠️  Expenses table: {e}")

# ── Tasks table ───────────────────────────────────────────────
tasks_schema = [
    bigquery.SchemaField("id",          "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("title",       "STRING",    mode="REQUIRED"),
    bigquery.SchemaField("status",      "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("due_date",    "DATE",      mode="NULLABLE"),
    bigquery.SchemaField("category",    "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("project_id",  "STRING",    mode="NULLABLE"),
    bigquery.SchemaField("created_at",  "TIMESTAMP", mode="NULLABLE"),
]

tasks_table = bigquery.Table(
    f"{PROJECT_ID}.{DATASET}.tasks",
    schema=tasks_schema
)

try:
    client.create_table(tasks_table)
    print("✅ BigQuery tasks table created")
except Exception as e:
    print(f"⚠️  Tasks table: {e}")

print(f"\n✅ BigQuery setup complete!")
print(f"   Dataset: {PROJECT_ID}.{DATASET}")
print(f"   Console: https://console.cloud.google.com/bigquery?project={PROJECT_ID}")
