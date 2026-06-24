from datetime import datetime

from fastapi import APIRouter, Request, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.core.config import settings
from app.models import (
    Gateway, Sensor, Tag, ConfiguredMeter, ConfiguredTag,
    LiveValue, HistoricalValue, Alert, SystemSetting,
    GatewayHealthLog, Site
)

router = APIRouter(prefix="/diagnostics")


def is_super_admin(user):
    return user.role and user.role.name == "super_admin"


def get_customer_gateway_ids(db, user):
    if is_super_admin(user):
        return [g.id for g in db.query(Gateway).all()]

    site_ids = [
        s.id for s in db.query(Site)
        .filter(Site.customer_id == user.customer_id)
        .all()
    ]

    if not site_ids:
        return []

    return [
        g.id for g in db.query(Gateway)
        .filter(Gateway.site_id.in_(site_ids))
        .all()
    ]


def get_int_setting(db: Session, key: str, default: int):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    try:
        return int(setting.value) if setting else default

    except Exception:
        return default



def format_duration(seconds):
    if seconds is None:
        return "Never"
    if seconds < 60:
        return f"{seconds} sec"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours} hr {minutes} min"


@router.get("")
def index(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    now = datetime.now()
    offline_seconds = get_int_setting(db, "data_offline_seconds", settings.DATA_OFFLINE_SECONDS)

    gateway_ids = get_customer_gateway_ids(db, user)

    gateways = (
        db.query(Gateway)
        .filter(Gateway.id.in_(gateway_ids))
        .order_by(Gateway.id.desc())
        .all()
    )

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

        current_status = (
            "Online"
            if last_seen and diff_seconds is not None and diff_seconds <= offline_seconds
            else "Offline"
        )

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

    configured_meter_ids = [
        m.id for m in db.query(ConfiguredMeter)
        .filter(ConfiguredMeter.gateway_id.in_(gateway_ids))
        .all()
    ]

    configured_tag_ids = [
        t.id for t in db.query(ConfiguredTag)
        .filter(ConfiguredTag.configured_meter_id.in_(configured_meter_ids))
        .all()
    ]

    health_logs = (
        db.query(GatewayHealthLog)
        .filter(GatewayHealthLog.gateway_id.in_(gateway_ids))
        .order_by(GatewayHealthLog.created_at.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        "diagnostics.html",
        {
            "request": request,
            "user": user,
            "is_super_admin": is_super_admin(user),
            "db_ok": db_ok,
            "mqtt_worker_status": "Running" if gateways else "No Gateway Configured",
            "scheduler_status": "Running",
            "total_gateways": len(gateways),
            "online_count": online_count,
            "offline_count": offline_count,
            "total_sensors": len(configured_meter_ids),
            "total_tags": len(configured_tag_ids),
            "total_discovered_meters": db.query(Sensor).count(),
            "total_discovered_tags": db.query(Tag).count(),
            "total_live_values": (
                db.query(LiveValue)
                .filter(LiveValue.configured_tag_id.in_(configured_tag_ids))
                .count()
            ),
            "total_historical_values": (
                db.query(HistoricalValue)
                .filter(HistoricalValue.configured_tag_id.in_(configured_tag_ids))
                .count()
            ),
            "active_alerts": (
                db.query(Alert)
                .filter(Alert.status == "active")
                .filter(Alert.tag_id.in_(configured_tag_ids))
                .count()
            ),
            "gateway_rows": gateway_rows,
            "health_logs": health_logs,
            "offline_seconds": offline_seconds,
        }
    )