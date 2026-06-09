from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_user
from app.models import Customer, Site
router=APIRouter(prefix='/customers')
@router.get('')
def index(request:Request, db:Session=Depends(get_db), user=Depends(require_user)):
    return templates.TemplateResponse('customers.html', {'request':request,'user':user,'customers':db.query(Customer).all(),'sites':db.query(Site).all()})
@router.post('/add')
def add(name:str=Form(...), contact_email:str=Form(''), db:Session=Depends(get_db), user=Depends(require_user)):
    db.add(Customer(name=name, contact_email=contact_email)); db.commit(); return RedirectResponse('/customers',303)
@router.post('/site/add')
def add_site(customer_id:int=Form(...), name:str=Form(...), location:str=Form(''), db:Session=Depends(get_db), user=Depends(require_user)):
    db.add(Site(customer_id=customer_id,name=name,location=location)); db.commit(); return RedirectResponse('/customers',303)
