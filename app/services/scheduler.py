from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.core.config import settings
from app.models import Gateway, Alert, SystemSetting
from app.services.retention_cleanup import cleanup_historical_data

_scheduler = None


def get_int_setting(db, key, default):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    if not setting:
        return default

    try:
        return int(setting.value)
    except Exception:
        return default


def scan_gateway_health():
    db = SessionLocal()

    try:
        offline_seconds = get_int_setting(
            db,
            "data_offline_seconds",
            settings.DATA_OFFLINE_SECONDS
        )

        cutoff = datetime.utcnow() - timedelta(seconds=offline_seconds)

        for gw in db.query(Gateway).filter(Gateway.is_active == True).all():

            if not gw.last_seen or gw.last_seen < cutoff:

                msg = f"Gateway {gw.code} communication failure"

                exists = (
                    db.query(Alert)
                    .filter(
                        Alert.message == msg,
                        Alert.status == "active"
                    )
                    .first()
                )

                if not exists:
                    db.add(
                        Alert(
                            severity="critical",
                            message=msg
                        )
                    )

        db.commit()

    finally:
        db.close()


def start_scheduler():
    global _scheduler

    if _scheduler:
        return

    _scheduler = BackgroundScheduler()

    # Gateway monitoring every 30 sec
    _scheduler.add_job(
        scan_gateway_health,
        "interval",
        seconds=30,
        id="gateway_health",
        replace_existing=True
    )

    # Historical cleanup every day at midnight
    _scheduler.add_job(
        cleanup_historical_data,
        "cron",
        hour=0,
        minute=0,
        id="historical_cleanup",
        replace_existing=True
    )

    _scheduler.start()

    print("Scheduler started")