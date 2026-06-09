from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from datetime import datetime
from app.core.database import Base
class Alert(Base):
    __tablename__='alerts'; id=Column(Integer, primary_key=True); tag_id=Column(Integer, ForeignKey('tags.id'), nullable=True); severity=Column(String(20), default='warning'); message=Column(String(255)); status=Column(String(20), default='active'); created_at=Column(DateTime, default=datetime.utcnow); acknowledged_at=Column(DateTime, nullable=True); acknowledged_by=Column(Integer, nullable=True)
class AuditLog(Base):
    __tablename__='audit_logs'; id=Column(Integer, primary_key=True); user_id=Column(Integer, nullable=True); action=Column(String(120)); details=Column(Text); created_at=Column(DateTime, default=datetime.utcnow)
class SystemSetting(Base):
    __tablename__='system_settings'; id=Column(Integer, primary_key=True); key=Column(String(120), unique=True); value=Column(Text)
