import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from app.main import app

client = TestClient(app)

def test_focus_protection_blocks_conflicts():
    """Test that FOCUS events protect against conflicting meetings"""
    # Create a FOCUS event
    base_time = datetime.now(timezone.utc)
    focus_start = base_time + timedelta(hours=2)
    focus_end = focus_start + timedelta(hours=2)
    
    focus_event = {
        "title": "Deep Work Session",
        "startAt": focus_start.isoformat(),
        "endAt": focus_end.isoformat(),
        "type": "FOCUS"
    }
    
    focus_response = client.post("/events", json=focus_event)
    print(f"Focus response status: {focus_response.status_code}")
    print(f"Focus response body: {focus_response.text}")
    assert focus_response.status_code == 201
    
    # Try to create a meeting that overlaps with FOCUS time
    meeting_start = focus_start + timedelta(minutes=30)
    meeting_end = meeting_start + timedelta(hours=1)
    
    conflicting_meeting = {
        "title": "Team Meeting",
        "startAt": meeting_start.isoformat(), 
        "endAt": meeting_end.isoformat(),
        "type": "MEETING"
    }
    
    conflict_response = client.post("/events", json=conflicting_meeting)
    
    # Should be blocked by focus protection
    assert conflict_response.status_code == 409
    
    error_data = conflict_response.json()
    assert error_data["detail"]["code"] == "FOCUS_PROTECTED"
    assert "FOCUS time is protected" in error_data["detail"]["message"]

def test_focus_protection_allows_override():
    """Test that FOCUS conflicts can be overridden when explicitly allowed"""
    # Create a FOCUS event
    base_time = datetime.now(timezone.utc)
    focus_start = base_time + timedelta(hours=3)
    focus_end = focus_start + timedelta(hours=2)
    
    focus_event = {
        "title": "Deep Work Session",
        "startAt": focus_start.isoformat(),
        "endAt": focus_end.isoformat(),
        "type": "FOCUS"
    }
    
    focus_response = client.post("/events", json=focus_event)
    assert focus_response.status_code == 201
    
    # Try to create meeting with override flag
    meeting_start = focus_start + timedelta(minutes=30)
    meeting_end = meeting_start + timedelta(hours=1)
    
    urgent_meeting = {
        "title": "Urgent Client Call",
        "startAt": meeting_start.isoformat(),
        "endAt": meeting_end.isoformat(),
        "type": "MEETING",
        "overrideFocusProtection": True
    }
    
    override_response = client.post("/events", json=urgent_meeting)
    
    # Should be allowed with override
    assert override_response.status_code == 201
    
    created_meeting = override_response.json()
    assert created_meeting["title"] == "Urgent Client Call"

def test_no_conflict_with_non_focus_events():
    """Test that regular events don't trigger focus protection"""
    # Create a regular meeting
    base_time = datetime.now(timezone.utc)
    meeting1_start = base_time + timedelta(hours=4)
    meeting1_end = meeting1_start + timedelta(hours=1)
    
    meeting1 = {
        "title": "Regular Meeting", 
        "startAt": meeting1_start.isoformat(),
        "endAt": meeting1_end.isoformat(),
        "type": "MEETING"
    }
    
    response1 = client.post("/events", json=meeting1)
    assert response1.status_code == 201
    
    # Create another meeting that overlaps (should be allowed for now)
    meeting2_start = meeting1_start + timedelta(minutes=30)
    meeting2_end = meeting2_start + timedelta(hours=1)
    
    meeting2 = {
        "title": "Another Meeting",
        "startAt": meeting2_start.isoformat(),
        "endAt": meeting2_end.isoformat(),
        "type": "MEETING"
    }
    
    response2 = client.post("/events", json=meeting2)
    
    # Should be allowed (we only protect FOCUS events for now)
    assert response2.status_code == 201

def test_focus_protection_exact_boundaries():
    """Test focus protection at exact time boundaries"""
    base_time = datetime.now(timezone.utc)
    focus_start = base_time + timedelta(hours=5)
    focus_end = focus_start + timedelta(hours=1)
    
    # Create FOCUS event
    focus_event = {
        "title": "Focused Work",
        "startAt": focus_start.isoformat(),
        "endAt": focus_end.isoformat(), 
        "type": "FOCUS"
    }
    
    focus_response = client.post("/events", json=focus_event)
    assert focus_response.status_code == 201
    
    # Meeting that starts exactly when focus ends (should be allowed)
    meeting_after = {
        "title": "Meeting After Focus",
        "startAt": focus_end.isoformat(),
        "endAt": (focus_end + timedelta(hours=1)).isoformat(),
        "type": "MEETING"
    }
    
    after_response = client.post("/events", json=meeting_after)
    assert after_response.status_code == 201  # Should be allowed
    
    # Meeting that ends exactly when focus starts (should be allowed)
    meeting_before = {
        "title": "Meeting Before Focus", 
        "startAt": (focus_start - timedelta(hours=1)).isoformat(),
        "endAt": focus_start.isoformat(),
        "type": "MEETING"
    }
    
    before_response = client.post("/events", json=meeting_before)
    assert before_response.status_code == 201  # Should be allowed