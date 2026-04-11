"""
LangChain v1 Tools for Gmail and Google Calendar
Using the new @tool decorator pattern from langchain_core.tools
"""

from datetime import datetime, timedelta
from typing import List, Optional, Type, Any
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool, tool

from google_services import (
    get_recent_emails,
    get_email_content,
    send_email,
    search_emails,
    create_event,
    list_events,
    update_event,
    delete_event,
    quick_add_event,
    check_credentials_exist
)


# ==================== INPUT SCHEMAS ====================

class GetEmailsInput(BaseModel):
    """Input for getting recent emails."""
    count: int = Field(default=5, description="Number of emails to fetch (max 20)")
    query: str = Field(default='', description="Gmail search query (e.g., 'is:unread', 'from:someone@example.com')")


class GetEmailContentInput(BaseModel):
    """Input for getting specific email content."""
    email_id: str = Field(description="The Gmail message ID to retrieve")


class SendEmailInput(BaseModel):
    """Input for sending an email."""
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body content (plain text)")
    cc: str = Field(default='', description="CC recipients (comma-separated, optional)")
    bcc: str = Field(default='', description="BCC recipients (comma-separated, optional)")


class SearchEmailsInput(BaseModel):
    """Input for searching emails."""
    query: str = Field(description="Gmail search query (e.g., 'is:unread subject:meeting')")
    max_results: int = Field(default=10, description="Maximum number of results")


class CreateCalendarEventInput(BaseModel):
    """Input for creating a calendar event."""
    summary: str = Field(description="Event title/summary")
    start_time: str = Field(description="Start time in ISO format (e.g., '2024-01-15T10:00:00')")
    end_time: str = Field(description="End time in ISO format (e.g., '2024-01-15T11:00:00')")
    description: str = Field(default='', description="Event description (optional)")
    location: str = Field(default='', description="Event location (optional)")
    attendees: str = Field(default='', description="Comma-separated list of attendee emails (optional)")


class ListCalendarEventsInput(BaseModel):
    """Input for listing calendar events."""
    max_results: int = Field(default=10, description="Maximum number of events to return")
    days_ahead: int = Field(default=7, description="Number of days to look ahead from now")


class UpdateCalendarEventInput(BaseModel):
    """Input for updating a calendar event."""
    event_id: str = Field(description="The event ID to update")
    summary: str = Field(default=None, description="New event title (optional)")
    start_time: str = Field(default=None, description="New start time in ISO format (optional)")
    end_time: str = Field(default=None, description="New end time in ISO format (optional)")
    description: str = Field(default=None, description="New description (optional)")
    location: str = Field(default=None, description="New location (optional)")


class DeleteCalendarEventInput(BaseModel):
    """Input for deleting a calendar event."""
    event_id: str = Field(description="The event ID to delete")


class QuickAddEventInput(BaseModel):
    """Input for quick adding an event using natural language."""
    text: str = Field(description="Natural language description (e.g., 'Meeting tomorrow at 3pm')")


# ==================== TOOL FUNCTIONS ====================

@tool
def get_recent_emails_tool(count: int = 5, query: str = '') -> str:
    """
    Get recent emails from Gmail inbox.

    Args:
        count: Number of emails to fetch (default 5, max 20)
        query: Gmail search query for filtering (e.g., 'is:unread', 'from:someone@example.com')

    Returns:
        Formatted string with email list including subject, sender, date, and snippet
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        count = min(count, 20)  # Limit to 20 emails
        emails = get_recent_emails(count=count, query=query)

        if not emails:
            return "📭 No emails found."

        result = f"📧 Recent Emails ({len(emails)}):\n\n"
        for i, email in enumerate(emails, 1):
            result += f"{i}. From: {email['sender']}\n"
            result += f"   Subject: {email['subject']}\n"
            result += f"   Date: {email['date']}\n"
            result += f"   Snippet: {email['snippet'][:100]}...\n"
            result += f"   ID: {email['id']}\n\n"

        return result

    except Exception as e:
        return f"❌ Error fetching emails: {str(e)}"


@tool
def get_email_content_tool(email_id: str) -> str:
    """
    Get the full content of a specific email.

    Args:
        email_id: The Gmail message ID to retrieve

    Returns:
        Formatted string with complete email details and body content
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        email = get_email_content(email_id)

        result = f"📧 Email Details:\n\n"
        result += f"From: {email['sender']}\n"
        result += f"To: {email.get('to', 'Unknown')}\n"
        result += f"Subject: {email['subject']}\n"
        result += f"Date: {email['date']}\n\n"
        result += f"Body:\n{email['body'][:2000]}"

        if len(email['body']) > 2000:
            result += "\n\n... (content truncated)"

        return result

    except Exception as e:
        return f"❌ Error getting email: {str(e)}"


