from pydantic import BaseModel


class SafeRecommendationRequest(BaseModel):
    name: str


class PathFindingOut(BaseModel):
    pin_a: str
    pin_b: str
    source_asset_id: str
    source_asset_name: str
    target_asset_id: str
    target_asset_name: str
    path_asset_ids: list[str]
    path_asset_names: list[str]
    protected: bool
    required_capability: str
    severity: str
