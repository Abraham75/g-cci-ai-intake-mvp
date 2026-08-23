from __future__ import annotations

from pydantic import BaseModel, Field


class CorrelationWeights(BaseModel):
    temporal: float = 0.30
    spatial: float = 0.30
    roadway: float = 0.15
    direction: float = 0.10
    mechanism: float = 0.10
    corroboration: float = 0.05

    def validate_sum(self) -> None:
        total = self.temporal + self.spatial + self.roadway + self.direction + self.mechanism + self.corroboration
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Correlation weights must sum to 1.0; got {total}")


class Settings(BaseModel):
    candidate_time_window_seconds: int = Field(default=20 * 60, ge=30)
    candidate_radius_meters: float = Field(default=5000.0, gt=0)
    same_incident_threshold: float = Field(default=0.82, ge=0, le=1)
    related_incident_threshold: float = Field(default=0.62, ge=0, le=1)
    camera_search_radius_meters: float = Field(default=4000.0, gt=0)
    max_camera_results: int = Field(default=8, ge=1, le=50)
    max_gap_results: int = Field(default=10, ge=1, le=50)
    weights: CorrelationWeights = CorrelationWeights()

    def model_post_init(self, __context) -> None:
        self.weights.validate_sum()


settings = Settings()
