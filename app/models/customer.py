from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True)
    contact_email = Column(String(160))
    phone = Column(String(40), nullable=True)
    address = Column(String(500), nullable=True)
    logo_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sites = relationship('Site', back_populates='customer')
class Site(Base):
    __tablename__='sites'; id=Column(Integer, primary_key=True); customer_id=Column(Integer, ForeignKey('customers.id')); name=Column(String(160)); location=Column(String(255)); created_at=Column(DateTime, default=datetime.utcnow)
    customer=relationship('Customer', back_populates='sites'); gateways=relationship('Gateway', back_populates='site')
