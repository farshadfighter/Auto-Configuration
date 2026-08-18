from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.core.responses import success
from app.drivers.registry import get_driver, list_technologies

router = APIRouter()


@router.get("/technologies", response_model=None)
def list_technology_catalog(db: DbSession, current_user=Depends(require_permission("configuration.view"))):
    """Technology Catalog (spec section 48) - what each registered driver supports. Frontend
    forms are built from this instead of being hardcoded per vendor (spec section 118)."""
    catalog = []
    for technology in list_technologies():
        driver = get_driver(technology)
        catalog.append(
            {
                "technology": technology,
                "vendor": driver.manifest.vendor,
                "supported_os": driver.manifest.supported_os,
                "capabilities": driver.manifest.capabilities,
                "rollback_strategy": driver.manifest.rollback_strategy.value,
            }
        )
    return success(catalog)
