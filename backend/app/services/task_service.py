from sqlalchemy.orm import Session
from ..db import models
from datetime import datetime

class TaskNotFound(Exception):
    pass

def create_task(db: Session, user_id: str, title: str, due_at=None, priority: int = 3, estimated_minutes=None, energy_tag=None):
    task = models.Task(user_id=user_id, title=title, due_at=due_at, priority=priority, estimated_minutes=estimated_minutes, energy_tag=energy_tag)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def get_task(db: Session, task_id: str):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise TaskNotFound()
    return task
