from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Customer, Gateway, Sensor, Tag, LiveValue, Alert
router=APIRouter()
@router.get('/dashboard')
def dashboard(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    stats={
        'customers': db.query(Customer).count(), 'gateways': db.query(Gateway).count(), 'sensors': db.query(Sensor).count(),
        'tags': db.query(Tag).count(), 'active_alerts': db.query(Alert).filter(Alert.status=='active').count(),
        'live': db.query(LiveValue).order_by(LiveValue.timestamp.desc()).limit(12).all()
    }
    return templates.TemplateResponse('dashboard.html', {'request':request,'user':user,'stats':stats})
