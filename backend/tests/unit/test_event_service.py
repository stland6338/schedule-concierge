import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from app.services.event_service import EventService, EventNotFound
from app.db.models import Event

def test_create_event():
    """Test event creation"""
    db_mock = Mock()
    service = EventService()
    
    # Mock the created event
    created_event = Event(
        id="event-123",
        user_id="user-1",
        calendar_id="cal-1", 
        title="Test Event",
        description="Test Description",
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc),
        type="MEETING"
    )
    
    db_mock.add.return_value = None
    db_mock.commit.return_value = None
    db_mock.refresh.return_value = None
    
    # Configure the mock to return our event when refresh is called
    def refresh_side_effect(event):
        event.id = "event-123"
        event.created_at = datetime.now(timezone.utc)
    
    db_mock.refresh.side_effect = refresh_side_effect
    
    result = service.create_event(
        db=db_mock,
        user_id="user-1",
        calendar_id="cal-1",
        title="Test Event",
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc),
        type="MEETING",
        description="Test Description"
    )
    
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()

def test_get_event_success():
    """Test successful event retrieval"""
    db_mock = Mock()
    service = EventService()
    
    event = Event(id="event-123", title="Test Event")
    db_mock.query.return_value.filter.return_value.first.return_value = event
    
    result = service.get_event(db_mock, "event-123")
    
    assert result == event
    db_mock.query.assert_called_once()

def test_get_event_not_found():
    """Test event not found scenario"""
    db_mock = Mock()
    service = EventService()
    
    db_mock.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(EventNotFound):
        service.get_event(db_mock, "nonexistent-id")

def test_update_event():
    """Test event update"""
    db_mock = Mock()
    service = EventService()
    
    existing_event = Event(
        id="event-123",
        title="Original Title",
        type="GENERAL"
    )
    
    db_mock.query.return_value.filter.return_value.first.return_value = existing_event
    db_mock.commit.return_value = None
    db_mock.refresh.return_value = None
    
    result = service.update_event(
        db=db_mock,
        event_id="event-123",
        title="Updated Title",
        type="MEETING"
    )
    
    assert existing_event.title == "Updated Title"
    assert existing_event.type == "MEETING"
    db_mock.commit.assert_called_once()
    db_mock.refresh.assert_called_once()

def test_delete_event():
    """Test event deletion"""
    db_mock = Mock()
    service = EventService()
    
    existing_event = Event(id="event-123", title="To Delete")
    db_mock.query.return_value.filter.return_value.first.return_value = existing_event
    db_mock.delete.return_value = None
    db_mock.commit.return_value = None
    
    service.delete_event(db_mock, "event-123")
    
    db_mock.delete.assert_called_once_with(existing_event)
    db_mock.commit.assert_called_once()