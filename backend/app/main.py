"""FastAPI application entrypoint.

Responsibilities kept minimal:
  * App / lifespan initialization
  * Router registration (auth, tasks, slots, events, nlp)
  * Cross-cutting concerns: metrics middleware & exception handlers
  * Lightweight NLP endpoints (parse / commit) colocated for now

NOTE: This file previously had duplicated imports and router registrations; cleaned for clarity.
"""

from contextlib import asynccontextmanager
import os
from datetime import datetime, date, time, timedelta, timezone
from fastapi import FastAPI, Request, Response, APIRouter, Body, Depends
try:  # Optional OpenTelemetry
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _otel_available = True
except Exception:  # pragma: no cover
    _otel_available = False
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session

from . import db  # noqa: F401 ensure models imported (register models before create_all)
from .api.tasks import router as tasks_router
from .api.slots import router as slots_router
from .api.events import router as events_router
from .api.auth import router as auth_router, get_current_user_optional
from .api.oauth import router as oauth_router
from .api.integrations import router as integrations_router
from .api.calendars import router as calendars_router
from .db import models
from .db.session import engine, Base, get_db
from .errors import BaseAppException, ValidationAppError
from .services import task_service
from .services.recommendation_service import compute_slots
from .services.nlp_service import parse_schedule_text
from .services.demo_user import get_or_create_demo_user


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - simple startup path
    """Initialize database schema (idempotent for tests) and apply lightweight dev migrations."""
    Base.metadata.create_all(bind=engine)
    try:  # best-effort SQLite column add (dev/testing convenience)
        with engine.connect() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            cols = {r[1] for r in res}
            if "hashed_password" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN hashed_password VARCHAR")
            # calendars table lightweight adds
            res_c = conn.exec_driver_sql("PRAGMA table_info(calendars)").fetchall()
            cal_cols = {r[1] for r in res_c}
            for col, ddl in [
                ("time_zone", "ALTER TABLE calendars ADD COLUMN time_zone VARCHAR"),
                ("access_role", "ALTER TABLE calendars ADD COLUMN access_role VARCHAR"),
                ("color", "ALTER TABLE calendars ADD COLUMN color VARCHAR"),
                ("is_primary", "ALTER TABLE calendars ADD COLUMN is_primary INTEGER DEFAULT 0"),
                ("is_default", "ALTER TABLE calendars ADD COLUMN is_default INTEGER DEFAULT 0"),
                ("selected", "ALTER TABLE calendars ADD COLUMN selected INTEGER DEFAULT 1"),
                ("updated_at", "ALTER TABLE calendars ADD COLUMN updated_at TIMESTAMP")
            ]:
                if col not in cal_cols:
                    try:
                        conn.exec_driver_sql(ddl)
                    except Exception:
                        pass
    except Exception:  # pragma: no cover
        pass
    yield


# --- Optional .env loading (opt-in via APP_LOAD_DOTENV) ---
if os.getenv("APP_LOAD_DOTENV") in {"1", "true", "TRUE", "yes", "on"}:  # pragma: no cover
    try:
        from dotenv import load_dotenv  # type: ignore
        # Respect existing env (override=False). Default search walks up from CWD.
        load_dotenv(override=False)
    except Exception:
        # If python-dotenv is not installed or any error occurs, continue without failing.
        pass

app = FastAPI(title="Schedule Concierge API", version="0.1.0", lifespan=lifespan)

