from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import (
    auth,
    dashboard,
    customers,
    devices,
    reports,
    alerts,
    users,
    settings_router,
    diagnostics,
    mqtt_discovery,
)
from app.services.scheduler import start_scheduler
from app.services.mqtt_worker import start_mqtt_worker
from app.models import *


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


for router in [
    auth.router,
    dashboard.router,
    customers.router,
    devices.router,
    reports.router,
    alerts.router,
    users.router,
    settings_router.router,
    diagnostics.router,
    mqtt_discovery.router,
]:
    app.include_router(router)


@app.on_event("startup")
def startup():
    start_scheduler()
    start_mqtt_worker()


@app.get("/")
def home():
    return RedirectResponse("/dashboard")