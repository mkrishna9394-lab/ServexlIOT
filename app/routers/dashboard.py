from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from datetime import datetime, timedelta
from app.core.templates import templates
from app.core.deps import require_user
from app.models import (
    Customer, Gateway, Site,
    ConfiguredMeter, ConfiguredTag,
    LiveValue, Alert, SystemSetting, HistoricalValue
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


def is_number(value):
    try:
        float(value)
        return True
    except Exception:
        return False

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

    latest_subq = (
        db.query(
            LiveValue.configured_tag_id,
            func.max(LiveValue.timestamp).label("latest_time")
        )
        .group_by(LiveValue.configured_tag_id)
        .subquery()
    )

    rows_query = (
        db.query(LiveValue, ConfiguredTag, ConfiguredMeter, Gateway)
        .join(
            latest_subq,
            (LiveValue.configured_tag_id == latest_subq.c.configured_tag_id) &
            (LiveValue.timestamp == latest_subq.c.latest_time)
        )
        .join(ConfiguredTag, LiveValue.configured_tag_id == ConfiguredTag.id)
        .join(ConfiguredMeter, ConfiguredTag.configured_meter_id == ConfiguredMeter.id)
        .join(Gateway, ConfiguredMeter.gateway_id == Gateway.id)
        .filter(ConfiguredTag.is_active == True)
    )

    if not is_super_admin(user):
        rows_query = rows_query.filter(ConfiguredMeter.gateway_id.in_(gateway_ids))

    rows = rows_query.order_by(
        ConfiguredMeter.name.asc(),
        ConfiguredTag.display_name.asc()
    ).all()

    offline_seconds = get_int_setting(db, "data_offline_seconds", 60)
    now = datetime.now()

    result = []

    for live, configured_tag, meter, gateway in rows:
        display_value = live.value_text if live.value_text not in [None, ""] else live.value
        numeric = is_number(display_value)

        gateway_offline = True
        if gateway.last_seen:
            diff_seconds = (now - gateway.last_seen).total_seconds()
            gateway_offline = diff_seconds > offline_seconds

        result.append({
            "tag_id": configured_tag.id,
            "meter_name": meter.name,
            "tag_name": configured_tag.display_name,
            "tag_type": configured_tag.tag_type or "Not Set",
            "value": display_value,
            "is_string": False if numeric else True,
            "timestamp": live.timestamp.strftime("%Y-%m-%d %H:%M:%S") if live.timestamp else "",
            "gateway_status": "Offline" if gateway_offline else "Online",
            "is_offline": gateway_offline,
            "meter_id": meter.id,
        })

    return result

@router.get("/trend/{tag_id}")
def trend_page(
    tag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    tag = db.query(ConfiguredTag).filter(ConfiguredTag.id == tag_id).first()

    return templates.TemplateResponse(
        "trend.html",
        {
            "request": request,
            "user": user,
            "tag": tag,
        }
    )


@router.get("/api/trend/{tag_id}")
def trend_data(
    tag_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    rows = (
        db.query(HistoricalValue)
        .filter(HistoricalValue.configured_tag_id == tag_id)
        .order_by(HistoricalValue.timestamp.desc())
        .limit(100)
        .all()
    )

    rows = list(reversed(rows))

    return [
        {
            "value": r.value_text if r.value_text not in [None, ""] else r.value,
            "timestamp": r.timestamp.strftime("%H:%M:%S") if r.timestamp else "",
            "is_string": not is_number(r.value_text if r.value_text not in [None, ""] else r.value),
        }
        for r in rows
    ]


@router.get("/meter-trend/{meter_id}")
def meter_trend_page(
    meter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    meter = db.query(ConfiguredMeter).filter(ConfiguredMeter.id == meter_id).first()

    return templates.TemplateResponse(
        "meter_trend.html",
        {
            "request": request,
            "user": user,
            "meter": meter,
        }
    )


@router.get("/api/meter-trend/{meter_id}")
def meter_trend_data(
    meter_id: int,
    period: str = "1h",
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    now = datetime.now()

    period_map = {
        "15m": now - timedelta(minutes=15),
        "30m": now - timedelta(minutes=30),
        "1h": now - timedelta(hours=1),
        "6h": now - timedelta(hours=6),
        "12h": now - timedelta(hours=12),
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
    }

    start_time = period_map.get(period, now - timedelta(hours=1))

    tags = (
        db.query(ConfiguredTag)
        .filter(
            ConfiguredTag.configured_meter_id == meter_id,
            ConfiguredTag.is_active == True
        )
        .all()
    )

    result = []

    for tag in tags:
        rows = (
            db.query(HistoricalValue)
            .filter(
                HistoricalValue.configured_tag_id == tag.id,
                HistoricalValue.timestamp >= start_time
            )
            .order_by(HistoricalValue.timestamp.asc())
            .limit(500)
            .all()
        )

        values = []

        for r in rows:
            display_value = r.value_text if r.value_text not in [None, ""] else r.value

            if not is_number(display_value):
                continue

            values.append({
                "timestamp": r.timestamp.strftime("%H:%M:%S") if r.timestamp else "",
                "value": float(display_value),
            })

        if values:
            result.append({
                "tag_id": tag.id,
                "tag_name": tag.display_name,
                "tag_type": tag.tag_type or "Not Set",
                "values": values,
            })

    return result