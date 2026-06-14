from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.services.event_logger import log_event
from app.core.database import get_db
from app.core.templates import templates
from app.core.deps import require_roles
from app.core.security import hash_password
from app.models import User, Role, Customer

router = APIRouter(prefix="/users")


@router.get("")
def index(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": user,
            "users": db.query(User).order_by(User.id.desc()).all(),
            "roles": db.query(Role).all(),
            "customers": db.query(Customer).all(),
        }
    )


@router.post("/add")
def add(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role_id: int = Form(...),
    customer_id: str = Form(""),
    phone: str = Form(""),
    must_change_password: str = Form("off"),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    customer_id_val = int(customer_id) if customer_id.strip() else None

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse("/users", 303)

    db.add(User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role_id=role_id,
        customer_id=customer_id_val,
        phone=phone,
        is_active=True,
        must_change_password=True if must_change_password == "on" else False,
        password_expiry=datetime.utcnow() + timedelta(days=90),
    ))

    db.commit()
    
    log_event(
        db,
        user,
        "Users",
        "Create User",
        f"Created user {name}"
    )
    
    return RedirectResponse("/users", 303)


@router.post("/update")
def update(
    user_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    role_id: int = Form(...),
    customer_id: str = Form(""),
    phone: str = Form(""),
    is_active: str = Form("off"),
    must_change_password: str = Form("off"),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    u = db.query(User).filter(User.id == user_id).first()

    if u:
        u.name = name
        u.email = email
        u.role_id = role_id
        u.customer_id = int(customer_id) if customer_id.strip() else None
        u.phone = phone
        u.is_active = True if is_active == "on" else False
        u.must_change_password = True if must_change_password == "on" else False
        db.commit()
        
        log_event(
            db,
            user,
            "Users",
            "Update User",
            f"Updated user {u.name}"
        )

    return RedirectResponse("/users", 303)


@router.post("/reset-password")
def reset_password(
    user_id: int = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    u = db.query(User).filter(User.id == user_id).first()

    if u:
        u.password_hash = hash_password(new_password)
        u.must_change_password = True
        u.password_expiry = datetime.utcnow() + timedelta(days=90)
        db.commit()
        
        log_event(
            db,
            user,
            "Users",
            "Reset Password",
            f"Password reset for {u.name}"
        )

    return RedirectResponse("/users", 303)


@router.post("/disable")
def disable(
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    u = db.query(User).filter(User.id == user_id).first()

    if u:
        u.is_active = False
        db.commit()
        
        log_event(
            db,
            user,
            "Users",
            "Disable User",
            f"Disabled user {u.name}"
        )

    return RedirectResponse("/users", 303)


@router.post("/enable")
def enable(
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    u = db.query(User).filter(User.id == user_id).first()

    if u:
        u.is_active = True
        db.commit()
        
        log_event(
            db,
            user,
            "Users",
            "Enable User",
            f"Enabled user {u.name}"
        )

    return RedirectResponse("/users", 303)


@router.post("/delete")
def delete(
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("super_admin"))
):
    u = db.query(User).filter(User.id == user_id).first()

    if u:
        user_name = u.name
        db.delete(u)
        db.commit()
        
        log_event(
            db,
            user,
            "Users",
            "Delete User",
            f"Deleted user {user_name}"
        )

    return RedirectResponse("/users", 303)