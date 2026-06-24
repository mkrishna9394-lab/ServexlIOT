from fastapi import Request, Depends, HTTPException
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

    if user.must_change_password and request.url.path != "/change-password":
        return RedirectResponse("/change-password", status_code=303)

    return user


def require_roles(*allowed_roles):
    def checker(user=Depends(require_user)):
        if isinstance(user, RedirectResponse):
            return user

        role_name = user.role.name if user.role else ""

        if role_name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access denied")

        return user

    return checker