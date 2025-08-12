import pytest
from unittest.mock import Mock, MagicMock
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

def test_detect_conflict_with_overlapping_events():
    """Test that overlapping events are detected as conflicts"""
    db_mock = Mock()
    service = ConflictService()
    
    # Create a new event that overlaps with existing ones
    new_event = make_event(2, 1, "MEETING", "New Meeting")  # 2-3 PM
    
    # Mock existing events: one that overlaps
    existing_events = [
        make_event(1, 2, "GENERAL", "Existing Event")  # 1-3 PM (overlaps)
    ]
    
    # Mock the full chain: query().filter().filter().filter().filter().all()
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    # Chain the filters properly
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    conflicts = service.detect_conflicts(db_mock, new_event)
    
    assert len(conflicts) == 1
    assert conflicts[0].id == "event-1"

def test_detect_no_conflict_with_non_overlapping_events():
    """Test that non-overlapping events don't create conflicts"""
    db_mock = Mock()
    service = ConflictService()
    
    # Create a new event
    new_event = make_event(4, 1, "MEETING", "New Meeting")  # 4-5 PM
    
    # Mock existing events: none that overlap (should return empty due to SQL filter)
    existing_events = []  # No overlapping events found by database query
    
    # Mock the full chain
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    conflicts = service.detect_conflicts(db_mock, new_event)
    
    assert len(conflicts) == 0

def test_detect_multiple_conflicts():
    """Test detection of multiple overlapping events"""
    db_mock = Mock()
    service = ConflictService()
    
    # New event that overlaps with multiple existing events
    new_event = make_event(2, 3, "MEETING", "Long Meeting")  # 2-5 PM
    
    # Multiple overlapping events (only overlapping ones returned by DB)
    existing_events = [
        make_event(1, 2, "GENERAL", "Event 1"),    # 1-3 PM (overlaps)
        make_event(3, 2, "FOCUS", "Event 2"),      # 3-5 PM (overlaps)
    ]
    
    # Mock the chain
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    conflicts = service.detect_conflicts(db_mock, new_event)
    
    assert len(conflicts) == 2
    conflict_ids = [c.id for c in conflicts]
    assert "event-1" in conflict_ids
    assert "event-3" in conflict_ids

def test_suggest_conflict_resolution():
    """Test conflict resolution suggestions"""
    db_mock = Mock()
    service = ConflictService()
    
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
        suggestions = service.suggest_resolution(db_mock, conflicting_event)
        
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
    db_mock = Mock()
    service = ConflictService()
    
    # Try to create meeting during focus time
    new_event = make_event(2, 1, "MEETING", "Team Meeting")  # 2-3 PM
    
    # Existing focus block
    existing_events = [
        make_event(1.5, 2, "FOCUS", "Deep Work")  # 1:30-3:30 PM (overlaps)
    ]
    
    # Mock the chain
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    # Should detect conflict
    conflicts = service.detect_conflicts(db_mock, new_event)
    assert len(conflicts) == 1
    
    # Should strongly recommend rescheduling (not allowed to override FOCUS)
    with pytest.raises(ConflictDetected) as exc_info:
        service.validate_event_creation(db_mock, new_event, allow_focus_override=False)
    
    assert "FOCUS time is protected" in str(exc_info.value)

def test_allow_focus_override():
    """Test that FOCUS conflicts can be overridden when explicitly allowed"""
    db_mock = Mock()
    service = ConflictService()
    
    # Try to create meeting during focus time
    new_event = make_event(2, 1, "MEETING", "Urgent Meeting")
    
    # Existing focus block
    existing_events = [
        make_event(1.5, 2, "FOCUS", "Deep Work")
    ]
    
    # Mock the chain
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    # Should be allowed with explicit override
    try:
        service.validate_event_creation(db_mock, new_event, allow_focus_override=True)
        # Should not raise exception
    except ConflictDetected:
        pytest.fail("Should allow FOCUS override when explicitly enabled")

def test_conflict_severity_scoring():
    """Test that conflicts are scored by severity"""
    db_mock = Mock()
    service = ConflictService()
    
    new_event = make_event(2, 2, "MEETING", "Long Meeting")  # 2-4 PM
    
    # Different types of conflicting events (only overlapping ones returned by DB)
    existing_events = [
        make_event(1, 2, "GENERAL", "Regular Event"),    # 1-3 PM
        make_event(3, 2, "FOCUS", "Deep Work"),          # 3-5 PM  
        make_event(1.5, 1, "MEETING", "Important Meeting")  # 1:30-2:30 PM
    ]
    
    # Mock the chain
    filter_mock = Mock()
    filter_mock.all.return_value = existing_events
    
    query_mock = Mock()
    query_mock.filter.return_value.filter.return_value.filter.return_value.filter.return_value = filter_mock
    
    db_mock.query.return_value = query_mock
    
    conflicts = service.detect_conflicts(db_mock, new_event)
    
    # Should detect all 3 conflicts
    assert len(conflicts) == 3
    
    # Get conflict analysis with severity
    analysis = service.analyze_conflicts(conflicts, new_event)
    
    assert "severity_score" in analysis
    assert "focus_conflicts" in analysis
    assert "meeting_conflicts" in analysis
    
    # FOCUS conflicts should be flagged as high severity
    assert analysis["focus_conflicts"] > 0