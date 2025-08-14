from __future__ import annotations
from typing import Protocol, Dict, Any, List, Optional


class CalendarProvider(Protocol):
    """Abstracts external calendar operations for testability."""

    def list_calendars(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return external calendars for the user."""
        ...

    def list_events(
        self,
        user_context: Dict[str, Any],
        calendar_external_id: str,
        sync_token: Optional[str] = None,
        since_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return events and optionally a next sync token.
        Result shape: { 'items': [...], 'nextSyncToken': Optional[str] }
        """
        ...
