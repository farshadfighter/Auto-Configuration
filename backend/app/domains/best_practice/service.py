import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.db.base import utcnow
from app.domains.assets.models import Asset, AssetRole, AssetType
from app.domains.best_practice import engine
from app.domains.best_practice.models import (
    ArchitectureFinding,
    BestPracticeRun,
    BestPracticeRunStatus,
    FindingStatus,
    finding_assets,
)
from app.domains.topology import service as topology_service
from app.domains.topology.models import TopologyLink, TopologyNode, TopologyNodeType


def _generate_finding_code() -> str:
    return f"FND-{uuid.uuid4().hex[:8].upper()}"


def _build_asset_contexts(db: Session) -> dict[uuid.UUID, dict]:
    topology_service.sync_nodes_from_assets(db)
    topology_service.sync_links_from_relationships(db)
    db.flush()

    degree: dict[uuid.UUID, int] = defaultdict(int)
    nodes_by_asset = {
        n.reference_id: n
        for n in db.scalars(select(TopologyNode).where(TopologyNode.node_type == TopologyNodeType.DEVICE))
    }
    node_id_to_asset = {n.id: asset_id for asset_id, n in nodes_by_asset.items()}
    for link in db.scalars(select(TopologyLink)):
        for node_id in (link.source_node_id, link.destination_node_id):
            asset_id = node_id_to_asset.get(node_id)
            if asset_id:
                degree[asset_id] += 1

    asset_types = {t.id: t.code for t in db.scalars(select(AssetType))}
    roles = {r.id: r.code for r in db.scalars(select(AssetRole))}

    contexts = {}
    for asset in db.scalars(select(Asset).where(Asset.deleted_at.is_(None))):
        contexts[asset.id] = {
            "asset": {
                "id": str(asset.id),
                "asset_code": asset.asset_code,
                "criticality": asset.criticality.value,
                "status": asset.status.value,
                "managed": asset.managed.value,
                "owner_id": str(asset.owner_id) if asset.owner_id else None,
                "site_id": str(asset.site_id) if asset.site_id else None,
                "zone_id": str(asset.zone_id) if asset.zone_id else None,
                "environment_id": str(asset.environment_id) if asset.environment_id else None,
                "management_ip": str(asset.management_ip) if asset.management_ip is not None else None,
                "asset_type_code": asset_types.get(asset.asset_type_id),
                "role_code": roles.get(asset.role_id) if asset.role_id else None,
                "metadata": asset.asset_metadata or {},
            },
            "topology": {"degree": degree.get(asset.id, 0)},
        }
    return contexts


def run_analysis(db: Session, *, triggered_by: uuid.UUID | None) -> BestPracticeRun:
    run = BestPracticeRun(triggered_by=triggered_by, status=BestPracticeRunStatus.RUNNING, started_at=utcnow())
    db.add(run)
    db.flush()

    try:
        rules = engine.load_rules()
        contexts = _build_asset_contexts(db)

        # Open findings from a prior run are superseded by fresh evaluation each run, so a
        # fixed condition doesn't leave a stale NEW finding behind. Findings a human has already
        # triaged (accepted/ignored/remediated/closed/in_review) are left untouched.
        db.query(ArchitectureFinding).filter(ArchitectureFinding.status == FindingStatus.NEW).delete()
        db.flush()

        findings_created = 0
        for rule in rules:
            for asset_id, context in contexts.items():
                if not engine.evaluate_rule_against_context(rule, context):
                    continue
                finding = ArchitectureFinding(
                    finding_code=_generate_finding_code(),
                    run_id=run.id,
                    rule_code=rule.id,
                    title=rule.title,
                    technology=rule.technology,
                    category=rule.category,
                    severity=rule.severity,
                    current_state=context["asset"],
                    expected_state={"condition": rule.conditions},
                    recommendation=rule.recommendation,
                    status=FindingStatus.NEW,
                    detected_at=utcnow(),
                )
                db.add(finding)
                db.flush()
                db.execute(finding_assets.insert().values(finding_id=finding.id, asset_id=asset_id))
                findings_created += 1

        run.rules_evaluated = len(rules)
        run.findings_created = findings_created
        run.status = BestPracticeRunStatus.SUCCESS
        run.completed_at = utcnow()
    except Exception:
        run.status = BestPracticeRunStatus.FAILED
        run.completed_at = utcnow()
        db.flush()
        raise

    db.flush()
    return run


def list_findings(
    db: Session, *, status: str | None = None, severity: str | None = None, page: int = 1, page_size: int = 50
) -> tuple[list[ArchitectureFinding], int]:
    query = select(ArchitectureFinding)
    if status:
        query = query.where(ArchitectureFinding.status == status)
    if severity:
        query = query.where(ArchitectureFinding.severity == severity)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(ArchitectureFinding.detected_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return items, total


def get_finding(db: Session, finding_id: uuid.UUID) -> ArchitectureFinding:
    finding = db.get(ArchitectureFinding, finding_id)
    if not finding:
        raise NotFoundError("FINDING_NOT_FOUND", f"Finding {finding_id} not found")
    return finding


def get_finding_asset_ids(db: Session, finding_id: uuid.UUID) -> list[uuid.UUID]:
    return list(db.scalars(select(finding_assets.c.asset_id).where(finding_assets.c.finding_id == finding_id)))


def accept_finding(db: Session, finding_id: uuid.UUID) -> ArchitectureFinding:
    finding = get_finding(db, finding_id)
    finding.status = FindingStatus.ACCEPTED
    db.flush()
    return finding


def ignore_finding(db: Session, finding_id: uuid.UUID, reason: str) -> ArchitectureFinding:
    if not reason or not reason.strip():
        raise ValidationAppError("IGNORE_REASON_REQUIRED", "A reason is required to ignore a finding")
    finding = get_finding(db, finding_id)
    finding.status = FindingStatus.IGNORED
    finding.ignore_reason = reason
    db.flush()
    return finding
