from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
class Gateway(Base):
    __tablename__ = "gateways"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    code = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    mqtt_host = Column(String(255), default="localhost")
    mqtt_port = Column(Integer, default=1883)
    mqtt_username = Column(String(255), default="")
    mqtt_password = Column(String(255), default="")
    mqtt_topic = Column(String(255), default="#")

    last_seen = Column(DateTime, nullable=True)

    site = relationship("Site", back_populates="gateways")
    sensors = relationship("Sensor", back_populates="gateway")
class Sensor(Base):
    __tablename__='sensors'; id=Column(Integer, primary_key=True); gateway_id=Column(Integer, ForeignKey('gateways.id')); code=Column(String(80)); name=Column(String(120)); sensor_type=Column(String(80)); is_active=Column(Boolean, default=True)
    gateway=relationship('Gateway', back_populates='sensors'); tags=relationship('Tag', back_populates='sensor')
class Tag(Base):
    __tablename__='tags'; id=Column(Integer, primary_key=True); sensor_id=Column(Integer, ForeignKey('sensors.id')); key=Column(String(80)); display_name=Column(String(120)); unit=Column(String(40)); low_limit=Column(Float, nullable=True); high_limit=Column(Float, nullable=True); log_enabled=Column(Boolean, default=True)
    sensor=relationship('Sensor', back_populates='tags')
