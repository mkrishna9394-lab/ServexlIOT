from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.core.templates import templates
from app.models import EventLog

router = APIRouter(prefix="/event-logs")

PAGE_SIZE = 10


def is_super_admin(user):
    return user.role and user.role.name == "super_admin"


@router.get("")
def index(
    request: Request,
    page: int = Query(1),
    db: Session = Depends(get_db),
    user=Depends(require_user)
):
    query = db.query(EventLog)

    if not is_super_admin(user):
        query = query.filter(EventLog.customer_id == user.customer_id)

    total_records = query.count()

    logs = (
        query
        .order_by(EventLog.created_at.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE

    return templates.TemplateResponse(
        "event_logs.html",
        {
            "request": request,
            "user": user,
            "logs": logs,
            "page": page,
            "total_pages": total_pages,
        }
    )