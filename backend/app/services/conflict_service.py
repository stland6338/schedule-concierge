from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from ..db import models
from ..repositories.event_repository import EventRepository, SqlAlchemyEventRepository
from .recommendation_service import compute_slots

class ConflictDetected(Exception):
    """Raised when event conflicts are detected and not allowed"""
    pass

class ConflictService:
    """Service for detecting and resolving event conflicts"""
    def __init__(self, repository: EventRepository | None = None):
        self.repo = repository or SqlAlchemyEventRepository()
    
    def detect_conflicts(self, db: Session, new_event: models.Event) -> List[models.Event]:
        """
        Detect conflicts between a new event and existing events.
        
        Args:
            db: Database session
            new_event: Event to check for conflicts
            
        Returns:
            List of conflicting existing events
        """
        # Ensure timezone consistency
        new_start = new_event.start_at
        new_end = new_event.end_at
        
        if new_start.tzinfo is None:
            new_start = new_start.replace(tzinfo=timezone.utc)
        if new_end.tzinfo is None:
            new_end = new_end.replace(tzinfo=timezone.utc)

        # Find overlapping events via repository (selected calendars only)
        overlapping_events = self.repo.find_overlapping(db, new_event.user_id, new_start, new_end)
        # Don't conflict with self (only if the event has an ID)
        if getattr(new_event, 'id', None):
            overlapping_events = [e for e in overlapping_events if e.id != new_event.id]

        return overlapping_events
    
    def suggest_resolution(self, db: Session, conflicting_event: models.Event, 
                          limit: int = 5) -> List[Dict]:
        """
        Suggest alternative time slots for a conflicting event.
        
        Args:
            db: Database session
            conflicting_event: Event that has conflicts
            limit: Maximum number of suggestions
            
        Returns:
            List of alternative time slot suggestions with scores
        """
        # Get all existing events to avoid new conflicts
        user_id = conflicting_event.user_id
        now = datetime.now(timezone.utc)
        end_window = now + timedelta(days=14)  # Look ahead 2 weeks

        existing_events = self.repo.find_future_events(db, user_id, now, end_window, exclude_event_id=conflicting_event.id)

        # Create availability windows for next 2 weeks (working hours)
        availability = []
        for day in range(14):
            day_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day)
            day_end = day_start.replace(hour=17)  # 9 AM to 5 PM

            # Skip weekends (rough approximation)
            if day_start.weekday() < 5:  # Monday = 0, Friday = 4
                availability.append({"start": day_start, "end": day_end})

        # Create a task-like object for the recommendation engine
        duration_minutes = int((conflicting_event.end_at - conflicting_event.start_at).total_seconds() / 60)

        # Mock a task object with the properties needed by the recommendation engine
        class MockTask:
            def __init__(self, event):
                self.estimated_minutes = duration_minutes
                self.priority = 3  # Default priority
                self.due_at = None  # No specific due date
                self.energy_tag = None
                if event.type == "FOCUS":
                    self.energy_tag = "deep"
                elif event.type == "MEETING":
                    self.priority = 2  # Higher priority for meetings

        mock_task = MockTask(conflicting_event)

        # Get recommendations
        suggestions = compute_slots(
            mock_task,
            availability,
            limit=limit,
            existing_events=existing_events,
        )

        return suggestions
    
    def validate_event_creation(self, db: Session, new_event: models.Event, 
                               allow_focus_override: bool = False):
        """
        Validate if a new event can be created without unacceptable conflicts.
        
        Args:
            db: Database session
            new_event: Event to validate
            allow_focus_override: Whether to allow overriding FOCUS blocks
            
        Raises:
            ConflictDetected: If conflicts are detected and not allowed
        """
        conflicts = self.detect_conflicts(db, new_event)
        
        if not conflicts:
            return  # No conflicts
        
        # Check for FOCUS time conflicts (but only prevent non-FOCUS events from conflicting)
        focus_conflicts = [c for c in conflicts if c.type == "FOCUS"]
        
        if focus_conflicts and new_event.type != "FOCUS" and not allow_focus_override:
            raise ConflictDetected(
                f"FOCUS time is protected. Cannot create event during focus blocks: "
                f"{[c.title for c in focus_conflicts]}"
            )
        
        # For now, we allow other types of conflicts with warnings
        # In the future, this could be more sophisticated
    
    def analyze_conflicts(self, conflicts: List[models.Event], 
                         new_event: models.Event) -> Dict:
        """
        Analyze conflicts and provide severity scoring.
        
        Args:
            conflicts: List of conflicting events
            new_event: The event causing conflicts
            
        Returns:
            Analysis dictionary with severity metrics
        """
        analysis = {
            "total_conflicts": len(conflicts),
            "focus_conflicts": 0,
            "meeting_conflicts": 0,
            "general_conflicts": 0,
            "severity_score": 0.0
        }
        
        for conflict in conflicts:
            if conflict.type == "FOCUS":
                analysis["focus_conflicts"] += 1
                analysis["severity_score"] += 0.8  # High penalty for focus conflicts
            elif conflict.type == "MEETING":
                analysis["meeting_conflicts"] += 1
                analysis["severity_score"] += 0.5  # Medium penalty for meeting conflicts
            else:
                analysis["general_conflicts"] += 1
                analysis["severity_score"] += 0.2  # Low penalty for general conflicts
        
        # Normalize severity score
        if len(conflicts) > 0:
            analysis["severity_score"] = analysis["severity_score"] / len(conflicts)
        
        return analysis