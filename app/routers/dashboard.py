from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import (
    Customer, Gateway, Site,
    ConfiguredMeter, ConfiguredTag,
    LiveValue, Alert, SystemSetting
)

router = APIRouter()

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

    return [
        g.id for g in db.query(Gateway)
        .filter(Gateway.site_id.in_(site_ids))
        .all()
    ]


def get_int_setting(db: Session, key: str, default: int):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        return default

    try:
        return int(setting.value)
    except Exception:
        return default


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    gateway_ids = get_customer_gateway_ids(db, user)

    meter_query = db.query(ConfiguredMeter)
    gateway_query = db.query(Gateway)

    if not is_super_admin(user):
        meter_query = meter_query.filter(ConfiguredMeter.gateway_id.in_(gateway_ids))
        gateway_query = gateway_query.filter(Gateway.id.in_(gateway_ids))

    meters = meter_query.all()
    meter_ids = [m.id for m in meters]

    tag_query = db.query(ConfiguredTag).filter(ConfiguredTag.is_active == True)

    if not is_super_admin(user):
        tag_query = tag_query.filter(ConfiguredTag.configured_meter_id.in_(meter_ids))

    alert_query = (
        db.query(Alert)
        .join(ConfiguredTag, Alert.tag_id == ConfiguredTag.id)
        .join(ConfiguredMeter, ConfiguredTag.configured_meter_id == ConfiguredMeter.id)
        .filter(Alert.status == "active")
    )

    if not is_super_admin(user):
        alert_query = alert_query.filter(ConfiguredMeter.gateway_id.in_(gateway_ids))

    stats = {}

    if is_super_admin(user):
        stats["customers"] = db.query(Customer).count()

    stats.update({
        "gateways": gateway_query.count(),
        "meters": len(meters),
        "tags": tag_query.count(),
        "active_alerts": alert_query.count(),
    })

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "dashboard_refresh_seconds": get_int_setting(db, "dashboard_refresh_seconds", 2),
            "live_trend_points": get_int_setting(db, "live_trend_points", 30),
        }
    )


@router.get("/api/live-values")
def live_values(db: Session = Depends(get_db), user=Depends(require_user)):
    gateway_ids = get_customer_gateway_ids(db, user)

    rows_query = (
        db.query(LiveValue, ConfiguredTag, ConfiguredMeter)
        .join(ConfiguredTag, LiveValue.configured_tag_id == ConfiguredTag.id)
        .join(ConfiguredMeter, ConfiguredTag.configured_meter_id == ConfiguredMeter.id)
        .filter(ConfiguredTag.is_active == True)
    )

    if not is_super_admin(user):
        rows_query = rows_query.filter(ConfiguredMeter.gateway_id.in_(gateway_ids))

    rows = rows_query.order_by(LiveValue.timestamp.desc()).limit(50).all()

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