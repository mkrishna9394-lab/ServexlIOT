from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.core.security import hash_password
from app.models import User, Role, Customer
router=APIRouter(prefix='/users')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('users.html', {'request':request,'user':user,'users':db.query(User).all(),'roles':db.query(Role).all(),'customers':db.query(Customer).all()})
@router.post('/add')
def add(name:str=Form(...), email:str=Form(...), password:str=Form(...), role_id:int=Form(...), customer_id:int|None=Form(None), db:Session=Depends(get_db), user=Depends(require_user)):
    db.add(User(name=name,email=email,password_hash=hash_password(password),role_id=role_id,customer_id=customer_id,is_active=True)); db.commit(); return RedirectResponse('/users',303)
