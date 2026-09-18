"""Starter design blueprints ("start from a template" instead of an empty canvas). Purely static,
data-only definitions - instantiating one just creates ordinary DesignComponent/DesignRelationship
rows (not real Assets), exactly like a manually drawn design, so the result is a normal draft the
user can edit, connect further, or map to inventory like anything else.
"""

from dataclasses import dataclass, field


@dataclass
class TemplateComponent:
    key: str
    component_type: str
    name: str
    position: dict
    safe_pin: str | None = None


@dataclass
class TemplateRelationship:
    source_key: str
    target_key: str
    relationship_type: str = "connected_to"
    link_type: str | None = None


@dataclass
class DesignTemplate:
    code: str
    name: str
    description: str
    category: str
    components: list[TemplateComponent] = field(default_factory=list)
    relationships: list[TemplateRelationship] = field(default_factory=list)


TEMPLATES: list[DesignTemplate] = [
    DesignTemplate(
        code="small_branch",
        name="Small Branch",
        description="WAN router, firewall, access switch, and a local server for a small branch site.",
        category="branch",
        components=[
            TemplateComponent("router", "router", "Branch Router", {"x": 0, "y": 0}, safe_pin="wan"),
            TemplateComponent("firewall", "firewall", "Branch Firewall", {"x": 0, "y": 140}, safe_pin="internet_edge"),
            TemplateComponent("switch", "switch", "Branch Switch", {"x": 0, "y": 280}, safe_pin="branch"),
            TemplateComponent("server", "server", "Branch Server", {"x": 0, "y": 420}, safe_pin="branch"),
        ],
        relationships=[
            TemplateRelationship("router", "firewall", link_type="wan"),
            TemplateRelationship("firewall", "switch", link_type="lan"),
            TemplateRelationship("switch", "server", link_type="lan"),
        ],
    ),
    DesignTemplate(
        code="three_tier_campus",
        name="3-Tier Campus",
        description="WAN edge into a core/distribution/access campus LAN with a wireless controller on the core.",
        category="campus",
        components=[
            TemplateComponent("wan_router", "router", "WAN Router", {"x": 340, "y": 0}, safe_pin="wan"),
            TemplateComponent("edge_fw", "firewall", "Edge Firewall", {"x": 340, "y": 140}, safe_pin="internet_edge"),
            TemplateComponent("core_sw", "switch", "Core Switch", {"x": 340, "y": 280}, safe_pin="campus_core"),
            TemplateComponent("dist_sw_1", "switch", "Distribution Switch 1", {"x": 160, "y": 420}, safe_pin="campus_distribution"),
            TemplateComponent("dist_sw_2", "switch", "Distribution Switch 2", {"x": 520, "y": 420}, safe_pin="campus_distribution"),
            TemplateComponent("wlc", "wlc", "Wireless Controller", {"x": 340, "y": 420}, safe_pin="campus_core"),
            TemplateComponent("access_sw_1", "switch", "Access Switch 1", {"x": 160, "y": 560}, safe_pin="campus_access"),
            TemplateComponent("access_sw_2", "switch", "Access Switch 2", {"x": 520, "y": 560}, safe_pin="campus_access"),
        ],
        relationships=[
            TemplateRelationship("wan_router", "edge_fw", link_type="wan"),
            TemplateRelationship("edge_fw", "core_sw", link_type="lan"),
            TemplateRelationship("core_sw", "dist_sw_1", link_type="lan"),
            TemplateRelationship("core_sw", "dist_sw_2", link_type="lan"),
            TemplateRelationship("core_sw", "wlc", link_type="lan"),
            TemplateRelationship("dist_sw_1", "access_sw_1", link_type="lan"),
            TemplateRelationship("dist_sw_2", "access_sw_2", link_type="lan"),
        ],
    ),
    DesignTemplate(
        code="small_datacenter",
        name="Small Datacenter",
        description="Redundant firewall pair, core switch, load balancer, and application/domain servers.",
        category="datacenter",
        components=[
            TemplateComponent("dc_router", "router", "DC Router", {"x": 300, "y": 0}, safe_pin="internet_edge"),
            TemplateComponent("dc_fw_a", "firewall", "DC Firewall A", {"x": 160, "y": 140}, safe_pin="internet_edge"),
            TemplateComponent("dc_fw_b", "firewall", "DC Firewall B", {"x": 440, "y": 140}, safe_pin="internet_edge"),
            TemplateComponent("dc_core_sw", "switch", "DC Core Switch", {"x": 300, "y": 280}, safe_pin="data_center"),
            TemplateComponent("dc_lb", "load_balancer", "Load Balancer", {"x": 300, "y": 420}, safe_pin="data_center"),
            TemplateComponent("dc_app_1", "server", "App Server 1", {"x": 160, "y": 560}, safe_pin="data_center"),
            TemplateComponent("dc_app_2", "server", "App Server 2", {"x": 440, "y": 560}, safe_pin="data_center"),
            TemplateComponent("dc_dc", "domain_controller", "Domain Controller", {"x": 300, "y": 560}, safe_pin="data_center"),
        ],
        relationships=[
            TemplateRelationship("dc_router", "dc_fw_a", link_type="wan"),
            TemplateRelationship("dc_router", "dc_fw_b", link_type="wan"),
            TemplateRelationship("dc_fw_a", "dc_core_sw", link_type="lan"),
            TemplateRelationship("dc_fw_b", "dc_core_sw", link_type="lan"),
            TemplateRelationship("dc_core_sw", "dc_lb", link_type="lan"),
            TemplateRelationship("dc_lb", "dc_app_1", link_type="lan"),
            TemplateRelationship("dc_lb", "dc_app_2", link_type="lan"),
            TemplateRelationship("dc_core_sw", "dc_dc", link_type="lan"),
        ],
    ),
]

_BY_CODE = {t.code: t for t in TEMPLATES}


def list_templates() -> list[DesignTemplate]:
    return TEMPLATES


def get_template(code: str) -> DesignTemplate | None:
    return _BY_CODE.get(code)
