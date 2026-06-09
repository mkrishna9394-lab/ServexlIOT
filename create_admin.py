from app.core.database import Base, engine, SessionLocal
from app.models import *
from app.core.security import hash_password
from app.models.user import User, Role

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    if not db.query(Role).filter(Role.name == 'super_admin').first():
        db.add_all([Role(name='super_admin'), Role(name='admin'), Role(name='customer_user'), Role(name='engineer')])
        db.commit()
    role = db.query(Role).filter(Role.name == 'super_admin').first()
    user = db.query(User).filter(User.email == 'admin@example.com').first()
    if not user:
        db.add(User(name='Super Admin', email='admin@example.com', password_hash=hash_password('Admin@123'), role_id=role.id, is_active=True))
        db.commit()
    print('Ready. Login: admin@example.com / Admin@123')
finally:
    db.close()
