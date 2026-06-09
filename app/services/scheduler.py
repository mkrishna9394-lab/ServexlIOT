from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.core.config import settings
from app.models import Gateway, Alert
_scheduler=None

def scan_gateway_health():
    db=SessionLocal()
    try:
        cutoff=datetime.utcnow()-timedelta(seconds=settings.DATA_OFFLINE_SECONDS)
        for gw in db.query(Gateway).filter(Gateway.is_active==True).all():
            if not gw.last_seen or gw.last_seen < cutoff:
                msg=f'Gateway {gw.code} communication failure'
                if not db.query(Alert).filter(Alert.message==msg, Alert.status=='active').first():
                    db.add(Alert(severity='critical', message=msg))
        db.commit()
    finally: db.close()

def start_scheduler():
    global _scheduler
    if _scheduler: return
    _scheduler=BackgroundScheduler()
    _scheduler.add_job(scan_gateway_health, 'interval', seconds=30, id='gateway_health', replace_existing=True)
    _scheduler.start()
