from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Alert

router = APIRouter(prefix="/alerts")


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    alerts = db.query(Alert).order_by(Alert.id.desc()).all()

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
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if alert:
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.now()

        if hasattr(user, "id"):
            alert.acknowledged_by = user.id

        db.commit()

    return RedirectResponse("/alerts", 303)