@tool
def send_email_tool(to: str, subject: str, body: str, cc: str = '', bcc: str = '') -> str:
    """
    Send an email via Gmail.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content (plain text)
        cc: CC recipients (comma-separated, optional)
        bcc: BCC recipients (comma-separated, optional)

    Returns:
        Success message or error
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        result = send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return f"✅ {result}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


@tool
def search_emails_tool(query: str, max_results: int = 10) -> str:
    """
    Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g., 'is:unread', 'subject:meeting', 'from:boss@company.com')
        max_results: Maximum number of results to return

    Returns:
        Formatted string with matching emails
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        emails = search_emails(query=query, max_results=min(max_results, 20))

        if not emails:
            return f"📭 No emails found for query: '{query}'"

        result = f"📧 Search Results for '{query}' ({len(emails)}):\n\n"
        for i, email in enumerate(emails, 1):
            result += f"{i}. From: {email['sender']}\n"
            result += f"   Subject: {email['subject']}\n"
            result += f"   Date: {email['date']}\n"
            result += f"   Snippet: {email['snippet'][:100]}...\n"
            result += f"   ID: {email['id']}\n\n"

        return result

    except Exception as e:
        return f"❌ Error searching emails: {str(e)}"


@tool
def create_calendar_event_tool(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = '',
    location: str = '',
    attendees: str = ''
) -> str:
    """
    Create a new event in Google Calendar.

    Args:
        summary: Event title
        start_time: Start time in ISO format (e.g., '2024-01-15T10:00:00')
        end_time: End time in ISO format (e.g., '2024-01-15T11:00:00')
        description: Event description (optional)
        location: Event location (optional)
        attendees: Comma-separated list of attendee emails (optional)

    Returns:
        Success message with event details and link
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        attendee_list = [e.strip() for e in attendees.split(',') if e.strip()] if attendees else []

        event = create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendee_list
        )

        return (
            f"✅ Event created successfully!\n\n"
            f"📌 Title: {event['summary']}\n"
            f"🕐 Start: {event['start']}\n"
            f"🕐 End: {event['end']}\n"
            f"🔗 Link: {event['link']}"
        )

    except Exception as e:
        return f"❌ Error creating event: {str(e)}"


@tool
def list_calendar_events_tool(max_results: int = 10, days_ahead: int = 7) -> str:
    """
    List upcoming events from Google Calendar.

    Args:
        max_results: Maximum number of events to return (default 10)
        days_ahead: Number of days to look ahead (default 7)

    Returns:
        Formatted string with event list
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        time_min = datetime.utcnow().isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        events = list_events(
            max_results=max_results,
            time_min=time_min,
            time_max=time_max
        )

        if not events:
            return f"📅 No events found for the next {days_ahead} days."

        result = f"📅 Upcoming Events (next {days_ahead} days):\n\n"
        for i, event in enumerate(events, 1):
            result += f"{i}. {event['summary']}\n"
            result += f"   🕐 {event['start']}\n"
            if event.get('location'):
                result += f"   📍 {event['location']}\n"
            result += f"   🆔 {event['id']}\n\n"

        return result

    except Exception as e:
        return f"❌ Error listing events: {str(e)}"


@tool
def update_calendar_event_tool(
    event_id: str,
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None
) -> str:
    """
    Update an existing calendar event.

    Args:
        event_id: The event ID to update (get from list_events)
        summary: New title (optional)
        start_time: New start time in ISO format (optional)
        end_time: New end time in ISO format (optional)
        description: New description (optional)
        location: New location (optional)

    Returns:
        Success message with updated event details
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        event = update_event(
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location
        )

        return (
            f"✅ Event updated successfully!\n\n"
            f"📌 Title: {event['summary']}\n"
            f"🕐 Start: {event['start']}\n"
            f"🕐 End: {event['end']}\n"
            f"🔗 Link: {event['link']}"
        )

    except Exception as e:
        return f"❌ Error updating event: {str(e)}"


@tool
def delete_calendar_event_tool(event_id: str) -> str:
    """
    Delete a calendar event.

    Args:
        event_id: The event ID to delete (get from list_events)

    Returns:
        Success message
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        result = delete_event(event_id)
        return f"✅ {result}"
    except Exception as e:
        return f"❌ Error deleting event: {str(e)}"


@tool
def quick_add_event_tool(text: str) -> str:
    """
    Quick add an event using natural language.

    Args:
        text: Natural language description (e.g., 'Meeting with John tomorrow at 3pm', 'Lunch next Friday at noon')

    Returns:
        Success message with created event details
    """
    if not check_credentials_exist():
        return "❌ Google credentials not configured. Please set up credentials.json."

    try:
        event = quick_add_event(text)

        return (
            f"✅ Event added via quick add!\n\n"
            f"📌 Title: {event['summary']}\n"
            f"🕐 Start: {event['start']}\n"
            f"🕐 End: {event['end']}\n"
            f"🔗 Link: {event['link']}"
        )

    except Exception as e:
        return f"❌ Error adding event: {str(e)}"


# ==================== TOOL LISTS ====================

# Gmail tools list
GMAIL_TOOLS = [
    get_recent_emails_tool,
    get_email_content_tool,
    send_email_tool,
    search_emails_tool
]

# Calendar tools list
CALENDAR_TOOLS = [
    create_calendar_event_tool,
    list_calendar_events_tool,
    update_calendar_event_tool,
    delete_calendar_event_tool,
    quick_add_event_tool
]

# All Google tools combined
ALL_GOOGLE_TOOLS = GMAIL_TOOLS + CALENDAR_TOOLS
