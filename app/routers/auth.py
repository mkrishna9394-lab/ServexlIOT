from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.security import verify_password, hash_password
from app.models.user import User
router=APIRouter()
@router.get('/login')
def login_page(request: Request): return templates.TemplateResponse('login.html', {'request':request})
@router.post('/login')
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_active == True).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            'login.html',
            {'request': request, 'error': 'Invalid email or password'}
        )

    request.session["user_id"] = user.id

    resp = RedirectResponse('/dashboard', status_code=303)
    resp.set_cookie('user_id', str(user.id), httponly=True)
    return resp
@router.get('/logout')
def logout(request: Request):
    request.session.clear()
    resp = RedirectResponse('/login')
    resp.delete_cookie('user_id')
    return resp
@router.get('/forgot-password')
def forgot(request:Request): return templates.TemplateResponse('forgot_password.html', {'request':request})
@router.post('/forgot-password')
def forgot_post(request:Request, email:str=Form(...), db:Session=Depends(get_db)):
    return templates.TemplateResponse('forgot_password.html', {'request':request,'message':'Password reset flow placeholder configured. Connect SMTP in Notification Service.'})
