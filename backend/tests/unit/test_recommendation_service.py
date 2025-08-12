from app.services.recommendation_service import compute_slots, score_slot
from types import SimpleNamespace
from datetime import datetime, timedelta

def make_task(priority=3, due_hours=None, estimated_minutes=30):
    due_at = datetime.utcnow() + timedelta(hours=due_hours) if due_hours else None
    return SimpleNamespace(estimated_minutes=estimated_minutes, priority=priority, due_at=due_at)

def test_compute_slots_basic():
    task = make_task()
    now = datetime.utcnow()
    windows = [{"start": now, "end": now + timedelta(hours=2)}]
    slots = compute_slots(task, windows, limit=3)
    assert len(slots) > 0
    assert all('score' in s for s in slots)

def test_score_slot_due_urgency_increases_score():
    task1 = make_task(due_hours=10)
    task2 = make_task(due_hours=70)
    now = datetime.utcnow()
    s1 = score_slot(task1, now, now + timedelta(minutes=30))
    s2 = score_slot(task2, now, now + timedelta(minutes=30))
    assert s1 > s2
