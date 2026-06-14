from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from datetime import datetime, timedelta
from app.core.database import Base
class Alert(Base):
    __tablename__='alerts'; id=Column(Integer, primary_key=True); tag_id=Column(Integer, ForeignKey('tags.id'), nullable=True); severity=Column(String(20), default='warning'); message=Column(String(255)); status=Column(String(20), default='active'); created_at=Column(DateTime, default=datetime.now); acknowledged_at=Column(DateTime, nullable=True); acknowledged_by=Column(Integer, nullable=True)
class AuditLog(Base):
    __tablename__='audit_logs'; id=Column(Integer, primary_key=True); user_id=Column(Integer, nullable=True); action=Column(String(120)); details=Column(Text); created_at=Column(DateTime, default=datetime.now)
class SystemSetting(Base):
    __tablename__='system_settings'; id=Column(Integer, primary_key=True); key=Column(String(120), unique=True); value=Column(Text)
    
class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    user_name = Column(String(120), nullable=True)
    role = Column(String(50), nullable=True)
    customer_id = Column(Integer, nullable=True)

    module = Column(String(80))
    action = Column(String(120))
    details = Column(Text)

    created_at = Column(DateTime, default=datetime.now)    
