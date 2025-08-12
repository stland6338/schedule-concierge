# Ensure model metadata is loaded when importing app.db
from .session import Base  # noqa: F401
from .models import User, Task, Event  # noqa: F401
