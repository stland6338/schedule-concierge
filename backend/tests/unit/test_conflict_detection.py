import pytest
from datetime import datetime, timedelta, timezone
from app.services.conflict_service import ConflictService, ConflictDetected
from app.db.models import Event, Task

def make_event(start_hours, duration_hours, event_type="GENERAL", title="Test Event"):
    """Helper to create test event"""
    start_at = datetime.now(timezone.utc) + timedelta(hours=start_hours)
    end_at = start_at + timedelta(hours=duration_hours)
    return Event(
        id=f"event-{start_hours}",
        title=title,
        start_at=start_at,
        end_at=end_at,
        type=event_type,
        user_id="demo-user"
    )


class FakeEventRepository:
    def __init__(self):
        self.events_by_user = {}

    def add(self, user_id, event):
        self.events_by_user.setdefault(user_id, []).append(event)

    def find_overlapping(self, db, user_id: str, start: datetime, end: datetime):
        events = self.events_by_user.get(user_id, [])
        return [e for e in events if e.start_at < end and e.end_at > start]

    def find_future_events(self, db, user_id: str, now: datetime, end_window: datetime, exclude_event_id: str | None = None):
        events = self.events_by_user.get(user_id, [])
        result = []
        for e in events:
            if exclude_event_id and getattr(e, 'id', None) == exclude_event_id:
                continue
            if e.start_at >= now and e.start_at <= end_window:
                result.append(e)
        return result

def test_detect_conflict_with_overlapping_events():
    """Test that overlapping events are detected as conflicts"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # Create a new event that overlaps with existing ones
    new_event = make_event(2, 1, "MEETING", "New Meeting")  # 2-3 PM
    
    # Existing event overlaps
    repo.add("demo-user", make_event(1, 2, "GENERAL", "Existing Event"))
    conflicts = service.detect_conflicts(None, new_event)
    
    assert len(conflicts) == 1
    assert conflicts[0].id == "event-1"

def test_detect_no_conflict_with_non_overlapping_events():
    """Test that non-overlapping events don't create conflicts"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # Create a new event
    new_event = make_event(4, 1, "MEETING", "New Meeting")  # 4-5 PM
    
    # No existing events
    conflicts = service.detect_conflicts(None, new_event)
    
    assert len(conflicts) == 0

def test_detect_multiple_conflicts():
    """Test detection of multiple overlapping events"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # New event that overlaps with multiple existing events
    new_event = make_event(2, 3, "MEETING", "Long Meeting")  # 2-5 PM
    
    # Multiple overlapping events
    repo.add("demo-user", make_event(1, 2, "GENERAL", "Event 1"))
    repo.add("demo-user", make_event(3, 2, "FOCUS", "Event 2"))
    conflicts = service.detect_conflicts(None, new_event)
    
    assert len(conflicts) == 2
    conflict_ids = [c.id for c in conflicts]
    assert "event-1" in conflict_ids
    assert "event-3" in conflict_ids

def test_suggest_conflict_resolution():
    """Test conflict resolution suggestions"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # Conflicting event
    conflicting_event = make_event(2, 1, "MEETING", "Meeting")  # 2-3 PM
    
    # Mock recommendation service call
    from app.services.recommendation_service import compute_slots
    original_compute_slots = compute_slots
    
    def mock_compute_slots(task_like, availability, limit=5, existing_events=None):
        # Return some alternative time slots
        base_time = datetime.now(timezone.utc)
        return [
            {
                "startAt": (base_time + timedelta(hours=4)).isoformat(),
                "endAt": (base_time + timedelta(hours=5)).isoformat(),
                "score": 0.8
            },
            {
                "startAt": (base_time + timedelta(hours=6)).isoformat(),
                "endAt": (base_time + timedelta(hours=7)).isoformat(),
                "score": 0.7
            }
        ]
    
    # Patch the function temporarily
    import app.services.recommendation_service
    app.services.recommendation_service.compute_slots = mock_compute_slots
    
    try:
        suggestions = service.suggest_resolution(None, conflicting_event)
        
        assert len(suggestions) > 0
        assert all("startAt" in s for s in suggestions)
        assert all("endAt" in s for s in suggestions)
        assert all("score" in s for s in suggestions)
        
        # Should be sorted by score descending
        scores = [s["score"] for s in suggestions]
        assert scores == sorted(scores, reverse=True)
        
    finally:
        # Restore original function
        app.services.recommendation_service.compute_slots = original_compute_slots

def test_focus_time_protection():
    """Test that FOCUS events are strongly protected from conflicts"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # Try to create meeting during focus time
    new_event = make_event(2, 1, "MEETING", "Team Meeting")  # 2-3 PM
    
    # Existing focus block
    repo.add("demo-user", make_event(1.5, 2, "FOCUS", "Deep Work"))
    
    # Should detect conflict
    conflicts = service.detect_conflicts(None, new_event)
    assert len(conflicts) == 1
    
    # Should strongly recommend rescheduling (not allowed to override FOCUS)
    with pytest.raises(ConflictDetected) as exc_info:
        service.validate_event_creation(None, new_event, allow_focus_override=False)
    
    assert "FOCUS time is protected" in str(exc_info.value)

def test_allow_focus_override():
    """Test that FOCUS conflicts can be overridden when explicitly allowed"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    # Try to create meeting during focus time
    new_event = make_event(2, 1, "MEETING", "Urgent Meeting")
    
    # Existing focus block
    repo.add("demo-user", make_event(1.5, 2, "FOCUS", "Deep Work"))
    
    # Should be allowed with explicit override
    try:
        service.validate_event_creation(None, new_event, allow_focus_override=True)
        # Should not raise exception
    except ConflictDetected:
        pytest.fail("Should allow FOCUS override when explicitly enabled")

def test_conflict_severity_scoring():
    """Test that conflicts are scored by severity"""
    repo = FakeEventRepository()
    service = ConflictService(repository=repo)
    
    new_event = make_event(2, 2, "MEETING", "Long Meeting")  # 2-4 PM
    
    # Different types of conflicting events
    repo.add("demo-user", make_event(1, 2, "GENERAL", "Regular Event"))
    repo.add("demo-user", make_event(3, 2, "FOCUS", "Deep Work"))
    repo.add("demo-user", make_event(1.5, 1, "MEETING", "Important Meeting"))
    conflicts = service.detect_conflicts(None, new_event)
    
    # Should detect all 3 conflicts
    assert len(conflicts) == 3
    
    # Get conflict analysis with severity
    analysis = service.analyze_conflicts(conflicts, new_event)
    
    assert "severity_score" in analysis
    assert "focus_conflicts" in analysis
    assert "meeting_conflicts" in analysis
    
    # FOCUS conflicts should be flagged as high severity
    assert analysis["focus_conflicts"] > 0