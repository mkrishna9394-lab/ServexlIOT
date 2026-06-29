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
    __tablename__ = 'sensors'

    id = Column(Integer, primary_key=True)
    gateway_id = Column(Integer, ForeignKey('gateways.id'))
    code = Column(String(80))
    name = Column(String(120))
    sensor_type = Column(String(80))
    is_active = Column(Boolean, default=True)
    is_configured = Column(Boolean, default=False)

    gateway = relationship('Gateway', back_populates='sensors')
    tags = relationship('Tag', back_populates='sensor')
class Tag(Base):
    __tablename__='tags'; id=Column(Integer, primary_key=True); sensor_id=Column(Integer, ForeignKey('sensors.id')); key=Column(String(80)); display_name=Column(String(120)); unit=Column(String(40)); low_limit=Column(Float, nullable=True); high_limit=Column(Float, nullable=True); log_enabled=Column(Boolean, default=False)
    sensor=relationship('Sensor', back_populates='tags')

class GatewayDeleteLog(Base):
    __tablename__ = "gateway_delete_logs"

    id = Column(Integer, primary_key=True)
    gateway_code = Column(String(100))
    reason = Column(String(500))
    deleted_at = Column(DateTime, default=datetime.now)


class MeterDeleteLog(Base):
    __tablename__ = "meter_delete_logs"

    id = Column(Integer, primary_key=True)
    meter_code = Column(String(100))
    meter_name = Column(String(120))
    reason = Column(String(500))
    deleted_at = Column(DateTime, default=datetime.now)

class GatewayAssignmentLog(Base):
    __tablename__ = "gateway_assignment_logs"

    id = Column(Integer, primary_key=True)
    gateway_id = Column(Integer, nullable=True)
    gateway_code = Column(String(100))

    from_customer = Column(String(160), nullable=True)
    from_site = Column(String(160), nullable=True)

    to_customer = Column(String(160), nullable=True)
    to_site = Column(String(160), nullable=True)

    action = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)    

class ConfiguredMeter(Base):
    __tablename__ = "configured_meters"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"))
    gateway_id = Column(Integer, ForeignKey("gateways.id"))

    code = Column(String(80))
    name = Column(String(120))
    sensor_type = Column(String(80))

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    sensor = relationship("Sensor")
    gateway = relationship("Gateway")


class ConfiguredTag(Base):
    __tablename__ = "configured_tags"

    id = Column(Integer, primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"))
    configured_meter_id = Column(Integer, ForeignKey("configured_meters.id"))

    key = Column(String(120))

    # Original MQTT tag name
    display_name = Column(String(120))

    # User-defined alias
    alias_name = Column(String(120))

    # Original MQTT unit
    unit = Column(String(40))

    # User-defined unit
    custom_unit = Column(String(40))

    # Analog/Digital/Counter/String
    tag_type = Column(String(40))

    low_limit = Column(Float, nullable=True)
    high_limit = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    tag = relationship("Tag")
    configured_meter = relationship("ConfiguredMeter")

class GatewayHealthLog(Base):
    __tablename__ = "gateway_health_logs"

    id = Column(Integer, primary_key=True)
    gateway_id = Column(Integer, nullable=True)
    gateway_code = Column(String(100))
    status = Column(String(20))  # Online / Offline
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)    