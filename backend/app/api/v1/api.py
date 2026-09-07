from fastapi import APIRouter

from app.domains.architecture_recommendation.router import router as architecture_recommendation_router
from app.domains.assets.router import router as assets_router
from app.domains.audit.router import router as audit_router
from app.domains.best_practice.router import router as best_practice_router
from app.domains.approval.router import router as approval_router
from app.domains.backup.router import router as backup_router
from app.domains.configuration.catalog_router import router as catalog_router
from app.domains.configuration.router import router as configuration_router
from app.domains.credentials.router import router as credentials_router
from app.domains.deployment.router import router as deployment_router
from app.domains.design.router import router as design_router
from app.domains.discovery.router import router as discovery_router
from app.domains.drift.router import router as drift_router
from app.domains.identity.router import router as identity_router
from app.domains.reporting.router import router as reporting_router
from app.domains.topology.router import router as topology_router

api_router = APIRouter()
api_router.include_router(identity_router, tags=["identity"])
api_router.include_router(assets_router, tags=["assets"])
api_router.include_router(credentials_router, tags=["credentials"])
api_router.include_router(audit_router, tags=["audit"])
api_router.include_router(discovery_router, tags=["discovery"])
api_router.include_router(topology_router, tags=["topology"])
api_router.include_router(best_practice_router, tags=["best_practice"])
api_router.include_router(design_router, tags=["design"])
api_router.include_router(configuration_router, tags=["configuration"])
api_router.include_router(catalog_router, tags=["catalog"])
api_router.include_router(approval_router, tags=["approval"])
api_router.include_router(backup_router, tags=["backup"])
api_router.include_router(deployment_router, tags=["deployment"])
api_router.include_router(drift_router, tags=["drift"])
api_router.include_router(reporting_router, tags=["reporting"])
api_router.include_router(architecture_recommendation_router, tags=["architecture_recommendation"])
