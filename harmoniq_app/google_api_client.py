import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Key is at ~/harmoniq-ai-nm/sa-key.json
SA_KEY_FILE = '/app/agents/harmoniq_app/sa-key.json'

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def get_credentials():
    """Service account credentials — no OAuth needed."""
    return service_account.Credentials.from_service_account_file(
        SA_KEY_FILE,
        scopes=SCOPES
    )

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

def get_sheets_service():
    return build('sheets', 'v4', credentials=get_credentials())

def get_docs_service():
    return build('docs', 'v1', credentials=get_credentials())

def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())
