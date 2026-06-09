from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer
from app.core.config import settings
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
def token_serializer():
    return URLSafeSerializer(settings.SECRET_KEY, salt='auth')
