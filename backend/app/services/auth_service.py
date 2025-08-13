from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from ..db import models

# Simple settings (could be externalized)
SECRET_KEY = "dev-secret-change-me"  # in production load from env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(raw, hashed)

def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, email: str, password: str) -> Optional[models.User]:
        user = self.db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password or ""):
            return None
        return user

    def register_if_absent(self, email: str, password: Optional[str] = None) -> models.User:
        user = self.db.query(models.User).filter(models.User.email == email).first()
        if user:
            return user
        user = models.User(email=email, hashed_password=hash_password(password or "demo-pass"))
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
