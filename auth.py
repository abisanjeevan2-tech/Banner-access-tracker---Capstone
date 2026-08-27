from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from itsdangerous import URLSafeTimedSerializer
from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session serializer
session_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    """Create a session token for a user"""
    return session_serializer.dumps({"user_id": user_id, "created": datetime.utcnow().isoformat()})


def verify_session_token(token: str, max_age: int = settings.SESSION_MAX_AGE) -> Optional[int]:
    """Verify and decode a session token, returns user_id if valid"""
    try:
        data = session_serializer.loads(token, max_age=max_age)
        return data.get("user_id")
    except Exception:
        return None