# --- OpenTelemetry Tracing (optional) ---
if _otel_available and os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    resource = Resource.create({"service.name": "schedule-concierge-backend"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
else:  # pragma: no cover
    tracer = None

# --- Metrics setup ---
REQUEST_COUNT = Counter(
    "schedule_concierge_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "schedule_concierge_request_latency_seconds", "Latency of HTTP requests", ["method", "path"]
)

# Application-level domain metrics
NLP_PARSE_COUNT = Counter(
    "schedule_concierge_nlp_parse_total", "Total NLP parse requests"
)
NLP_PARSE_DURATION = Histogram(
    "schedule_concierge_nlp_parse_duration_seconds", "Latency of NLP schedule parse"
)
NLP_COMMIT_COUNT = Counter(
    "schedule_concierge_nlp_commit_total", "Total NLP commit requests"
)
NLP_COMMIT_DURATION = Histogram(
    "schedule_concierge_nlp_commit_duration_seconds", "Latency of NLP commit endpoint"
)

# --- CORS (for local frontend dev) ---
cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS")
if cors_origins_env:
    allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
else:
    allow_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NLP router ---
nlp_router = APIRouter(prefix="/nlp", tags=["nlp"])


@nlp_router.post("/parse-schedule")
async def parse_schedule(payload: dict = Body(...)):
    NLP_PARSE_COUNT.inc()
    with NLP_PARSE_DURATION.time():
        return parse_schedule_text(payload.get("input", ""))


@nlp_router.post("/commit", status_code=201)
async def commit_schedule(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    NLP_COMMIT_COUNT.inc()
    with NLP_COMMIT_DURATION.time():
        draft = payload.get("draft") or {}
        if not draft:
            raise ValidationAppError("NO_DRAFT", "draft is required")
        title = draft.get("title") or "タスク"
        estimated = draft.get("estimatedMinutes") or 30
        energy_tag = draft.get("energyTag")
        due_date_str = draft.get("date")
        due_at = None
        if due_date_str:
            try:
                d = date.fromisoformat(due_date_str)
                due_at = datetime.combine(d, time(23, 59)).replace(tzinfo=timezone.utc)
            except Exception:
                due_at = None
        user = current_user or get_or_create_demo_user(db)

        task = task_service.create_task(
            db,
            user_id=user.id,
            title=title,
            due_at=due_at,
            priority=3,
            estimated_minutes=estimated,
            energy_tag=energy_tag,
        )

        now = datetime.now(timezone.utc)
        availability = []
        for day in range(5):
            day_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day)
            if day_start.weekday() < 5:
                availability.append({"start": day_start, "end": day_start.replace(hour=17)})
        existing_events = (
            db.query(models.Event)
            .join(models.Calendar, models.Calendar.id == models.Event.calendar_id)
            .filter(models.Event.user_id == user.id, models.Calendar.selected == 1)
            .all()
        )
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


# --- Register routers once ---
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(slots_router)
app.include_router(events_router)
app.include_router(nlp_router)
app.include_router(oauth_router)
app.include_router(integrations_router)
app.include_router(calendars_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    if path.startswith("/events/") and len(path) > len("/events/"):
        path_label = "/events/:id"
    else:
        path_label = path
    with REQUEST_LATENCY.labels(method=method, path=path_label).time():
        if tracer:
            with tracer.start_as_current_span(f"HTTP {method} {path_label}"):
                response: Response = await call_next(request)
        else:
            response: Response = await call_next(request)
    REQUEST_COUNT.labels(method=method, path=path_label, status=str(response.status_code)).inc()
    return response


@app.get("/metrics")
def metrics():  # pragma: no cover - external scrape
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # pragma: no cover
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "INTERNAL_ERROR", "message": "unexpected error"}},
    )


@app.get("/healthz")
async def health():
    health = {"status": "ok"}
    # Redis state store check (optional)
    try:
        from app.services.oauth_service import OAuthService
        svc = OAuthService()
        from app.services.state_store import RedisStateStore
        backend = 'redis' if isinstance(svc.state_store, RedisStateStore) else 'memory'
        health['oauthStateBackend'] = backend
        if backend == 'redis':
            # PING (non-fatal)
            try:
                pong = svc.state_store.redis.ping()
                health['redis'] = 'up' if pong else 'down'
            except Exception:
                health['redis'] = 'error'
    except Exception:  # pragma: no cover
        pass
    # Tracing status
    health['tracing'] = 'enabled' if ('tracer' in globals() and tracer) else 'disabled'
    return health
