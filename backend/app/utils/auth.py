"""
Authentication utilities for verifying Supabase JWT tokens.

Provides a FastAPI dependency that extracts and validates the access token
from the Authorization header, then returns the authenticated user's UUID.
"""

import logging
import re
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from ..config import settings

logger = logging.getLogger(__name__)

# Password validation rules (mirrors frontend logic)
_PASSWORD_SPECIAL = re.compile(r'[!@#$%^&*()\-_+=\[\]{};:\'"\\|,.<>/?`~]')


def validate_password(password: str) -> list[str]:
    """
    Validate a password against the project rules.

    Rules:
      - minimum 4 characters
      - at least 2 digits
      - at least 1 special character

    Returns a list of error messages (empty == valid).
    """
    errors: list[str] = []
    if len(password) < 4:
        errors.append("Must be at least 4 characters long")
    digit_count = sum(c.isdigit() for c in password)
    if digit_count < 2:
        errors.append("Must contain at least 2 numbers")
    if not _PASSWORD_SPECIAL.search(password):
        errors.append("Must contain at least 1 special character")
    return errors


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    FastAPI dependency: extract authenticated Supabase user ID from the
    Authorization header (Bearer <access_token>).

    Falls back to ``"anonymous"`` during development when the JWT secret
    is not configured so that existing behaviour is preserved.
    """
    if not authorization:
        # Allow unauthenticated in dev when no JWT secret is set
        if not settings.supabase_jwt_secret:
            return "anonymous"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    # If JWT secret is not configured, allow passthrough for dev
    if not settings.supabase_jwt_secret:
        logger.debug("JWT secret not set – skipping token verification")
        return "anonymous"

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
            )
        return user_id
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
