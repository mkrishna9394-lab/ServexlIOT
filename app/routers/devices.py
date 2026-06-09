from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Site, Gateway, Sensor, Tag, LiveValue, HistoricalValue, Alert

router = APIRouter(prefix='/devices')


@router.get('')
def index(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    tags = (
        db.query(Tag)
        .join(Sensor, Tag.sensor_id == Sensor.id)
        .order_by(Tag.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        'devices.html',
        {
            'request': request,
            'user': user,
            'sites': db.query(Site).all(),
            'gateways': db.query(Gateway).all(),
            'sensors': db.query(Sensor).all(),
            'tags': tags,
        }
    )


@router.post('/gateway/add')
def gateway(
    site_id: int = Form(...),
    code: str = Form(...),
    mqtt_host: str = Form('localhost'),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(''),
    mqtt_password: str = Form(''),
    mqtt_topic: str = Form('#'),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.add(Gateway(
        site_id=site_id,
        code=code,
        is_active=True,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        mqtt_topic=mqtt_topic
    ))
    db.commit()
    return RedirectResponse('/devices', 303)


@router.post('/sensor/add')
def sensor(
    gateway_id: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    sensor_type: str = Form('general'),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    db.add(Sensor(
        gateway_id=gateway_id,
        code=code,
        name=name,
        sensor_type=sensor_type
    ))
    db.commit()
    return RedirectResponse('/devices', 303)


@router.post('/tag/add')
def tag_add(
    sensor_id: int = Form(...),
    key: str = Form(...),
    display_name: str = Form(...),
    unit: str = Form(''),
    low_limit: str = Form(""),
    high_limit: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    low_limit_val = float(low_limit) if low_limit.strip() else None
    high_limit_val = float(high_limit) if high_limit.strip() else None
    
    db.add(Tag(
        sensor_id=sensor_id,
        key=key,
        display_name=display_name,
        unit=unit,
        low_limit=low_limit,
        high_limit=high_limit
    ))
    db.commit()
    return RedirectResponse('/devices', 303)


@router.post('/tag/update')
def tag_update(
    tag_id: int = Form(...),
    sensor_id: int = Form(...),
    key: str = Form(...),
    display_name: str = Form(...),
    unit: str = Form(''),
    low_limit: str = Form(""),
    high_limit: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    low_limit_val = float(low_limit) if low_limit.strip() else None
    high_limit_val = float(high_limit) if high_limit.strip() else None

    tag = db.query(Tag).filter(Tag.id == tag_id).first()

    if tag:
        tag.sensor_id = sensor_id
        tag.key = key
        tag.display_name = display_name
        tag.unit = unit
        tag.low_limit = low_limit_val
        tag.high_limit = high_limit_val
        db.commit()

    return RedirectResponse('/devices', 303)


@router.post('/tag/delete')
def tag_delete(
    tag_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()

    if tag:
        db.query(LiveValue).filter(LiveValue.tag_id == tag_id).delete()
        db.query(HistoricalValue).filter(HistoricalValue.tag_id == tag_id).delete()
        db.query(Alert).filter(Alert.tag_id == tag_id).delete()

        db.delete(tag)
        db.commit()

    return RedirectResponse('/devices', 303)