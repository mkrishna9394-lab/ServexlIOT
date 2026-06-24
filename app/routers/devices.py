from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
from app.services.event_logger import log_event
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import (
    Site, Customer,
    Gateway, Sensor, Tag,
    ConfiguredMeter, ConfiguredTag,
    LiveValue, HistoricalValue, Alert,
    GatewayDeleteLog, MeterDeleteLog, GatewayAssignmentLog
)
from app.services.mqtt_discovery_service import discover_mqtt_tags
from app.services.mqtt_worker import start_single_gateway_worker

router = APIRouter(prefix="/devices")

def is_super_admin(user):
    return user.role and user.role.name == "super_admin"


def customer_site_ids(db, user):
    if is_super_admin(user):
        return None

    return [
        s.id for s in db.query(Site)
        .filter(Site.customer_id == user.customer_id)
        .all()
    ]

def to_float(value):
    try:
        return float(value) if str(value).strip() else None
    except Exception:
        return None


@router.get("")
def index(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    site_ids = customer_site_ids(db, user)

    sites_query = db.query(Site)
    gateways_query = db.query(Gateway)

    if site_ids is not None:
        sites_query = sites_query.filter(Site.id.in_(site_ids))
        gateways_query = gateways_query.filter(Gateway.site_id.in_(site_ids))

    sites = sites_query.all()
    gateways = gateways_query.all()
    gateway_ids = [g.id for g in gateways]

    sensors_query = db.query(Sensor)
    configured_sensors_query = db.query(ConfiguredMeter)
    tags_query = db.query(Tag)
    configured_tags_query = db.query(ConfiguredTag)

    if gateway_ids:
        sensors_query = sensors_query.filter(Sensor.gateway_id.in_(gateway_ids))
        configured_sensors_query = configured_sensors_query.filter(
            ConfiguredMeter.gateway_id.in_(gateway_ids)
        )
    else:
        sensors_query = sensors_query.filter(False)
        configured_sensors_query = configured_sensors_query.filter(False)

    sensors = sensors_query.all()
    configured_sensors = configured_sensors_query.all()

    sensor_ids = [s.id for s in sensors]
    configured_meter_ids = [m.id for m in configured_sensors]

    if sensor_ids:
        tags_query = tags_query.filter(Tag.sensor_id.in_(sensor_ids))
    else:
        tags_query = tags_query.filter(False)

    if configured_meter_ids:
        configured_tags_query = configured_tags_query.filter(
            ConfiguredTag.configured_meter_id.in_(configured_meter_ids)
        )
    else:
        configured_tags_query = configured_tags_query.filter(False)

    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "user": user,
            "sites": sites,
            "gateways": gateways,
            "customers": db.query(Customer).all() if is_super_admin(user) else db.query(Customer).filter(Customer.id == user.customer_id).all(),
            "sensors": sensors,
            "configured_sensors": configured_sensors,
            "tags": tags_query.order_by(Tag.id.desc()).all(),
            "configured_tags": configured_tags_query.all(),
        },
    )


