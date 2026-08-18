import jwt
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, require_permission
from app.core.responses import success
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.domains.audit.service import record_audit_event
from app.domains.identity import service
from app.domains.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    RoleCreate,
    RoleOut,
    TokenResponse,
    UserCreate,
    UserOut,
)

router = APIRouter()


@router.post("/auth/login", response_model=None)
def login(payload: LoginRequest, db: DbSession):
    user = service.authenticate_user(db, payload.username, payload.password)
    if not user:
        record_audit_event(
            db, user_id=None, action="LOGIN_FAILED", object_type="user", object_id=None, result="FAILURE"
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_FAILED", "message": "Invalid username or password"},
        )
    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    record_audit_event(db, user_id=user.id, action="LOGIN_SUCCESS", object_type="user", object_id=user.id, result="SUCCESS")
    db.commit()
    return success(tokens.model_dump())


@router.post("/auth/refresh", response_model=None)
def refresh(payload: RefreshRequest, db: DbSession):
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("not a refresh token")
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_FAILED", "message": "Invalid refresh token"},
        )
    user = service.get_user_by_id(db, decoded["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_FAILED", "message": "User not found or inactive"},
        )
    tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return success(tokens.model_dump())


@router.get("/auth/me", response_model=None)
def me(current_user: CurrentUser):
    return success(UserOut.model_validate(current_user).model_dump(mode="json"))


@router.get("/users", response_model=None)
def list_users(db: DbSession, current_user=Depends(require_permission("user.view"))):
    from app.domains.identity.models import User as UserModel

    users = db.query(UserModel).all()
    return success([UserOut.model_validate(u).model_dump(mode="json") for u in users])


@router.post("/users", response_model=None, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, current_user=Depends(require_permission("user.create"))):
    user = service.create_user(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role_ids=payload.role_ids,
    )
    record_audit_event(
        db, user_id=current_user.id, action="USER_CREATED", object_type="user", object_id=user.id, result="SUCCESS"
    )
    db.commit()
    return success(UserOut.model_validate(user).model_dump(mode="json"))


@router.get("/roles", response_model=None)
def list_roles(db: DbSession, current_user=Depends(require_permission("role.view"))):
    from app.domains.identity.models import Role as RoleModel

    roles = db.query(RoleModel).all()
    return success([RoleOut.model_validate(r).model_dump(mode="json") for r in roles])


@router.post("/roles", response_model=None, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: DbSession, current_user=Depends(require_permission("role.manage"))):
    role = service.create_role(db, payload.name, payload.description, payload.permission_codes)
    record_audit_event(
        db, user_id=current_user.id, action="ROLE_CREATED", object_type="role", object_id=role.id, result="SUCCESS"
    )
    db.commit()
    return success(RoleOut.model_validate(role).model_dump(mode="json"))
