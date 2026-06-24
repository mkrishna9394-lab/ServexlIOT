from app.models import EventLog


def log_event(db, user, module, action, details=""):
    db.add(EventLog(
        user_id=user.id if user else None,
        user_name=user.name if user else None,
        role=user.role.name if user and user.role else None,
        customer_id=user.customer_id if user else None,
        module=module,
        action=action,
        details=details,
    ))
    db.commit()