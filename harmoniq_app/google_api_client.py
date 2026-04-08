import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def get_credentials():
    credentials, _ = google.auth.default(scopes=SCOPES)
    return credentials

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

def get_sheets_service():
    return build('sheets', 'v4', credentials=get_credentials())

def get_docs_service():
    return build('docs', 'v1', credentials=get_credentials())

def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())
