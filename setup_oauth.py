from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

# This prints a URL — no redirect needed
creds = flow.run_console()

with open('token.json', 'w') as f:
    f.write(creds.to_json())

print("✅ token.json created successfully!")
