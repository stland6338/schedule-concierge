from fastapi import FastAPI, Request, Response
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

# Prometheus metrics
REQUEST_COUNT = Counter(
    'schedule_concierge_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)
REQUEST_LATENCY = Histogram(
    'schedule_concierge_request_latency_seconds',
    'Latency of HTTP requests',
    ['method', 'path']
)

app = FastAPI(title="Schedule Concierge API", version="0.1.0")

app.include_router(tasks_router)
app.include_router(slots_router)
app.include_router(events_router)

nlp_router = APIRouter(prefix="/nlp", tags=["nlp"])

@nlp_router.post("/parse-schedule")
def parse_schedule(payload: dict = Body(...)):
    text: str = payload.get("input", "").strip()
    if not text:
        return {"intents": [], "draft": None}
    today = date.today()
    target_date = today
    # 日付語
    if "明日" in text:
        target_date = today + timedelta(days=1)
    elif "明後日" in text:
        target_date = today + timedelta(days=2)
    # 時刻抽出 (午前/午後 + 数字 + 時)
    hour = 9
    minute = 0
    m = re.search(r"(午前|午後)?(\d{1,2})時", text)
    if m:
        h = int(m.group(2))
        if m.group(1) == "午後" and h < 12:
            h += 12
        hour = h
    # 分指定
    dm = re.search(r"(\d{1,3})分", text)
    duration = 60
    if dm:
        duration = min(480, int(dm.group(1)))
    # 所要時間を別途時間表現から (\d+時間)
    hm = re.search(r"(\d{1,2})時間", text)
    if hm:
        duration = int(hm.group(1)) * 60
    start_dt = datetime.combine(target_date, time(hour=hour, minute=minute, tzinfo=timezone.utc))
    # タイトル抽出: ノイズ語除去
    noise_patterns = ["今日は", "明日", "明後日", "午前", "午後", r"\d{1,2}時", r"\d{1,2}時間", r"\d{1,3}分", "書きたい", "したい"]
    title = text
    for p in noise_patterns:
        title = re.sub(p, "", title)
    title = title.replace("  ", " ").strip(" 。、 ")
    # 先頭助詞/格助詞などの除去 (簡易)
    title = re.sub(r"^(に|を|へ|で)+", "", title)
    if not title:
        title = "タスク"
    # "絵のラフ" のような末尾助詞削る最小対応
    title = re.sub(r"(を|の|へ|に)$", "", title)
    # energy tag inference (簡易ルール)
    energy_tag = None
    if re.search(r"集中|深く|ディープ|集中して", text):
        energy_tag = "deep"
    elif re.search(r"朝|午前", text) and hour < 11:
        energy_tag = "morning"
    elif re.search(r"午後|昼", text):
        energy_tag = "afternoon"

    draft = {
        "title": title,
        "date": target_date.isoformat(),
        "startAt": start_dt.isoformat(),
        "estimatedMinutes": duration,
        "energyTag": energy_tag
    }
    return {"intents": [{"type": "create_task", "confidence": 0.9}], "draft": draft}

@nlp_router.post("/commit", status_code=201)
def commit_schedule(payload: dict = Body(...), db: Session = Depends(get_db)):
    draft = payload.get("draft") or {}
    if not draft:
        raise HTTPException(status_code=400, detail={"code": "NO_DRAFT", "message": "draft is required"})
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
    user_id = "demo-user"
    # ensure user exists
    if not db.query(models.User).filter(models.User.id == user_id).first():
        u = models.User(id=user_id, email="demo@example.com", timezone="UTC", locale="en-US")
        db.add(u)
        db.commit()
    task = task_service.create_task(db, user_id=user_id, title=title, due_at=due_at, priority=3, estimated_minutes=estimated, energy_tag=energy_tag)
    # Build availability next 5 days working hours
    now = datetime.now(timezone.utc)
    availability = []
    for day in range(5):
        day_start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=day)
        if day_start.weekday() < 5:  # week days
            availability.append({"start": day_start, "end": day_start.replace(hour=17)})
    existing_events = db.query(models.Event).filter(models.Event.user_id == user_id).all()
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

@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)

@app.get("/healthz")
async def health():
    return {"status": "ok"}
