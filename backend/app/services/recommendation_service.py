from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

SLOT_GRANULARITY_MIN = 15

class SlotSuggestion(dict):
    pass

class NoAvailability(Exception):
    pass

def compute_slots(task, availability_windows: List[Dict], limit: int = 5, existing_events: Optional[List] = None):
    """
    Compute optimal slots for a task given availability windows and existing events.
    
    Args:
        task: Task object with priority, due_at, estimated_minutes, etc.
        availability_windows: List of dicts with 'start' and 'end' datetime
        limit: Maximum number of slots to return
        existing_events: List of existing Event objects to avoid conflicts
    """
    if existing_events is None:
        existing_events = []
    
    required = task.estimated_minutes or 30
    slots = []
    
    for w in availability_windows:
        cur = w['start']
        while cur + timedelta(minutes=required) <= w['end']:
            end = cur + timedelta(minutes=required)
            
            # Check if this slot conflicts with existing events
            conflicts = _check_slot_conflicts(cur, end, existing_events)
            if not conflicts:
                score = score_slot(task, cur, end, existing_events)
                slots.append({
                    "startAt": cur.isoformat(), 
                    "endAt": end.isoformat(), 
                    "score": round(score, 4)
                })
                
            if len(slots) >= limit * 3:  # gather some extra for sorting
                break
            cur += timedelta(minutes=SLOT_GRANULARITY_MIN)
    
    if not slots:
        return []
    
    # Sort by score descending
    slots.sort(key=lambda x: x['score'], reverse=True)
    
    # Deduplicate adjacent slots
    dedup = []
    for s in slots:
        if not any(abs(parse_iso(s['startAt']) - parse_iso(d['startAt'])).total_seconds() < SLOT_GRANULARITY_MIN*60 for d in dedup):
            dedup.append(s)
        if len(dedup) >= limit:
            break
    return dedup

def score_slot(task, start, end, existing_events: Optional[List] = None):
    """
    Score a potential slot for a task based on multiple factors:
    - Due date urgency
    - Priority weighting  
    - Energy tag matching
    - Working hours preference
    - Focus time protection
    """
    if existing_events is None:
        existing_events = []
        
    base_score = 1.0
    
    # 1. Due date urgency factor
    if task.due_at:
        due_at = task.due_at
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        hours_left = (due_at - start).total_seconds() / 3600
        if hours_left > 0:
            # More urgent as due date approaches, capped at 72h
            urgency_factor = max(0, 1 - min(hours_left / 72, 1))
            base_score += urgency_factor * 0.5  # Up to 0.5 bonus
    
    # 2. Priority weighting (priority 1 is highest)
    priority_factor = (6 - task.priority) * 0.1  # priority 1 -> 0.5, priority 5 -> 0.1
    base_score += priority_factor
    
    # 3. Energy tag matching
    energy_bonus = _calculate_energy_bonus(task, start)
    base_score += energy_bonus
    
    # 4. Working hours preference
    working_hours_bonus = _calculate_working_hours_bonus(start)
    base_score += working_hours_bonus
    
    # 5. Focus time protection penalty
    focus_penalty = _calculate_focus_penalty(start, end, existing_events)
    base_score *= focus_penalty  # Multiplicative penalty
    
    return max(base_score, 0.01)  # Minimum score

def _check_slot_conflicts(start, end, existing_events):
    """Check if a slot conflicts with any existing events"""
    for event in existing_events:
        # Ensure all datetimes are timezone-aware for comparison
        event_start = event.start_at
        event_end = event.end_at
        
        # If event datetimes are naive, make them UTC
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=timezone.utc)
        if event_end.tzinfo is None:
            event_end = event_end.replace(tzinfo=timezone.utc)
            
        if start < event_end and end > event_start:
            return True
    return False

def _calculate_energy_bonus(task, start):
    """Calculate bonus based on energy tag matching with time of day"""
    if not hasattr(task, 'energy_tag') or not task.energy_tag:
        return 0.0
    
    hour = start.hour
    
    if task.energy_tag == "morning":
        if 6 <= hour <= 10:
            return 0.3  # Strong morning preference
        elif 11 <= hour <= 14:
            return 0.1  # Moderate mid-day preference
        else:
            return -0.1  # Slight penalty for non-morning
    
    elif task.energy_tag == "afternoon":
        if 13 <= hour <= 17:
            return 0.3  # Strong afternoon preference
        elif 11 <= hour <= 12 or 18 <= hour <= 19:
            return 0.1  # Moderate adjacent hours
        else:
            return -0.1  # Slight penalty for non-afternoon
    
    elif task.energy_tag == "deep":
        # Deep work prefers quiet hours
        if 6 <= hour <= 9 or 19 <= hour <= 21:
            return 0.2  # Early morning or evening
        elif 10 <= hour <= 16:
            return -0.2  # Penalize busy mid-day
    
    return 0.0

def _calculate_working_hours_bonus(start):
    """Give bonus for typical working hours"""
    hour = start.hour
    
    if 9 <= hour <= 17:  # Standard work hours
        return 0.2
    elif 8 <= hour <= 8 or 18 <= hour <= 19:  # Extended work hours
        return 0.1
    else:
        return -0.1  # Penalty for off-hours

def _calculate_focus_penalty(start, end, existing_events):
    """Apply heavy penalty if slot overlaps with FOCUS events"""
    for event in existing_events:
        if hasattr(event, 'type') and event.type == 'FOCUS':
            # Ensure timezone consistency
            event_start = event.start_at
            event_end = event.end_at
            
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
            
            # Check overlap
            if start < event_end and end > event_start:
                return 0.1  # Heavy penalty (90% reduction)
    
    return 1.0  # No penalty

def parse_iso(s: str):
    """Parse ISO format datetime string"""
    if s.endswith('Z'):
        s = s.replace('Z', '+00:00')
    return datetime.fromisoformat(s)
