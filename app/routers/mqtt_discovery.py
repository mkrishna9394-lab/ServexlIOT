import json

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Site, Gateway, Sensor, Tag
from app.services.mqtt_discovery_service import discover_mqtt_tags
from app.services.mqtt_worker import start_single_gateway_worker


router = APIRouter(prefix="/mqtt-discovery")


@router.get("")
def mqtt_discovery_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    return templates.TemplateResponse(
        "mqtt_discovery.html",
        {
            "request": request,
            "user": user,
            "sites": db.query(Site).all(),
            "discovered": None,
            "form_data": {},
        }
    )


@router.post("/discover")
def discover(
    request: Request,
    site_id: int = Form(...),
    gateway_code: str = Form(...),
    mqtt_host: str = Form(...),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(""),
    mqtt_password: str = Form(""),
    mqtt_topic: str = Form("QIOT/#"),
    duration: int = Form(10),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    try:
        discovered = discover_mqtt_tags(
            host=mqtt_host,
            port=mqtt_port,
            username=mqtt_username,
            password=mqtt_password,
            topic=mqtt_topic,
            duration=duration,
        )

        return templates.TemplateResponse(
            "mqtt_discovery.html",
            {
                "request": request,
                "user": user,
                "sites": db.query(Site).all(),
                "discovered": discovered,
                "discovered_json": json.dumps(discovered),
                "form_data": {
                    "site_id": site_id,
                    "gateway_code": gateway_code,
                    "mqtt_host": mqtt_host,
                    "mqtt_port": mqtt_port,
                    "mqtt_username": mqtt_username,
                    "mqtt_password": mqtt_password,
                    "mqtt_topic": mqtt_topic,
                    "duration": duration,
                },
                "message": f"Discovery completed. Found {len(discovered)} sub-topics.",
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "mqtt_discovery.html",
            {
                "request": request,
                "user": user,
                "sites": db.query(Site).all(),
                "discovered": None,
                "form_data": {},
                "error": str(e),
            }
        )


@router.post("/save")
def save_discovered_tags(
    request: Request,
    site_id: int = Form(...),
    gateway_code: str = Form(...),
    mqtt_host: str = Form(...),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(""),
    mqtt_password: str = Form(""),
    mqtt_topic: str = Form("QIOT/#"),
    selected_tags: list[str] = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    gateway = db.query(Gateway).filter(Gateway.code == gateway_code).first()

    if not gateway:
        gateway = Gateway(
            site_id=site_id,
            code=gateway_code,
            is_active=True,
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
            mqtt_topic=mqtt_topic,
        )
        db.add(gateway)
        db.commit()
        db.refresh(gateway)
    else:
        gateway.site_id = site_id
        gateway.is_active = True
        gateway.mqtt_host = mqtt_host
        gateway.mqtt_port = mqtt_port
        gateway.mqtt_username = mqtt_username
        gateway.mqtt_password = mqtt_password
        gateway.mqtt_topic = mqtt_topic
        db.commit()
        db.refresh(gateway)

    created_count = 0

    for item in selected_tags:
        data = json.loads(item)

        base_topic = data["base_topic"]
        slot_name = data["slot_name"]
        tag_key = data["key"]
        tag_name = data["name"]
        tag_unit = data.get("unit", "")

        sensor_code = base_topic.replace("/", "_").replace(":", "_")

        sensor = (
            db.query(Sensor)
            .filter(
                Sensor.gateway_id == gateway.id,
                Sensor.code == sensor_code
            )
            .first()
        )

        if not sensor:
            sensor = Sensor(
                gateway_id=gateway.id,
                code=sensor_code,
                name=slot_name,
                sensor_type="MQTT_DEVICE",
                is_active=True,
            )
            db.add(sensor)
            db.commit()
            db.refresh(sensor)

        existing_tag = (
            db.query(Tag)
            .filter(
                Tag.sensor_id == sensor.id,
                Tag.key == tag_key
            )
            .first()
        )

        if not existing_tag:
            db.add(Tag(
                sensor_id=sensor.id,
                key=tag_key,
                display_name=tag_name,
                unit=tag_unit,
                log_enabled=True,
            ))
            created_count += 1

    db.commit()
    
    start_single_gateway_worker(gateway.id)

    return RedirectResponse("/devices", status_code=303)