from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class LiveValue(Base):
    __tablename__ = "live_values"

    id = Column(Integer, primary_key=True)
    configured_tag_id = Column(Integer, ForeignKey("configured_tags.id"), unique=True)

    value = Column(Float, nullable=True)
    value_text = Column(String(500), nullable=True)

    quality = Column(String(30), default="GOOD")
    timestamp = Column(DateTime, default=datetime.now)


class HistoricalValue(Base):
    __tablename__ = "historical_values"

    id = Column(Integer, primary_key=True)

    configured_tag_id = Column(
        Integer,
        ForeignKey("configured_tags.id"),
        index=True
    )

    value = Column(Float, nullable=True)
    value_text = Column(String(500), nullable=True)

    timestamp = Column(DateTime, default=datetime.now, index=True)

    source = Column(String(40), default="MQTT")