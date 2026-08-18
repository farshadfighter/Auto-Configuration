from fastapi import APIRouter

from app.domains.assets.router import router as assets_router
from app.domains.audit.router import router as audit_router
from app.domains.credentials.router import router as credentials_router
from app.domains.identity.router import router as identity_router

api_router = APIRouter()
api_router.include_router(identity_router, tags=["identity"])
api_router.include_router(assets_router, tags=["assets"])
api_router.include_router(credentials_router, tags=["credentials"])
api_router.include_router(audit_router, tags=["audit"])
