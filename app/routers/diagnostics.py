from datetime import datetime

from fastapi import APIRouter, Request, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.core.config import settings
from app.models import (
    Gateway,
    Sensor,
    Tag,
    ConfiguredMeter,
    ConfiguredTag,
    LiveValue,
    HistoricalValue,
    Alert,
    SystemSetting,
    GatewayHealthLog,
)

router = APIRouter(prefix="/diagnostics")


def get_int_setting(db: Session, key: str, default: int):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        return default

    try:
        return int(setting.value)
    except Exception:
        return default


def format_duration(seconds: int):
    if seconds is None:
        return "Never"

    if seconds < 60:
        return f"{seconds} sec"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    minutes = minutes % 60
    if hours < 24:
        return f"{hours} hr {minutes} min"

    days = hours // 24
    hours = hours % 24
    return f"{days} day {hours} hr"


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db_ok = True

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    now = datetime.now()

    offline_seconds = get_int_setting(
        db,
        "data_offline_seconds",
        settings.DATA_OFFLINE_SECONDS
    )

    gateways = db.query(Gateway).order_by(Gateway.id.desc()).all()

    gateway_rows = []
    online_count = 0
    offline_count = 0

    for gw in gateways:
        last_seen = gw.last_seen

        if last_seen:
            diff_seconds = int((now - last_seen).total_seconds())
            communicated_since = format_duration(diff_seconds)
        else:
            diff_seconds = None
            communicated_since = "Never"

        is_online = (
            last_seen is not None
            and diff_seconds is not None
            and diff_seconds <= offline_seconds
        )

        current_status = "Online" if is_online else "Offline"

        if current_status == "Online":
            online_count += 1
        else:
            offline_count += 1

        last_log = (
            db.query(GatewayHealthLog)
            .filter(GatewayHealthLog.gateway_id == gw.id)
            .order_by(GatewayHealthLog.id.desc())
            .first()
        )

        if not last_log or last_log.status != current_status:
            db.add(GatewayHealthLog(
                gateway_id=gw.id,
                gateway_code=gw.code,
                status=current_status,
                last_seen=last_seen
            ))
            db.commit()

        gateway_rows.append({
            "code": gw.code,
            "mqtt_host": gw.mqtt_host,
            "mqtt_port": gw.mqtt_port,
            "mqtt_topic": gw.mqtt_topic,
            "last_seen": last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else "Never",
            "communicated_since": communicated_since,
            "status": current_status,
        })

    health_logs = (
        db.query(GatewayHealthLog)
        .order_by(GatewayHealthLog.created_at.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        "diagnostics.html",
        {
            "request": request,
            "user": user,
            "db_ok": db_ok,
            "mqtt_worker_status": "Running" if gateways else "No Gateway Configured",
            "scheduler_status": "Running",
            "total_gateways": len(gateways),
            "online_count": online_count,
            "offline_count": offline_count,
            "total_sensors": db.query(ConfiguredMeter).count(),
            "total_tags": db.query(ConfiguredTag).count(),
            "total_discovered_meters": db.query(Sensor).count(),
            "total_discovered_tags": db.query(Tag).count(),
            "total_live_values": db.query(LiveValue).count(),
            "total_historical_values": db.query(HistoricalValue).count(),
            "active_alerts": db.query(Alert).filter(Alert.status == "active").count(),
            "gateway_rows": gateway_rows,
            "health_logs": health_logs,
            "offline_seconds": offline_seconds,
        }
    )