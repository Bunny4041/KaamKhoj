from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(subject: Union[str, int], extra: dict = {}) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access", **extra}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, int]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, token_type: str = "access") -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != token_type:
            raise credentials_exception
        subject: str = payload.get("sub")
        if subject is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def create_email_verification_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": email, "exp": expire, "type": "email_verify"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_email_token(token: str) -> str:
    """Returns email if valid, raises HTTPException otherwise."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") not in ("email_verify", "password_reset"):
            raise HTTPException(status_code=400, detail="Invalid token type")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
