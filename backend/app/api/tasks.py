from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..services import task_service

from ..db import models  # ensure models imported for metadata registration
from ..services.demo_user import get_or_create_demo_user
from .auth import get_current_user_optional

router = APIRouter(prefix="/tasks")

class TaskCreate(BaseModel):
    title: str
    dueAt: datetime | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimatedMinutes: int | None = Field(default=None, ge=5, le=480)
    energyTag: str | None = Field(default=None, description="Energy tag hint (deep/morning/afternoon etc)")

class TaskOut(BaseModel):
    id: str
    title: str
    dueAt: datetime | None = None
    priority: int
    estimatedMinutes: int | None = None
    status: str
    energyTag: str | None = None

@router.post("", response_model=TaskOut, status_code=201, response_model_by_alias=True)
def create_task(body: TaskCreate, db: Session = Depends(get_db), current_user: models.User | None = Depends(get_current_user_optional)):
    # current_user provided if authenticated; otherwise emulate legacy demo-user
    user = current_user or get_or_create_demo_user(db)
    task = task_service.create_task(db, user_id=user.id, title=body.title, due_at=body.dueAt, priority=body.priority, estimated_minutes=body.estimatedMinutes, energy_tag=body.energyTag)
    return {
        "id": task.id,
        "title": task.title,
        "dueAt": task.due_at,
        "priority": task.priority,
        "estimatedMinutes": task.estimated_minutes,
        "status": task.status,
        "energyTag": task.energy_tag,
    }
