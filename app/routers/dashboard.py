from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Customer, Gateway, Sensor, Tag, LiveValue, Alert

router = APIRouter()

@router.get('/dashboard')
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(require_user)):
    stats = {
        'customers': db.query(Customer).count(),
        'gateways': db.query(Gateway).count(),
        'sensors': db.query(Sensor).count(),
        'tags': db.query(Tag).count(),
        'active_alerts': db.query(Alert).filter(Alert.status == 'active').count()
    }
    return templates.TemplateResponse(
        'dashboard.html',
        {'request': request, 'user': user, 'stats': stats}
    )

@router.get('/api/live-values')
def live_values(db: Session = Depends(get_db), user=Depends(require_user)):
    rows = (
        db.query(LiveValue, Tag, Sensor)
        .join(Tag, LiveValue.tag_id == Tag.id)
        .join(Sensor, Tag.sensor_id == Sensor.id)
        .order_by(LiveValue.timestamp.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "tag_id": tag.id,
            "sensor_name": sensor.name,
            "tag_name": tag.display_name,
            "value": live.value,
            "timestamp": live.timestamp.strftime("%Y-%m-%d %H:%M:%S") if live.timestamp else ""
        }
        for live, tag, sensor in rows
    ]