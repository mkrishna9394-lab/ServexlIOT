from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
class Role(Base):
    __tablename__='roles'; id=Column(Integer, primary_key=True); name=Column(String(50), unique=True, nullable=False)
class User(Base):
    __tablename__='users'
    id=Column(Integer, primary_key=True); name=Column(String(120)); email=Column(String(160), unique=True, index=True)
    password_hash=Column(String(255)); role_id=Column(Integer, ForeignKey('roles.id')); customer_id=Column(Integer, ForeignKey('customers.id'), nullable=True)
    is_active=Column(Boolean, default=True); created_at=Column(DateTime, default=datetime.utcnow)
    role=relationship('Role'); customer=relationship('Customer')
