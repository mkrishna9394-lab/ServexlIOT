from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.services.event_logger import log_event
from app.core.database import get_db
from app.core.templates import templates
from app.core.security import verify_password, hash_password
from app.models.user import User

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == email,
        User.is_active == True
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"}
        )

    user.last_login = datetime.utcnow()
    db.commit()

    request.session["user_id"] = user.id
    
    log_event(
        db,
        user,
        "Authentication",
        "Login",
        "User logged in"
    )

    if user.must_change_password:
        resp = RedirectResponse("/change-password", status_code=303)
    else:
        resp = RedirectResponse("/dashboard", status_code=303)

    resp.set_cookie("user_id", str(user.id), httponly=True)
    return resp


@router.get("/change-password")
def change_password_page(
    request: Request,
    db: Session = Depends(get_db)
):
    uid = request.session.get("user_id")

    if not uid:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == int(uid)).first()

    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "user": user
        }
    )


@router.post("/change-password")
def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    uid = request.session.get("user_id")

    if not uid:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == int(uid)).first()

    if not user:
        return RedirectResponse("/login", status_code=303)

    if not verify_password(old_password, user.password_hash):
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": user,
                "error": "Old password is incorrect"
            }
        )

    if new_password != confirm_password:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": user,
                "error": "New password and confirm password do not match"
            }
        )

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_expiry = datetime.utcnow() + timedelta(days=90)

    db.commit()
    log_event(db, user, "Authentication", "Change Password", "User changed password")

    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("user_id")

    if uid:
        user = db.query(User).filter(User.id == int(uid)).first()
        if user:
            log_event(db, user, "Authentication", "Logout", "User logged out")

    request.session.clear()
    resp = RedirectResponse("/login")
    resp.delete_cookie("user_id")
    return resp


@router.get("/forgot-password")
def forgot(request: Request):
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request}
    )


@router.post("/forgot-password")
def forgot_post(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "message": "Password reset flow placeholder configured. Connect SMTP in Notification Service."
        }
    )