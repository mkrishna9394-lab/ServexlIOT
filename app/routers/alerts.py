from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Alert, Tag, Sensor, Gateway, Site

router = APIRouter(prefix="/alerts")


def is_super_admin(user):
    return user.role and user.role.name == "super_admin"


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    query = (
        db.query(Alert)
        .outerjoin(Tag, Alert.tag_id == Tag.id)
        .outerjoin(Sensor, Tag.sensor_id == Sensor.id)
        .outerjoin(Gateway, Sensor.gateway_id == Gateway.id)
        .outerjoin(Site, Gateway.site_id == Site.id)
    )

    if not is_super_admin(user):
        query = query.filter(Site.customer_id == user.customer_id)

    alerts = query.order_by(Alert.id.desc()).all()

    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "user": user,
            "alerts": alerts,
        }
    )


@router.post("/{alert_id}/ack")
def ack(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    query = (
        db.query(Alert)
        .outerjoin(Tag, Alert.tag_id == Tag.id)
        .outerjoin(Sensor, Tag.sensor_id == Sensor.id)
        .outerjoin(Gateway, Sensor.gateway_id == Gateway.id)
        .outerjoin(Site, Gateway.site_id == Site.id)
        .filter(Alert.id == alert_id)
    )

    if not is_super_admin(user):
        query = query.filter(Site.customer_id == user.customer_id)

    alert = query.first()

    if alert:
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = user.id
        db.commit()
        
        log_event(
            db,
            user,
            "Alerts",
            "Acknowledge Alert",
            f"Alert ID {alert.id}"
        )

    return RedirectResponse("/alerts", 303)