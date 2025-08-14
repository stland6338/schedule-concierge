"""Domain enumerations for strong typing & validation."""
from enum import Enum

class EventType(str, Enum):
    GENERAL = "GENERAL"
    MEETING = "MEETING"
    FOCUS = "FOCUS"
    BUFFER = "BUFFER"

class TaskStatus(str, Enum):
    DRAFT = "Draft"
    # Future statuses can be added here (e.g., PLANNED, COMPLETED)
