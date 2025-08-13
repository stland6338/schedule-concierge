"""Utility for ensuring presence of a demo (fallback) user.

Consolidates previously duplicated logic across multiple endpoints.
"""
from sqlalchemy.orm import Session
from ..db import models

DEMO_USER_ID = "demo-user"
DEMO_EMAIL = "demo@example.com"


def get_or_create_demo_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.id == DEMO_USER_ID).first()
    if user:
        return user
    user = models.User(id=DEMO_USER_ID, email=DEMO_EMAIL, timezone="UTC", locale="en-US")
    db.add(user)
    db.commit()
    return db.query(models.User).filter(models.User.id == DEMO_USER_ID).first()
