import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.domains.assets.models import Asset
from app.domains.best_practice.models import ArchitectureFinding
from app.domains.design import templates as template_catalog
from app.domains.design.models import (
    ArchitectureDesign,
    ArchitectureDesignVersion,
    DesignApproval,
    DesignAssetMapping,
    DesignComponent,
    DesignRecommendationMapping,
    DesignRelationship,
    DesignVersionStatus,
)


def create_design(db: Session, *, name: str, description: str | None, mode: str, created_by: uuid.UUID | None) -> ArchitectureDesign:
    design = ArchitectureDesign(name=name, description=description, mode=mode, created_by=created_by)
    db.add(design)
    db.flush()
    version = ArchitectureDesignVersion(design_id=design.id, version_number=1, created_by=created_by)
    db.add(version)
    db.flush()
    return design


def list_design_templates() -> list[template_catalog.DesignTemplate]:
    return template_catalog.list_templates()


def create_design_from_template(
    db: Session, *, template_code: str, name: str, description: str | None, created_by: uuid.UUID | None
) -> ArchitectureDesign:
    template = template_catalog.get_template(template_code)
    if not template:
        raise ValidationAppError("UNKNOWN_DESIGN_TEMPLATE", f"No design template '{template_code}'")

    design = create_design(db, name=name, description=description, mode="manual", created_by=created_by)
    version = get_latest_version(db, design.id)

    component_id_by_key: dict[str, uuid.UUID] = {}
    for tc in template.components:
        component = DesignComponent(
            design_version_id=version.id,
            component_type=tc.component_type,
            name=tc.name,
            properties={"safe_pin": tc.safe_pin} if tc.safe_pin else None,
            position=tc.position,
        )
        db.add(component)
        db.flush()
        component_id_by_key[tc.key] = component.id

    for tr in template.relationships:
        db.add(
            DesignRelationship(
                design_version_id=version.id,
                source_component_id=component_id_by_key[tr.source_key],
                target_component_id=component_id_by_key[tr.target_key],
                relationship_type=tr.relationship_type,
                link_type=tr.link_type,
            )
        )
    db.flush()
    return design


def get_design(db: Session, design_id: uuid.UUID) -> ArchitectureDesign:
    design = db.get(ArchitectureDesign, design_id)
    if not design:
        raise NotFoundError("DESIGN_NOT_FOUND", f"Design {design_id} not found")
    return design


