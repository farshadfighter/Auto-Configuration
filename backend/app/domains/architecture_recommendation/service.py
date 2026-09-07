import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.architecture_recommendation import engine
from app.domains.assets.models import Asset, AssetRole, AssetType
from app.domains.design import service as design_service
from app.domains.design.models import ArchitectureDesign, DesignAssetMapping, DesignComponent, DesignMode, DesignRelationship

COLUMN_WIDTH = 260
ROW_HEIGHT = 110


def _assets_by_pin(db: Session) -> dict[str, list[tuple[Asset, str, str | None]]]:
    """Every non-deleted, classified asset grouped by safe_pin, alongside its asset_type code
    and role name (both needed for engine.asset_satisfies_component matching)."""
    rows = db.execute(
        select(Asset, AssetType.code, AssetRole.name)
        .join(AssetType, Asset.asset_type_id == AssetType.id)
        .outerjoin(AssetRole, Asset.role_id == AssetRole.id)
        .where(Asset.deleted_at.is_(None), Asset.safe_pin.isnot(None))
    )
    grouped: dict[str, list[tuple[Asset, str, str | None]]] = {}
    for asset, type_code, role_name in rows:
        grouped.setdefault(asset.safe_pin.value, []).append((asset, type_code, role_name))
    return grouped


def generate_recommendation(db: Session, *, name: str, created_by: uuid.UUID | None) -> ArchitectureDesign:
    """Builds a new Architecture Design pre-populated with a SAFE-inspired reference topology,
    grounded in whatever of the current asset inventory has been classified by Place in the
    Network (Asset.safe_pin). Existing assets appear as real components (mapped back to the
    asset); reference roles the inventory doesn't yet cover appear as recommended-but-missing
    components so the gap is visible directly in the generated diagram."""
    pins = engine.load_pins()
    assets_by_pin = _assets_by_pin(db)

    design = design_service.create_design(
        db,
        name=name,
        description=(
            "Auto-generated from the current asset inventory using a SAFE-inspired Places-in-"
            "the-Network reference model. Dashed components are recommended roles not yet "
            "covered by a classified asset - not a finding from live analysis."
        ),
        mode=DesignMode.BEST_PRACTICE_ASSISTED,
        created_by=created_by,
    )
    version = design_service.get_latest_version(db, design.id)

    component_by_pin_first: dict[str, uuid.UUID] = {}

    for pin in pins:
        pin_assets = assets_by_pin.get(pin.id, [])
        satisfied_component_types: set[str] = set()
        row = 0

        for asset, type_code, role_name in pin_assets:
            component = DesignComponent(
                design_version_id=version.id,
                component_type=type_code,
                name=asset.name,
                properties={"safe_pin": pin.id, "recommended": False},
                position={"x": pin.order * COLUMN_WIDTH, "y": row * ROW_HEIGHT},
            )
            db.add(component)
            db.flush()
            db.add(DesignAssetMapping(design_component_id=component.id, asset_id=asset.id))
            component_by_pin_first.setdefault(pin.id, component.id)
            row += 1

            for rc in pin.recommended_components:
                if rc.component_type in satisfied_component_types:
                    continue
                if engine.asset_satisfies_component(rc, asset_type_code=type_code, role_name=role_name, asset_name=asset.name):
                    satisfied_component_types.add(rc.component_type)

        for rc in pin.recommended_components:
            if rc.component_type in satisfied_component_types:
                continue
            component = DesignComponent(
                design_version_id=version.id,
                component_type=rc.component_type,
                name=rc.name,
                properties={"safe_pin": pin.id, "recommended": True},
                position={"x": pin.order * COLUMN_WIDTH, "y": row * ROW_HEIGHT},
            )
            db.add(component)
            db.flush()
            component_by_pin_first.setdefault(pin.id, component.id)
            row += 1

    for pin in pins:
        source_id = component_by_pin_first.get(pin.id)
        if not source_id:
            continue
        for target_pin_id in pin.connects_to:
            target_id = component_by_pin_first.get(target_pin_id)
            if not target_id:
                continue
            db.add(
                DesignRelationship(
                    design_version_id=version.id,
                    source_component_id=source_id,
                    target_component_id=target_id,
                    relationship_type="connects_to",
                )
            )

    db.flush()
    return design
