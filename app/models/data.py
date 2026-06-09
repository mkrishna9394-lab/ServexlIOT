from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from app.core.database import Base
class LiveValue(Base):
    __tablename__='live_values'; id=Column(Integer, primary_key=True); tag_id=Column(Integer, ForeignKey('tags.id'), unique=True); value=Column(Float); quality=Column(String(30), default='GOOD'); timestamp=Column(DateTime, default=datetime.utcnow)
class HistoricalValue(Base):
    __tablename__='historical_values'; id=Column(Integer, primary_key=True); tag_id=Column(Integer, ForeignKey('tags.id'), index=True); value=Column(Float); timestamp=Column(DateTime, default=datetime.utcnow, index=True); source=Column(String(40), default='MQTT')
