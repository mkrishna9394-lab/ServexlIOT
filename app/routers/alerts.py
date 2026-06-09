from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Alert
router=APIRouter(prefix='/alerts')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('alerts.html', {'request':request,'user':user,'alerts':db.query(Alert).order_by(Alert.created_at.desc()).all()})
@router.post('/{alert_id}/ack')
def ack(alert_id:int, db:Session=Depends(get_db), user=Depends(require_user)):
    a=db.query(Alert).get(alert_id); a.status='acknowledged'; a.acknowledged_at=datetime.utcnow(); a.acknowledged_by=user.id; db.commit(); return RedirectResponse('/alerts',303)
