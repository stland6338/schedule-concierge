from contextlib import asynccontextmanager
from datetime import datetime, date, time, timedelta, timezone

from fastapi import FastAPI, Request, Response, APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session

from . import db  # noqa: F401 ensure models imported (register models before create_all)
from .api.tasks import router as tasks_router
from .api.slots import router as slots_router
from .api.events import router as events_router
from .api.auth import router as auth_router, get_current_user_optional
from .db import models
from .db.session import engine, Base, get_db
from .errors import BaseAppException, ValidationAppError
from .services import task_service
from .services.recommendation_service import compute_slots
from .services.nlp_service import parse_schedule_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema (idempotent for SQLite in tests)
    Base.metadata.create_all(bind=engine)
    # Lightweight migration: add hashed_password column if absent (SQLite dev only)
    try:
        with engine.connect() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            cols = {r[1] for r in res}
            if 'hashed_password' not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN hashed_password VARCHAR")
    except Exception:
        pass  # ignore if fails; tests will recreate fresh DB
    yield


app = FastAPI(title="Schedule Concierge API", version="0.1.0", lifespan=lifespan)
nlp_router = APIRouter(prefix="/nlp", tags=["nlp"])  # defined before decorated endpoints

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(slots_router)
app.include_router(events_router)
app.include_router(nlp_router)
app.include_router(slots_router)
app.include_router(events_router)
app.include_router(nlp_router)
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from .db.session import engine, Base
from . import db  # noqa: F401 ensure models imported (register models before create_all)
from .api.tasks import router as tasks_router
from .api.slots import router as slots_router
from .api.events import router as events_router
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .db.session import get_db
from .services import task_service
from .db import models
from .services.recommendation_service import compute_slots
from datetime import datetime, date, time, timedelta, timezone
import re
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .services.nlp_service import parse_schedule_text
from .errors import BaseAppException, ValidationAppError
from fastapi.responses import JSONResponse

REQUEST_COUNT = Counter('schedule_concierge_requests_total', 'Total HTTP requests', ['method', 'path', 'status'])
REQUEST_LATENCY = Histogram('schedule_concierge_request_latency_seconds', 'Latency of HTTP requests', ['method', 'path'])

nlp_router = APIRouter(prefix="/nlp", tags=["nlp"])  # ensure defined before decorators

@nlp_router.post("/parse-schedule")
async def parse_schedule(payload: dict = Body(...)):
    # parse_schedule_text is synchronous; call directly
    return parse_schedule_text(payload.get("input", ""))

@nlp_router.post("/commit", status_code=201)
async def commit_schedule(payload: dict = Body(...), db: Session = Depends(get_db), current_user: models.User | None = Depends(get_current_user_optional)):
    draft = payload.get("draft") or {}
    if not draft:
        raise ValidationAppError("NO_DRAFT", "draft is required")
    title = draft.get("title") or "タスク"
    estimated = draft.get("estimatedMinutes") or 30
    energy_tag = draft.get("energyTag")
    due_date_str = draft.get("date")
    # Interpret date as due date end of day for now
    due_at = None
    if due_date_str:
        try:
            d = date.fromisoformat(due_date_str)
            due_at = datetime.combine(d, time(23, 59)).replace(tzinfo=timezone.utc)
        except Exception:
            due_at = None
    if current_user is None:
        user_id = "demo-user"
        if not db.query(models.User).filter(models.User.id == user_id).first():
            u = models.User(id=user_id, email="demo@example.com", timezone="UTC", locale="en-US")
            db.add(u)
            db.commit()
        user = db.query(models.User).filter(models.User.id == user_id).first()
    else:
        user = current_user
    task = task_service.create_task(db, user_id=user.id, title=title, due_at=due_at, priority=3, estimated_minutes=estimated, energy_tag=energy_tag)
    # Build availability next 5 days working hours
    now = datetime.now(timezone.utc)
    availability = []
    for day in range(5):
        day_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day)
        if day_start.weekday() < 5:  # week days
            availability.append({"start": day_start, "end": day_start.replace(hour=17)})
    existing_events = db.query(models.Event).filter(models.Event.user_id == user.id).all()
    slots = compute_slots(task, availability, limit=5, existing_events=existing_events)
    task_out = {
        "id": task.id,
        "title": task.title,
        "dueAt": task.due_at,
        "priority": task.priority,
        "estimatedMinutes": task.estimated_minutes,
        "status": task.status,
        "energyTag": task.energy_tag,
    }
    return {"task": task_out, "slots": slots}

app.include_router(nlp_router)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    # Simplify high-cardinality paths
    if path.startswith('/events/') and len(path) > len('/events/'):
        path_label = '/events/:id'
    else:
        path_label = path
    with REQUEST_LATENCY.labels(method=method, path=path_label).time():
        response: Response = await call_next(request)
    REQUEST_COUNT.labels(method=method, path=path_label, status=str(response.status_code)).inc()
    return response

@app.get('/metrics')
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(status_code=exc.http_status, content={"detail": {"code": exc.code, "message": exc.message}})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # fallback (avoid leaking internals)
    return JSONResponse(status_code=500, content={"detail": {"code": "INTERNAL_ERROR", "message": "unexpected error"}})

 # (startup event removed; handled by lifespan)

@app.get("/healthz")
async def health():
    return {"status": "ok"}
