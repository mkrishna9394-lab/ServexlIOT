from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import SystemSetting
router=APIRouter(prefix='/settings')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('settings.html', {'request':request,'user':user,'settings':db.query(SystemSetting).all()})
@router.post('/save')
def save(key:str=Form(...), value:str=Form(...), db:Session=Depends(get_db), user=Depends(require_user)):
    s=db.query(SystemSetting).filter(SystemSetting.key==key).first() or SystemSetting(key=key)
    s.value=value; db.add(s); db.commit(); return RedirectResponse('/settings',303)
