"""
Google Services Module - Gmail and Google Calendar API Integration
Uses OAuth2 credentials from credentials.json
"""

import os
import json
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import List, Dict, Optional, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes required for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'


def get_credentials() -> Optional[Credentials]:
    """Get or refresh Google API credentials."""
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, get them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. "
                    "Please download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future runs
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_gmail_service():
    """Build and return Gmail API service."""
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def get_calendar_service():
    """Build and return Calendar API service."""
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


# ==================== GMAIL OPERATIONS ====================

def get_recent_emails(count: int = 5, query: str = '') -> List[Dict[str, Any]]:
    """
    Fetch recent emails from Gmail.

    Args:
        count: Number of emails to fetch (default 5)
        query: Gmail search query (e.g., 'is:unread', 'from:someone@example.com')

    Returns:
        List of email dictionaries with id, subject, sender, date, snippet
    """
    try:
        service = get_gmail_service()

        # Search for messages
        search_query = query if query else 'in:inbox'
        results = service.users().messages().list(
            userId='me',
            q=search_query,
            maxResults=count
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            return []

        emails = []
        for msg in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = msg_detail.get('payload', {}).get('headers', [])
            email_data = {
                'id': msg['id'],
                'subject': 'No Subject',
                'sender': 'Unknown',
                'date': 'Unknown',
                'snippet': msg_detail.get('snippet', '')
            }

            for header in headers:
                name = header.get('name', '')
                value = header.get('value', '')
                if name == 'Subject':
                    email_data['subject'] = value
                elif name == 'From':
                    email_data['sender'] = value
                elif name == 'Date':
                    email_data['date'] = value

            emails.append(email_data)

        return emails

    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching emails: {str(e)}")


def get_email_content(email_id: str) -> Dict[str, Any]:
    """
    Get full content of a specific email.

    Args:
        email_id: The Gmail message ID

    Returns:
        Dictionary with email details and body
    """
    try:
        service = get_gmail_service()

        msg = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        headers = msg.get('payload', {}).get('headers', [])
        email_data = {
            'id': email_id,
            'subject': 'No Subject',
            'sender': 'Unknown',
            'date': 'Unknown',
            'body': '',
            'snippet': msg.get('snippet', '')
        }

        for header in headers:
            name = header.get('name', '')
            value = header.get('value', '')
            if name == 'Subject':
                email_data['subject'] = value
            elif name == 'From':
                email_data['sender'] = value
            elif name == 'Date':
                email_data['date'] = value
            elif name == 'To':
                email_data['to'] = value

        # Extract body
        payload = msg.get('payload', {})
        body = extract_body_from_payload(payload)
        email_data['body'] = body

        return email_data

    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error getting email: {str(e)}")


def extract_body_from_payload(payload: Dict) -> str:
    """Extract text body from email payload."""
    body = ''

    mime_type = payload.get('mimeType', '')

    if mime_type == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    elif mime_type == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            html = base64.urlsafe_b64decode(data).decode('utf-8')
            # Simple HTML to text conversion
            import re
            body = re.sub('<[^<]+?>', '', html)
    elif 'parts' in payload:
        for part in payload['parts']:
            part_body = extract_body_from_payload(part)
            if part_body:
                body += part_body + '\n'

    return body.strip()


def send_email(to: str, subject: str, body: str, cc: str = '', bcc: str = '') -> str:
    """
    Send an email via Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)

    Returns:
        Success message with message ID
    """
    try:
        service = get_gmail_service()

        # Create message
        message = MIMEText(body, 'plain', 'utf-8')
        message['to'] = to
        message['subject'] = subject

        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        return f"Email sent successfully. Message ID: {send_message['id']}"

    except HttpError as e:
        raise Exception(f"Gmail API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error sending email: {str(e)}")


def search_emails(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g., 'is:unread', 'subject:meeting')
        max_results: Maximum number of results

    Returns:
        List of matching emails
    """
    return get_recent_emails(count=max_results, query=query)


# ==================== GOOGLE CALENDAR OPERATIONS ====================

def get_calendar_list() -> List[Dict[str, Any]]:
    """Get list of user's calendars."""
    try:
        service = get_calendar_service()
        calendars = service.calendarList().list().execute()
        return calendars.get('items', [])
    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error getting calendars: {str(e)}")


def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = '',
    location: str = '',
    attendees: List[str] = None,
    calendar_id: str = 'primary'
) -> Dict[str, Any]:
    """
    Create a calendar event.

    Args:
        summary: Event title
        start_time: Start time in ISO format (e.g., '2024-01-15T10:00:00')
        end_time: End time in ISO format
        description: Event description
        location: Event location
        attendees: List of attendee email addresses
        calendar_id: Calendar ID (default: primary)

    Returns:
        Created event details
    """
    try:
        service = get_calendar_service()

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return {
            'id': created_event['id'],
            'summary': created_event['summary'],
            'start': created_event['start']['dateTime'],
            'end': created_event['end']['dateTime'],
            'link': created_event.get('htmlLink', '')
        }

    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error creating event: {str(e)}")


