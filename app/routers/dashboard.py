from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import (
    Customer, Gateway,
    ConfiguredMeter, ConfiguredTag,
    LiveValue, Alert, SystemSetting
)

router = APIRouter()


def get_int_setting(db: Session, key: str, default: int):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    if not setting:
        return default

    try:
        return int(setting.value)
    except Exception:
        return default


@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    dashboard_refresh_seconds = get_int_setting(db, "dashboard_refresh_seconds", 2)
    live_trend_points = get_int_setting(db, "live_trend_points", 30)

    stats = {
        "customers": db.query(Customer).count(),
        "gateways": db.query(Gateway).count(),
        "meters": db.query(ConfiguredMeter).count(),
        "tags": db.query(ConfiguredTag).filter(ConfiguredTag.is_active == True).count(),
        "active_alerts": db.query(Alert).filter(Alert.status == "active").count(),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "dashboard_refresh_seconds": dashboard_refresh_seconds,
            "live_trend_points": live_trend_points,
        }
    )


@router.get("/api/live-values")
def live_values(
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    rows = (
        db.query(LiveValue, ConfiguredTag, ConfiguredMeter)
        .join(ConfiguredTag, LiveValue.configured_tag_id == ConfiguredTag.id)
        .join(ConfiguredMeter, ConfiguredTag.configured_meter_id == ConfiguredMeter.id)
        .filter(ConfiguredTag.is_active == True)
        .order_by(LiveValue.timestamp.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "tag_id": configured_tag.id,
            "meter_name": meter.name,
            "tag_name": configured_tag.display_name,
            "value": live.value,
            "timestamp": live.timestamp.strftime("%Y-%m-%d %H:%M:%S") if live.timestamp else "",
        }
        for live, configured_tag, meter in rows
    ]