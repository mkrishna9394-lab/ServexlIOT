from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User


def current_user(request: Request, db: Session):
    uid = request.session.get("user_id")

    if not uid:
        return None

    try:
        uid = int(uid)
    except Exception:
        return None

    return db.query(User).filter(User.id == uid, User.is_active == True).first()


def require_user(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    return user