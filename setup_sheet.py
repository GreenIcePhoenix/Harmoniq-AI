from harmoniq_app.tools.google_api_client import get_sheets_service, get_drive_service
from dotenv import load_dotenv
import os

load_dotenv()

sheets = get_sheets_service()
drive  = get_drive_service()

# Create the spreadsheet
spreadsheet = sheets.spreadsheets().create(body={
    'properties': {'title': 'Harmoniq Expense Tracker'},
    'sheets': [{'properties': {'title': 'Expenses'}}]
}).execute()

sheet_id  = spreadsheet['spreadsheetId']
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

print(f"✅ Sheet created!")
print(f"   ID  : {sheet_id}")
print(f"   URL : {sheet_url}")

# Write headers
sheets.spreadsheets().values().update(
    spreadsheetId=sheet_id,
    range='Expenses!A1:F1',
    valueInputOption='RAW',
    body={'values': [['ID', 'Date', 'Category', 'Description', 'Amount (INR)', 'User']]}
).execute()
print("✅ Headers written to sheet")

# Share the sheet with your personal Google account
# so you can actually see it in Drive
drive.permissions().create(
    fileId=sheet_id,
    body={
        'type': 'user',
        'role': 'writer',
        'emailAddress': 'future.mathur@gmail.com'
    },
    sendNotificationEmail=False
).execute()
print("✅ Sheet shared with future.mathur@gmail.com")

# Save sheet ID to .env
env_path = '.env'
with open(env_path, 'r') as f:
    content = f.read()

if 'SHEETS_EXPENSE_ID' in content:
    # Update existing line
    lines = content.splitlines()
    lines = [l if not l.startswith('SHEETS_EXPENSE_ID') 
             else f'SHEETS_EXPENSE_ID={sheet_id}' for l in lines]
    with open(env_path, 'w') as f:
        f.write('\n'.join(lines))
else:
    with open(env_path, 'a') as f:
        f.write(f'\nSHEETS_EXPENSE_ID={sheet_id}\n')

print(f"✅ SHEETS_EXPENSE_ID saved to .env")
print(f"\n🎉 Open your sheet: {sheet_url}")
