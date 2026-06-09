from fastapi import APIRouter, Request, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.core.config import settings
router=APIRouter(prefix='/diagnostics')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    db_ok=True
    try: db.execute(text('SELECT 1'))
    except Exception: db_ok=False
    return templates.TemplateResponse('diagnostics.html', {'request':request,'user':user,'db_ok':db_ok,'mqtt_enabled':settings.MQTT_ENABLED})
