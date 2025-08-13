from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..db.session import get_db
from ..db import models
from ..services.task_service import get_task, TaskNotFound
from ..services.recommendation_service import compute_slots
from .auth import get_current_user_optional

router = APIRouter(prefix="/slots")

@router.get("/suggest")
def suggest_slots(taskId: str = Query(...), limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db), current_user: models.User | None = Depends(get_current_user_optional)):
    try:
        task = get_task(db, taskId)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "task not found"})
    
    # Get user's existing events for conflict detection
    user_id = current_user.id if current_user else "demo-user"
    now = datetime.now(timezone.utc)
    end_window = now + timedelta(days=7)  # Look ahead 7 days
    
    existing_events = db.query(models.Event).filter(
        models.Event.user_id == user_id,
        models.Event.start_at >= now,
        models.Event.start_at <= end_window
    ).all()
    
    # Create availability windows - for now, use working hours each day
    availability = []
    for day in range(7):  # Next 7 days
        day_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day)
        day_end = day_start.replace(hour=17)  # 9 AM to 5 PM
        
        # Skip weekends (rough approximation)
        if day_start.weekday() < 5:  # Monday = 0, Friday = 4
            availability.append({"start": day_start, "end": day_end})
    
    slots = compute_slots(task, availability, limit=limit, existing_events=existing_events)
    return {"taskId": taskId, "slots": slots}
