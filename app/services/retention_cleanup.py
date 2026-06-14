from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models import HistoricalValue, SystemSetting


def get_int_setting(db, key: str, default: int):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    if not setting:
        return default

    try:
        return int(setting.value)
    except Exception:
        return default


def cleanup_historical_data():
    db = SessionLocal()

    try:
        retention_days = get_int_setting(
            db,
            "historical_retention_days",
            30
        )

        if retention_days <= 0:
            print("Historical cleanup skipped. Retention days <= 0")
            return

        cutoff = datetime.now() - timedelta(days=retention_days)

        deleted_count = (
            db.query(HistoricalValue)
            .filter(HistoricalValue.timestamp < cutoff)
            .delete()
        )

        db.commit()

        print(
            f"Historical cleanup completed. "
            f"Retention={retention_days} days, "
            f"Deleted={deleted_count} records"
        )

    except Exception as e:
        db.rollback()
        print("Historical cleanup error:", e)

    finally:
        db.close()