@router.post("/gateway/add")
def gateway(
    site_id: int = Form(...),
    code: str = Form(...),
    mqtt_host: str = Form("localhost"),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(""),
    mqtt_password: str = Form(""),
    mqtt_topic: str = Form("#"),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    gateway_obj = db.query(Gateway).filter(Gateway.code == code).first()
    is_new_gateway = False

    if not gateway_obj:
        gateway_obj = Gateway(
            site_id=site_id,
            code=code,
            is_active=True,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
            mqtt_topic=mqtt_topic,
        )
        db.add(gateway_obj)
        db.commit()
        db.refresh(gateway_obj)
        is_new_gateway = True
    else:
        gateway_obj.site_id = site_id
        gateway_obj.is_active = True
        gateway_obj.mqtt_host = mqtt_host
        gateway_obj.mqtt_port = mqtt_port
        gateway_obj.mqtt_username = mqtt_username
        gateway_obj.mqtt_password = mqtt_password
        gateway_obj.mqtt_topic = mqtt_topic
        db.commit()
        db.refresh(gateway_obj)

    site = db.query(Site).filter(Site.id == site_id).first()

    if is_new_gateway:
        db.add(GatewayAssignmentLog(
            gateway_id=gateway_obj.id,
            gateway_code=gateway_obj.code,
            from_customer=None,
            from_site=None,
            to_customer=site.customer.name if site and site.customer else "",
            to_site=site.name if site else "",
            action="created",
        ))
        db.commit()

    try:
        discovered = discover_mqtt_tags(
            host=mqtt_host,
            port=mqtt_port,
            username=mqtt_username,
            password=mqtt_password,
            topic=mqtt_topic,
            duration=10,
        )

        for base_topic, item in discovered.items():
            meter_code = base_topic.replace("/", "_").replace(":", "_")
            meter_name = item.get("slot_name", meter_code)

            meter = db.query(Sensor).filter(
                Sensor.gateway_id == gateway_obj.id,
                Sensor.code == meter_code,
            ).first()

            if not meter:
                meter = Sensor(
                    gateway_id=gateway_obj.id,
                    code=meter_code,
                    name=meter_name,
                    sensor_type="MQTT_METER",
                    is_active=True,
                    is_configured=False,
                )
                db.add(meter)
                db.commit()
                db.refresh(meter)
            else:
                meter.name = meter_name
                meter.sensor_type = "MQTT_METER"
                meter.is_active = True
                db.commit()
                db.refresh(meter)

            for tag_data in item.get("tags", []):
                tag_key = tag_data.get("key")
                tag_name = tag_data.get("name")
                tag_unit = tag_data.get("unit", "")

                existing_tag = db.query(Tag).filter(
                    Tag.sensor_id == meter.id,
                    Tag.key == tag_key,
                ).first()

                if not existing_tag:
                    db.add(Tag(
                        sensor_id=meter.id,
                        key=tag_key,
                        display_name=tag_name,
                        unit=tag_unit,
                        low_limit=None,
                        high_limit=None,
                        log_enabled=False,
                    ))

        db.commit()

        log_event(db, user, "Devices", "Add Gateway", f"Gateway {gateway_obj.code} added/updated")

    except Exception as e:
        print("Gateway MQTT discovery failed:", e)

    start_single_gateway_worker(gateway_obj.id)
    return RedirectResponse("/devices", 303)


@router.post("/sensor/add")
def sensor_add(
    gateway_id: int = Form(...),
    sensor_id: int = Form(...),
    sensor_type: str = Form("MQTT_METER"),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    sensor = db.query(Sensor).filter(
        Sensor.id == sensor_id,
        Sensor.gateway_id == gateway_id
    ).first()

    if sensor:
        existing = db.query(ConfiguredMeter).filter(
            ConfiguredMeter.sensor_id == sensor.id
        ).first()

        if existing:
            existing.gateway_id = gateway_id
            existing.code = sensor.code
            existing.name = sensor.name
            existing.sensor_type = sensor_type
            existing.is_active = True
        else:
            db.add(ConfiguredMeter(
                sensor_id=sensor.id,
                gateway_id=gateway_id,
                code=sensor.code,
                name=sensor.name,
                sensor_type=sensor_type,
                is_active=True
            ))

        db.commit()

        log_event(db, user, "Devices", "Add Meter", f"Configured meter {sensor.name}")

    return RedirectResponse("/devices", 303)


@router.post("/sensor/update")
def sensor_update(
    configured_meter_id: int = Form(...),
    gateway_id: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    sensor_type: str = Form("MQTT_METER"),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    meter = db.query(ConfiguredMeter).filter(ConfiguredMeter.id == configured_meter_id).first()

    if meter:
        meter.gateway_id = gateway_id
        meter.code = code
        meter.name = name
        meter.sensor_type = sensor_type
        meter.is_active = True
        db.commit()

        log_event(db, user, "Devices", "Update Meter", f"Updated meter {meter.name}")

    return RedirectResponse("/devices", 303)


@router.post("/sensor/delete")
def sensor_delete(
    configured_meter_id: int = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    meter = db.query(ConfiguredMeter).filter(ConfiguredMeter.id == configured_meter_id).first()

    if meter:
        db.add(MeterDeleteLog(
            meter_code=meter.code,
            meter_name=meter.name,
            reason=reason,
        ))

        configured_tags = db.query(ConfiguredTag).filter(
            ConfiguredTag.configured_meter_id == meter.id
        ).all()

        for ct in configured_tags:
            db.query(LiveValue).filter(LiveValue.configured_tag_id == ct.id).delete()
            db.query(HistoricalValue).filter(HistoricalValue.configured_tag_id == ct.id).delete()
            db.query(Alert).filter(Alert.tag_id == ct.id).delete()
            db.delete(ct)

        db.delete(meter)
        db.commit()

        log_event(db, user, "Devices", "Delete Meter", f"Deleted meter {meter.name}. Reason: {reason}")

    return RedirectResponse("/devices", 303)


@router.post("/tag/add")
def tag_add(
    configured_meter_id: int = Form(...),
    tag_ids: List[int] = Form(...),
    low_limit: str = Form(""),
    high_limit: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    meter = db.query(ConfiguredMeter).filter(ConfiguredMeter.id == configured_meter_id).first()

    if meter:
        for tag_id in tag_ids:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()

            if not tag:
                continue

            existing = db.query(ConfiguredTag).filter(
                ConfiguredTag.tag_id == tag.id,
                ConfiguredTag.configured_meter_id == meter.id,
            ).first()

            if existing:
                existing.low_limit = to_float(low_limit)
                existing.high_limit = to_float(high_limit)
                existing.is_active = True
            else:
                db.add(ConfiguredTag(
                    tag_id=tag.id,
                    configured_meter_id=meter.id,
                    key=tag.key,
                    display_name=tag.display_name,
                    unit=tag.unit,
                    low_limit=to_float(low_limit),
                    high_limit=to_float(high_limit),
                    is_active=True,
                ))

        db.commit()

        log_event(db, user, "Devices", "Add Tag", f"Configured tag {tag.display_name}")

    return RedirectResponse("/devices", 303)


@router.post("/tag/update")
def tag_update(
    tag_id: int = Form(...),
    configured_meter_id: int = Form(...),
    low_limit: str = Form(""),
    high_limit: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    ct = db.query(ConfiguredTag).filter(ConfiguredTag.id == tag_id).first()

    if ct:
        ct.configured_meter_id = configured_meter_id
        ct.low_limit = to_float(low_limit)
        ct.high_limit = to_float(high_limit)
        ct.is_active = True
        db.commit()
        log_event(db, user, "Devices", "Update Tag", f"Updated configured tag {ct.display_name}")

    return RedirectResponse("/devices", 303)


@router.post("/tag/delete")
def tag_delete(
    configured_tag_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    ct = db.query(ConfiguredTag).filter(ConfiguredTag.id == configured_tag_id).first()

    if ct:
        db.query(LiveValue).filter(LiveValue.configured_tag_id == ct.id).delete()
        db.query(HistoricalValue).filter(HistoricalValue.configured_tag_id == ct.id).delete()
        db.query(Alert).filter(Alert.tag_id == ct.id).delete()
        db.delete(ct)
        db.commit()
        log_event(db, user, "Devices", "Delete Tag", f"Deleted configured tag {ct.display_name}")

    return RedirectResponse("/devices", 303)


@router.post("/gateway/update")
def gateway_update(
    gateway_id: int = Form(...),
    site_id: int = Form(...),
    code: str = Form(...),
    mqtt_host: str = Form("localhost"),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(""),
    mqtt_password: str = Form(""),
    mqtt_topic: str = Form("#"),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    gw = db.query(Gateway).filter(Gateway.id == gateway_id).first()

    if gw:
        gw.site_id = site_id
        gw.code = code
        gw.mqtt_host = mqtt_host
        gw.mqtt_port = mqtt_port
        gw.mqtt_username = mqtt_username
        gw.mqtt_password = mqtt_password
        gw.mqtt_topic = mqtt_topic
        db.commit()

        log_event(db, user, "Devices", "Update Gateway", f"Updated gateway {gw.code}")

    return RedirectResponse("/devices", 303)


@router.post("/gateway/reassign")
def gateway_reassign(
    gateway_id: int = Form(...),
    site_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    gw = db.query(Gateway).filter(Gateway.id == gateway_id).first()
    new_site = db.query(Site).filter(Site.id == site_id).first()

    if gw and new_site:
        old_site = gw.site

        db.add(GatewayAssignmentLog(
            gateway_id=gw.id,
            gateway_code=gw.code,
            from_customer=old_site.customer.name if old_site and old_site.customer else "",
            from_site=old_site.name if old_site else "",
            to_customer=new_site.customer.name if new_site.customer else "",
            to_site=new_site.name,
            action="reassigned",
        ))

        gw.site_id = site_id
        db.commit()

        log_event(db, user, "Devices", "Reassign Gateway", f"Gateway {gw.code} reassigned to {new_site.name}")

    return RedirectResponse("/devices", 303)


@router.post("/gateway/delete")
def gateway_delete(
    gateway_id: int = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    gw = db.query(Gateway).filter(Gateway.id == gateway_id).first()

    if gw:
        db.add(GatewayDeleteLog(
            gateway_code=gw.code,
            reason=reason,
        ))

        meters = db.query(ConfiguredMeter).filter(ConfiguredMeter.gateway_id == gw.id).all()

        for meter in meters:
            configured_tags = db.query(ConfiguredTag).filter(
                ConfiguredTag.configured_meter_id == meter.id
            ).all()

            for ct in configured_tags:
                db.query(LiveValue).filter(LiveValue.configured_tag_id == ct.id).delete()
                db.query(HistoricalValue).filter(HistoricalValue.configured_tag_id == ct.id).delete()
                db.query(Alert).filter(Alert.tag_id == ct.id).delete()
                db.delete(ct)

            db.delete(meter)

        sensors = db.query(Sensor).filter(Sensor.gateway_id == gw.id).all()

        for sensor in sensors:
            tags = db.query(Tag).filter(Tag.sensor_id == sensor.id).all()
            for tag in tags:
                db.delete(tag)
            db.delete(sensor)

        db.delete(gw)
        db.commit()

        log_event(db, user, "Devices", "Delete Gateway", f"Deleted gateway {gw.code}. Reason: {reason}")

    return RedirectResponse("/devices", 303)


@router.get("/gateway/history/{gateway_id}")
def gateway_history(
    gateway_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    logs = (
        db.query(GatewayAssignmentLog)
        .filter(GatewayAssignmentLog.gateway_id == gateway_id)
        .order_by(GatewayAssignmentLog.created_at.desc())
        .all()
    )

    return JSONResponse([
        {
            "date": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
            "action": log.action,
            "from_customer": log.from_customer or "-",
            "from_site": log.from_site or "-",
            "to_customer": log.to_customer or "-",
            "to_site": log.to_site or "-",
        }
        for log in logs
    ])