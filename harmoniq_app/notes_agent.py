from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
import os

def create_note_summary(tool_context: ToolContext, title: str, content: str) -> dict:
    from harmoniq_app.google_api_client import get_docs_service, get_drive_service

    try:
        docs  = get_docs_service()
        drive = get_drive_service()

        # Create doc
        doc = docs.documents().create(
            body={"title": title}
        ).execute()

        doc_id = doc.get("documentId")

        # Insert content
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content
                        }
                    }
                ]
            }
        ).execute()

        # Give access
        drive.permissions().create(
            fileId=doc_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": os.getenv("CALENDAR_OWNER")
            },
            sendNotificationEmail=False
        ).execute()

        link = f"https://docs.google.com/document/d/{doc_id}"

        return {
            "status": "success",
            "note": {
                "title": title,
                "content": content,
                "note_url": link
            },
            "message": f"✅ Note created: {title}\n📄 {link}"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def list_notes(tool_context: ToolContext) -> dict:
    """Lists all notes created by Harmoniq with their Google Docs links."""
    try:
        from harmoniq_app.google_api_client import get_drive_service
        drive = get_drive_service()

        results = drive.files().list(
            q="mimeType='application/vnd.google-apps.document' and trashed=false",
            spaces='drive',
            fields='files(id, name, createdTime, webViewLink)',
            orderBy='createdTime desc',
            pageSize=10
        ).execute()

        files = results.get('files', [])
        notes = [
            {
                "title":   f.get("name"),
                "url":     f.get("webViewLink"),
                "created": f.get("createdTime", "")[:10]
            }
            for f in files
        ]
        return {
            "status": "success",
            "count":  len(notes),
            "notes":  notes,
            "message": f"Found {len(notes)} notes in your Google Drive."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

notes_agent = Agent(
    name="notes_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description="Creates and manages structured notes linked to tasks.",
    instruction="""
    You are the Notes Manager for Harmoniq.
    - Use create_note_summary to create a note with a title and content.
    - Automatically link notes to the last created task if available in state.
    - Format note content clearly with sections when appropriate.
    - Confirm the note was created and share the document link.
    """,
    tools=[create_note_summary],
    output_key="notes_result"
)
