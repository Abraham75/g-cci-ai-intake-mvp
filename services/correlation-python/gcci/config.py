from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CorrelationWeights(BaseModel):
    temporal: float = 0.30
    spatial: float = 0.30
    roadway: float = 0.15
    direction: float = 0.10
    mechanism: float = 0.10
    corroboration: float = 0.05

    def validate_sum(self) -> None:
        total = (
            self.temporal
            + self.spatial
            + self.roadway
            + self.direction
            + self.mechanism
            + self.corroboration
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Correlation weights must sum to 1.0; got {total}")


class Settings(BaseSettings):
    candidate_time_window_seconds: int = Field(default=20 * 60, ge=30)
    candidate_radius_meters: float = Field(default=5000.0, gt=0)
    same_incident_threshold: float = Field(default=0.82, ge=0, le=1)
    related_incident_threshold: float = Field(default=0.62, ge=0, le=1)
    camera_search_radius_meters: float = Field(default=4000.0, gt=0)
    max_camera_results: int = Field(default=8, ge=1, le=50)
    max_gap_results: int = Field(default=10, ge=1, le=50)

    database_url: str = "postgresql+asyncpg://gcci:gcci@localhost:5432/gcci"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)

    worker_poll_seconds: float = Field(default=5.0, gt=0)
    worker_batch_size: int = Field(default=250, ge=1, le=5000)
    worker_reprocess_lookback_minutes: int = Field(default=30, ge=1, le=1440)

    weights: CorrelationWeights = CorrelationWeights()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GCCI_",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        self.weights.validate_sum()


settings = Settings()
