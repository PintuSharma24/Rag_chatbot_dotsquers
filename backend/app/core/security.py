from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import (
JWT_SECRET_KEY,
JWT_ALGORITHM,
JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)

# Password hashing

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")


    hashed_password = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed_password.decode("utf-8")


# Verify password

def verify_password(
    plain_password: str,
    hashed_password: str
    ) -> bool:
    plain_password_bytes = plain_password.encode("utf-8")
    hashed_password_bytes = hashed_password.encode("utf-8")

    
    return bcrypt.checkpw(
        plain_password_bytes,
        hashed_password_bytes
    )


# Create JWT access token

def create_access_token(data: dict) -> str:
    to_encode = data.copy()


    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return encoded_jwt


# Decode JWT access token

def decode_access_token(token: str):
    try:
        payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM]
        )


        return payload

    except JWTError:
        return None
    