def list_events(
    max_results: int = 10,
    time_min: str = None,
    time_max: str = None,
    calendar_id: str = 'primary'
) -> List[Dict[str, Any]]:
    """
    List calendar events.

    Args:
        max_results: Maximum number of events to return
        time_min: Start time in ISO format (default: now)
        time_max: End time in ISO format (optional)
        calendar_id: Calendar ID (default: primary)

    Returns:
        List of events
    """
    try:
        service = get_calendar_service()

        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'

        params = {
            'calendarId': calendar_id,
            'timeMin': time_min,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }

        if time_max:
            params['timeMax'] = time_max

        events_result = service.events().list(**params).execute()
        events = events_result.get('items', [])

        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'start': start,
                'end': end,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'link': event.get('htmlLink', '')
            })

        return formatted_events

    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error listing events: {str(e)}")


def update_event(
    event_id: str,
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None,
    calendar_id: str = 'primary'
) -> Dict[str, Any]:
    """
    Update an existing calendar event.

    Args:
        event_id: Event ID to update
        summary: New title (optional)
        start_time: New start time in ISO format (optional)
        end_time: New end time in ISO format (optional)
        description: New description (optional)
        location: New location (optional)
        calendar_id: Calendar ID (default: primary)

    Returns:
        Updated event details
    """
    try:
        service = get_calendar_service()

        # Get existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update fields if provided
        if summary:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_time:
            event['start']['dateTime'] = start_time
        if end_time:
            event['end']['dateTime'] = end_time

        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()

        return {
            'id': updated_event['id'],
            'summary': updated_event['summary'],
            'start': updated_event['start']['dateTime'],
            'end': updated_event['end']['dateTime'],
            'link': updated_event.get('htmlLink', '')
        }

    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error updating event: {str(e)}")


def delete_event(event_id: str, calendar_id: str = 'primary') -> str:
    """
    Delete a calendar event.

    Args:
        event_id: Event ID to delete
        calendar_id: Calendar ID (default: primary)

    Returns:
        Success message
    """
    try:
        service = get_calendar_service()

        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        return f"Event {event_id} deleted successfully."

    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error deleting event: {str(e)}")


def quick_add_event(text: str, calendar_id: str = 'primary') -> Dict[str, Any]:
    """
    Quick add event using natural language.

    Args:
        text: Natural language description (e.g., "Meeting tomorrow at 3pm")
        calendar_id: Calendar ID (default: primary)

    Returns:
        Created event details
    """
    try:
        service = get_calendar_service()

        created_event = service.events().quickAdd(
            calendarId=calendar_id,
            text=text
        ).execute()

        return {
            'id': created_event['id'],
            'summary': created_event['summary'],
            'start': created_event['start'].get('dateTime', created_event['start'].get('date')),
            'end': created_event['end'].get('dateTime', created_event['end'].get('date')),
            'link': created_event.get('htmlLink', '')
        }

    except HttpError as e:
        raise Exception(f"Calendar API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error quick-adding event: {str(e)}")


def check_credentials_exist() -> bool:
    """Check if credentials.json file exists."""
    return os.path.exists(CREDENTIALS_FILE)
