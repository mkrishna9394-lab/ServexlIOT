from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import SystemSetting

router = APIRouter(prefix="/settings")


DEFAULT_SETTINGS = {
    "app_name": "IIoT Cloud",
    "dashboard_refresh_seconds": "2",
    "diagnostics_refresh_seconds": "10",
    "data_offline_seconds": "60",
    "historical_retention_days": "30",
    "live_trend_points": "30",
}


def get_settings_dict(db: Session):
    existing = db.query(SystemSetting).all()
    data = {s.key: s.value for s in existing}

    for key, value in DEFAULT_SETTINGS.items():
        if key not in data:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
            data[key] = value

    db.commit()
    return data


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    settings = get_settings_dict(db)

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "settings": settings,
        }
    )


@router.post("/save")
def save(
    app_name: str = Form(...),
    dashboard_refresh_seconds: str = Form(...),
    diagnostics_refresh_seconds: str = Form(...),
    data_offline_seconds: str = Form(...),
    historical_retention_days: str = Form(...),
    live_trend_points: str = Form(...),
    logo_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    values = {
        "app_name": app_name,
        "dashboard_refresh_seconds": dashboard_refresh_seconds,
        "diagnostics_refresh_seconds": diagnostics_refresh_seconds,
        "data_offline_seconds": data_offline_seconds,
        "historical_retention_days": historical_retention_days,
        "live_trend_points": live_trend_points,
    }

    for key, value in values.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

        if not setting:
            setting = SystemSetting(key=key)

        setting.value = value
        db.add(setting)


    if logo_file and logo_file.filename:
        upload_dir = Path("app/static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        logo_path = upload_dir / "logo.png"
        with logo_path.open("wb") as buffer:
            shutil.copyfileobj(logo_file.file, buffer)

    db.commit()
    return RedirectResponse("/settings", 303)