from fastapi import FastAPI
from .db.session import engine, Base
from . import db  # noqa: F401 ensure models imported (register models before create_all)
from .api.tasks import router as tasks_router
from .api.slots import router as slots_router
from .api.events import router as events_router

app = FastAPI(title="Schedule Concierge API", version="0.1.0")

app.include_router(tasks_router)
app.include_router(slots_router)
app.include_router(events_router)

@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)

@app.get("/healthz")
async def health():
    return {"status": "ok"}
