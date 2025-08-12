from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
import threading

"""Database session / engine configuration.

NOTE: In-memory SQLite (":memory:") creates a new database per connection which
breaks tests that open multiple connections. For the lightweight initial TDD
setup we use a file-based SQLite database unless DATABASE_URL is provided.
This can be replaced by a PostgreSQL URL in real deployments.
"""

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./local.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

# Import models to register metadata
try:  # noqa: F401
    from . import models  # type: ignore
except Exception:  # pragma: no cover
    pass

_init_lock = threading.Lock()
_tables_created = False

def _ensure_tables():
    global _tables_created
    if _tables_created:
        return
    with _init_lock:
        if not _tables_created:
            Base.metadata.create_all(bind=engine)
            _tables_created = True

# Dependency
def get_db():
    _ensure_tables()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
