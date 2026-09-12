from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.domains.identity.models import User
from app.domains.identity.service import get_user_by_id, user_has_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTHENTICATION_FAILED", "message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_error
    except jwt.PyJWTError:
        raise credentials_error

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(code: str):
    def _checker(current_user: CurrentUser) -> User:
        if not user_has_permission(current_user, code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": f"Missing required permission: {code}",
                },
            )
        return current_user

    return _checker
