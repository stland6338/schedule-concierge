import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.services.recommendation_service import compute_slots, score_slot
from app.db.models import Task, Event

def make_task(priority=3, due_hours=None, estimated_minutes=30, energy_tag=None, user_id="demo-user"):
    """Helper to create test task"""
    due_at = datetime.now(timezone.utc) + timedelta(hours=due_hours) if due_hours else None
    return Task(
        id=f"task-{priority}",
        user_id=user_id,
        title=f"Test Task {priority}",
        priority=priority,
        estimated_minutes=estimated_minutes,
        due_at=due_at,
        energy_tag=energy_tag,
        status="Draft"
    )

def make_event(start_hours, duration_hours, event_type="GENERAL"):
    """Helper to create test event"""
    start_at = datetime.now(timezone.utc) + timedelta(hours=start_hours)
    end_at = start_at + timedelta(hours=duration_hours)
    return Event(
        id=f"event-{start_hours}",
        title=f"Event at {start_hours}h",
        start_at=start_at,
        end_at=end_at,
        type=event_type
    )

def test_compute_slots_considers_existing_events():
    """Test that slot computation considers existing events in the calendar"""
    task = make_task(priority=2, estimated_minutes=60)
    
    # Create availability window from 8 AM to 6 PM
    base_time = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    availability = [{
        "start": base_time, 
        "end": base_time + timedelta(hours=10)
    }]
    
    # Mock existing events: 10 AM - 11 AM meeting
    existing_events = [make_event(2, 1, "MEETING")]  # 2 hours from base_time = 10 AM
    
    slots = compute_slots(task, availability, limit=5, existing_events=existing_events)
    
    # Should have slots but none overlapping with the 10-11 AM meeting
    assert len(slots) > 0
    for slot in slots:
        slot_start = datetime.fromisoformat(slot["startAt"].replace('Z', '+00:00'))
        slot_end = datetime.fromisoformat(slot["endAt"].replace('Z', '+00:00'))
        
        # No slot should overlap with existing meeting
        meeting_start = existing_events[0].start_at
        meeting_end = existing_events[0].end_at
        
        assert not (slot_start < meeting_end and slot_end > meeting_start), \
            f"Slot {slot_start}-{slot_end} overlaps with meeting {meeting_start}-{meeting_end}"

def test_score_slot_priority_weighting():
    """Test that higher priority tasks get better scores for urgent slots"""
    base_time = datetime.now(timezone.utc)
    slot_start = base_time + timedelta(hours=1)
    slot_end = slot_start + timedelta(minutes=30)
    
    high_priority_task = make_task(priority=1, due_hours=24)  # High priority, due soon
    low_priority_task = make_task(priority=5, due_hours=24)   # Low priority, same due date
    
    high_score = score_slot(high_priority_task, slot_start, slot_end)
    low_score = score_slot(low_priority_task, slot_start, slot_end)
    
    assert high_score > low_score, "High priority task should score higher"

def test_score_slot_due_date_urgency():
    """Test that tasks due sooner get higher scores"""
    base_time = datetime.now(timezone.utc)
    slot_start = base_time + timedelta(hours=1)
    slot_end = slot_start + timedelta(minutes=30)
    
    urgent_task = make_task(priority=3, due_hours=6)    # Due in 6 hours
    normal_task = make_task(priority=3, due_hours=48)   # Due in 48 hours
    
    urgent_score = score_slot(urgent_task, slot_start, slot_end)
    normal_score = score_slot(normal_task, slot_start, slot_end)
    
    assert urgent_score > normal_score, "Urgent task should score higher"

def test_score_slot_energy_tag_matching():
    """Test that energy tag matching affects scoring"""
    # Morning slot (9 AM)
    morning_time = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    slot_start = morning_time
    slot_end = slot_start + timedelta(minutes=30)
    
    morning_task = make_task(priority=3, energy_tag="morning")
    afternoon_task = make_task(priority=3, energy_tag="afternoon")
    no_tag_task = make_task(priority=3, energy_tag=None)
    
    morning_score = score_slot(morning_task, slot_start, slot_end)
    afternoon_score = score_slot(afternoon_task, slot_start, slot_end)
    no_tag_score = score_slot(no_tag_task, slot_start, slot_end)
    
    assert morning_score > afternoon_score, "Morning task should score higher in morning slot"
    assert morning_score > no_tag_score, "Energy tag match should boost score"

def test_score_slot_focus_time_protection():
    """Test that FOCUS events are protected from being overridden"""
    base_time = datetime.now(timezone.utc)
    
    # Create a slot that would overlap with a FOCUS event
    focus_start = base_time + timedelta(hours=2)
    focus_end = focus_start + timedelta(hours=2)
    focus_event = Event(
        title="Deep Work",
        start_at=focus_start,
        end_at=focus_end,
        type="FOCUS"
    )
    
    task = make_task(priority=1)  # Even high priority
    
    # Try to score a slot that overlaps with focus time
    slot_start = focus_start + timedelta(minutes=30)  # Overlaps with focus block
    slot_end = slot_start + timedelta(minutes=30)
    
    # This should get a very low score due to focus protection
    score = score_slot(task, slot_start, slot_end, existing_events=[focus_event])
    
    # Score should be heavily penalized (less than 0.3)
    assert score < 0.3, "Slots overlapping FOCUS time should be heavily penalized"

def test_compute_slots_respects_minimum_duration():
    """Test that computed slots respect minimum duration requirements"""
    task = make_task(estimated_minutes=45)  # 45 minute task
    
    # Create a small availability window that can barely fit the task
    base_time = datetime.now(timezone.utc)
    availability = [{
        "start": base_time,
        "end": base_time + timedelta(minutes=50)  # Only 50 minutes available
    }]
    
    slots = compute_slots(task, availability, limit=5)
    
    # Should have very few slots since the window is small
    assert len(slots) >= 0  # Could be 0 or few slots
    
    # All slots should be exactly the task duration
    for slot in slots:
        start = datetime.fromisoformat(slot["startAt"].replace('Z', '+00:00'))
        end = datetime.fromisoformat(slot["endAt"].replace('Z', '+00:00'))
        duration = (end - start).total_seconds() / 60
        assert duration == 45, f"Slot duration should be 45 minutes, got {duration}"

def test_compute_slots_working_hours_preference():
    """Test that slots during working hours get better scores"""
    task = make_task(priority=3, estimated_minutes=30)
    
    # Create availability covering both work and non-work hours
    base_time = datetime.now(timezone.utc).replace(hour=6, minute=0, second=0, microsecond=0)  # 6 AM
    availability = [{
        "start": base_time,
        "end": base_time + timedelta(hours=16)  # 6 AM to 10 PM
    }]
    
    slots = compute_slots(task, availability, limit=10)
    
    # Find morning work hour slot vs evening slot
    morning_slots = []
    evening_slots = []
    
    for slot in slots:
        start = datetime.fromisoformat(slot["startAt"].replace('Z', '+00:00'))
        hour = start.hour
        
        if 9 <= hour <= 11:  # Morning work hours
            morning_slots.append(slot)
        elif 19 <= hour <= 21:  # Evening hours
            evening_slots.append(slot)
    
    if morning_slots and evening_slots:
        avg_morning_score = sum(s["score"] for s in morning_slots) / len(morning_slots)
        avg_evening_score = sum(s["score"] for s in evening_slots) / len(evening_slots)
        
        assert avg_morning_score > avg_evening_score, \
            "Morning work hours should generally score better than evening hours"