def list_designs(db: Session, *, page: int = 1, page_size: int = 50) -> tuple[list[ArchitectureDesign], int]:
    total = db.scalar(select(func.count()).select_from(ArchitectureDesign)) or 0
    items = list(
        db.scalars(
            select(ArchitectureDesign)
            .order_by(ArchitectureDesign.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def get_latest_version(db: Session, design_id: uuid.UUID) -> ArchitectureDesignVersion:
    version = db.scalar(
        select(ArchitectureDesignVersion)
        .where(ArchitectureDesignVersion.design_id == design_id)
        .order_by(ArchitectureDesignVersion.version_number.desc())
        .limit(1)
    )
    if not version:
        raise NotFoundError("DESIGN_VERSION_NOT_FOUND", f"No versions found for design {design_id}")
    return version


def get_version(db: Session, version_id: uuid.UUID) -> ArchitectureDesignVersion:
    version = db.get(ArchitectureDesignVersion, version_id)
    if not version:
        raise NotFoundError("DESIGN_VERSION_NOT_FOUND", f"Design version {version_id} not found")
    return version


def _require_draft(version: ArchitectureDesignVersion) -> None:
    if version.status != DesignVersionStatus.DRAFT:
        raise ConflictError(
            "DESIGN_VERSION_NOT_EDITABLE",
            f"Design version {version.version_label} is {version.status.value} and cannot be edited. "
            "Create a new version first.",
        )


def create_new_version(db: Session, design_id: uuid.UUID, created_by: uuid.UUID | None) -> ArchitectureDesignVersion:
    """Clones the latest version's components/relationships into a new draft version
    (spec section 22: editing after Approved must produce a new version)."""
    get_design(db, design_id)
    latest = get_latest_version(db, design_id)

    new_version = ArchitectureDesignVersion(
        design_id=design_id, version_number=latest.version_number + 1, created_by=created_by
    )
    db.add(new_version)
    db.flush()

    component_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for component in db.scalars(select(DesignComponent).where(DesignComponent.design_version_id == latest.id)):
        clone = DesignComponent(
            design_version_id=new_version.id,
            component_type=component.component_type,
            technology=component.technology,
            name=component.name,
            properties=component.properties,
            position=component.position,
        )
        db.add(clone)
        db.flush()
        component_id_map[component.id] = clone.id

    if component_id_map:
        mappings = db.scalars(
            select(DesignAssetMapping).where(DesignAssetMapping.design_component_id.in_(component_id_map.keys()))
        )
        for mapping in mappings:
            db.add(DesignAssetMapping(design_component_id=component_id_map[mapping.design_component_id], asset_id=mapping.asset_id))

    for relationship in db.scalars(select(DesignRelationship).where(DesignRelationship.design_version_id == latest.id)):
        db.add(
            DesignRelationship(
                design_version_id=new_version.id,
                source_component_id=component_id_map[relationship.source_component_id],
                target_component_id=component_id_map[relationship.target_component_id],
                relationship_type=relationship.relationship_type,
                source_interface=relationship.source_interface,
                target_interface=relationship.target_interface,
                link_type=relationship.link_type,
                speed_mbps=relationship.speed_mbps,
                vlan=relationship.vlan,
                subnet=relationship.subnet,
            )
        )
    db.flush()
    return new_version


def add_component(db: Session, version_id: uuid.UUID, data: dict) -> DesignComponent:
    version = get_version(db, version_id)
    _require_draft(version)
    component = DesignComponent(design_version_id=version_id, **data)
    db.add(component)
    db.flush()
    return component


def add_relationship(db: Session, version_id: uuid.UUID, data: dict) -> DesignRelationship:
    version = get_version(db, version_id)
    _require_draft(version)
    for key in ("source_component_id", "target_component_id"):
        if not db.get(DesignComponent, data[key]):
            raise NotFoundError("DESIGN_COMPONENT_NOT_FOUND", f"Design component {data[key]} not found")
    relationship = DesignRelationship(design_version_id=version_id, **data)
    db.add(relationship)
    db.flush()
    return relationship


def update_relationship(db: Session, relationship_id: uuid.UUID, data: dict) -> DesignRelationship:
    relationship = db.get(DesignRelationship, relationship_id)
    if not relationship:
        raise NotFoundError("DESIGN_RELATIONSHIP_NOT_FOUND", f"Design relationship {relationship_id} not found")
    version = get_version(db, relationship.design_version_id)
    _require_draft(version)
    for key, value in data.items():
        setattr(relationship, key, value)
    db.flush()
    return relationship


def get_version_graph(db: Session, version_id: uuid.UUID) -> tuple[list[DesignComponent], list[DesignRelationship]]:
    get_version(db, version_id)
    components = list(db.scalars(select(DesignComponent).where(DesignComponent.design_version_id == version_id)))
    relationships = list(
        db.scalars(select(DesignRelationship).where(DesignRelationship.design_version_id == version_id))
    )

    if components:
        mappings = db.execute(
            select(DesignAssetMapping.design_component_id, DesignAssetMapping.asset_id).where(
                DesignAssetMapping.design_component_id.in_([c.id for c in components])
            )
        ).all()
        asset_id_by_component = dict(mappings)
        for component in components:
            component.asset_id = asset_id_by_component.get(component.id)

    return components, relationships


def list_versions(db: Session, design_id: uuid.UUID) -> list[ArchitectureDesignVersion]:
    get_design(db, design_id)
    return list(
        db.scalars(
            select(ArchitectureDesignVersion)
            .where(ArchitectureDesignVersion.design_id == design_id)
            .order_by(ArchitectureDesignVersion.version_number)
        )
    )


_RELATIONSHIP_DIFF_FIELDS = ("source_interface", "target_interface", "link_type", "speed_mbps", "vlan", "subnet")


def compute_version_diff(db: Session, from_version_id: uuid.UUID, to_version_id: uuid.UUID) -> dict:
    """Diffs two versions of the same design by matching components by name and relationships by
    (source name, target name, type) - component/relationship ids are NOT stable across versions
    since create_new_version clones everything with fresh ids, so identity has to be name-based."""
    from_components, from_relationships = get_version_graph(db, from_version_id)
    to_components, to_relationships = get_version_graph(db, to_version_id)

    from_by_name = {c.name: c for c in from_components}
    to_by_name = {c.name: c for c in to_components}

    added_components = sorted(set(to_by_name) - set(from_by_name))
    removed_components = sorted(set(from_by_name) - set(to_by_name))
    changed_components = []
    for name in sorted(set(from_by_name) & set(to_by_name)):
        old, new = from_by_name[name], to_by_name[name]
        changes: dict[str, list] = {}
        if old.component_type != new.component_type:
            changes["component_type"] = [old.component_type, new.component_type]
        old_pin = (old.properties or {}).get("safe_pin")
        new_pin = (new.properties or {}).get("safe_pin")
        if old_pin != new_pin:
            changes["safe_pin"] = [old_pin, new_pin]
        if bool(old.asset_id) != bool(new.asset_id):
            changes["mapped_to_inventory"] = [bool(old.asset_id), bool(new.asset_id)]
        if changes:
            changed_components.append({"name": name, "changes": changes})

    def relationship_key(names_by_id: dict[uuid.UUID, str], relationship: DesignRelationship) -> str:
        source_name = names_by_id.get(relationship.source_component_id, "?")
        target_name = names_by_id.get(relationship.target_component_id, "?")
        return f"{source_name} -> {target_name} ({relationship.relationship_type})"

    from_names_by_id = {c.id: c.name for c in from_components}
    to_names_by_id = {c.id: c.name for c in to_components}
    from_rel_by_key = {relationship_key(from_names_by_id, r): r for r in from_relationships}
    to_rel_by_key = {relationship_key(to_names_by_id, r): r for r in to_relationships}

    added_relationships = sorted(set(to_rel_by_key) - set(from_rel_by_key))
    removed_relationships = sorted(set(from_rel_by_key) - set(to_rel_by_key))
    changed_relationships = []
    for key in sorted(set(from_rel_by_key) & set(to_rel_by_key)):
        old, new = from_rel_by_key[key], to_rel_by_key[key]
        changes = {
            field: [getattr(old, field), getattr(new, field)]
            for field in _RELATIONSHIP_DIFF_FIELDS
            if getattr(old, field) != getattr(new, field)
        }
        if changes:
            changed_relationships.append({"key": key, "changes": changes})

    return {
        "added_components": added_components,
        "removed_components": removed_components,
        "changed_components": changed_components,
        "added_relationships": added_relationships,
        "removed_relationships": removed_relationships,
        "changed_relationships": changed_relationships,
    }


def map_component_to_asset(db: Session, component_id: uuid.UUID, asset_id: uuid.UUID) -> None:
    if not db.get(DesignComponent, component_id):
        raise NotFoundError("DESIGN_COMPONENT_NOT_FOUND", f"Design component {component_id} not found")
    if not db.get(Asset, asset_id):
        raise NotFoundError("ASSET_NOT_FOUND", f"Asset {asset_id} not found")
    exists = db.get(DesignAssetMapping, {"design_component_id": component_id, "asset_id": asset_id})
    if not exists:
        db.add(DesignAssetMapping(design_component_id=component_id, asset_id=asset_id))
        db.flush()


def map_recommendation(db: Session, version_id: uuid.UUID, finding_id: uuid.UUID) -> None:
    get_version(db, version_id)
    if not db.get(ArchitectureFinding, finding_id):
        raise NotFoundError("FINDING_NOT_FOUND", f"Architecture finding {finding_id} not found")
    exists = db.get(DesignRecommendationMapping, {"design_version_id": version_id, "finding_id": finding_id})
    if not exists:
        db.add(DesignRecommendationMapping(design_version_id=version_id, finding_id=finding_id))
        db.flush()


def approve_design(db: Session, design_id: uuid.UUID, approved_by: uuid.UUID | None, comment: str | None) -> ArchitectureDesignVersion:
    version = get_latest_version(db, design_id)
    if version.status == DesignVersionStatus.APPROVED:
        return version

    previous_approved = db.scalar(
        select(ArchitectureDesignVersion).where(
            ArchitectureDesignVersion.design_id == design_id,
            ArchitectureDesignVersion.status == DesignVersionStatus.APPROVED,
        )
    )
    if previous_approved:
        previous_approved.status = DesignVersionStatus.SUPERSEDED

    version.status = DesignVersionStatus.APPROVED
    db.add(DesignApproval(design_version_id=version.id, approved_by=approved_by, comment=comment, approved_at=utcnow()))
    db.flush()
    return version
