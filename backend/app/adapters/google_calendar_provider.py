from __future__ import annotations
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ..ports.calendar_provider import CalendarProvider


class GoogleCalendarProvider(CalendarProvider):
    def __init__(self, credentials: Credentials):
        self._service = build('calendar', 'v3', credentials=credentials)

    def list_calendars(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        res = self._service.calendarList().list().execute()
        return res.get('items', [])

    def list_events(
        self,
        user_context: Dict[str, Any],
        calendar_external_id: str,
        sync_token: Optional[str] = None,
        since_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        req = self._service.events().list(
            calendarId=calendar_external_id,
            syncToken=sync_token if sync_token else None,
            timeMin=since_iso if (since_iso and not sync_token) else None,
            maxResults=2500,
            singleEvents=True,
            orderBy='startTime' if (since_iso and not sync_token) else None,
        )
        return req.execute()
