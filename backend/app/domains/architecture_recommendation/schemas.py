from pydantic import BaseModel


class SafeRecommendationRequest(BaseModel):
    name: str
