import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from app.main import app

client = TestClient(app)

def test_create_event():
    """Test creating a new event"""
    event_data = {
        "title": "Team Meeting",
        "startAt": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "endAt": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "type": "MEETING"
    }
    
    response = client.post("/events", json=event_data)
    assert response.status_code == 201
    
    event = response.json()
    assert event["title"] == "Team Meeting"
    assert event["type"] == "MEETING"
    assert "id" in event
    assert "createdAt" in event

def test_get_event():
    """Test retrieving an event by ID"""
    # First create an event
    event_data = {
        "title": "Focus Time",
        "startAt": (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat(),
        "endAt": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
        "type": "FOCUS"
    }
    
    create_response = client.post("/events", json=event_data)
    assert create_response.status_code == 201
    created_event = create_response.json()
    
    # Then retrieve it
    get_response = client.get(f"/events/{created_event['id']}")
    assert get_response.status_code == 200
    
    retrieved_event = get_response.json()
    assert retrieved_event["id"] == created_event["id"]
    assert retrieved_event["title"] == "Focus Time"

def test_list_events():
    """Test listing events for a user"""
    response = client.get("/events")
    assert response.status_code == 200
    
    events = response.json()
    assert isinstance(events, list)

def test_update_event():
    """Test updating an existing event"""
    # Create event first
    event_data = {
        "title": "Original Title",
        "startAt": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
        "endAt": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "type": "GENERAL"
    }
    
    create_response = client.post("/events", json=event_data)
    created_event = create_response.json()
    
    # Update the event
    update_data = {
        "title": "Updated Title",
        "startAt": event_data["startAt"],
        "endAt": event_data["endAt"],
        "type": "MEETING"
    }
    
    update_response = client.put(f"/events/{created_event['id']}", json=update_data)
    assert update_response.status_code == 200
    
    updated_event = update_response.json()
    assert updated_event["title"] == "Updated Title"
    assert updated_event["type"] == "MEETING"

def test_delete_event():
    """Test deleting an event"""
    # Create event first
    event_data = {
        "title": "To Be Deleted",
        "startAt": (datetime.now(timezone.utc) + timedelta(hours=7)).isoformat(),
        "endAt": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
        "type": "GENERAL"
    }
    
    create_response = client.post("/events", json=event_data)
    created_event = create_response.json()
    
    # Delete the event
    delete_response = client.delete(f"/events/{created_event['id']}")
    assert delete_response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/events/{created_event['id']}")
    assert get_response.status_code == 404

def test_create_event_validation_error():
    """Test creating event with invalid data"""
    invalid_data = {
        "title": "",  # Empty title should fail
        "startAt": "invalid-date",
        "endAt": "invalid-date"
    }
    
    response = client.post("/events", json=invalid_data)
    assert response.status_code == 422  # Validation error

def test_get_nonexistent_event():
    """Test getting an event that doesn't exist"""
    response = client.get("/events/nonexistent-id")
    assert response.status_code == 404
    
    error_data = response.json()
    assert error_data["detail"]["code"] == "EVENT_NOT_FOUND"