from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
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
    environment: str = "development"
    require_auth: bool = False

    # Static bearer identities are intended for service accounts and local/dev use.
    # Example: GCCI_AUTH_TOKENS='{"token":"SERVICE:ingestion-worker"}'
    auth_tokens: dict[str, str] = Field(default_factory=dict)

    # Provider-neutral OIDC/JWT configuration for human users. When configured,
    # unknown static tokens are validated against the issuer JWKS.
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_role_claim: str = "roles"
    oidc_name_claim: str = "name"
    oidc_allowed_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    # Base64-encoded 32-byte AES-GCM key. Contact-value writes/reveals are disabled
    # when the key is absent, so development can run without silently storing plaintext.
    contact_vault_key_b64: str | None = None
    contact_fingerprint_key: str | None = None
    internal_service_token: str | None = None

    source_timeout_seconds: float = Field(default=8.0, gt=0, le=60)
    gdot_camera_arcgis_url: str = (
        "https://enterprisegis.dot.ga.gov/hosting/rest/services/"
        "web_trafficcameras/MapServer/0/query"
    )
    camera_refresh_seconds: int = Field(default=300, ge=60, le=86400)
    camera_min_expected_records: int = Field(default=10, ge=1, le=10000)

    candidate_time_window_seconds: int = Field(default=20 * 60, ge=30)
    candidate_radius_meters: float = Field(default=5000.0, gt=0)
    same_incident_threshold: float = Field(default=0.82, ge=0, le=1)
    related_incident_threshold: float = Field(default=0.62, ge=0, le=1)

    camera_search_radius_meters: float = Field(default=4000.0, gt=0)
    max_camera_results: int = Field(default=8, ge=1, le=50)
    camera_preservation_before_minutes: int = Field(default=10, ge=0, le=180)
    camera_preservation_after_minutes: int = Field(default=10, ge=0, le=180)
    max_gap_results: int = Field(default=10, ge=1, le=50)

    database_url: str = "postgresql+asyncpg://gcci:gcci@localhost:5432/gcci"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)

    worker_poll_seconds: float = Field(default=5.0, gt=0)
    worker_batch_size: int = Field(default=250, ge=1, le=5000)
    worker_reprocess_lookback_minutes: int = Field(default=30, ge=1, le=1440)

    canonical_scorer_url: str = "http://localhost:3001/api/scoring/score"
    canonical_scorer_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    scoring_worker_batch_size: int = Field(default=100, ge=1, le=5000)
    scoring_retry_base_seconds: int = Field(default=15, ge=1, le=3600)
    scoring_retry_max_seconds: int = Field(default=900, ge=1, le=86400)
    score_material_confidence_delta: float = Field(default=0.05, ge=0, le=1)

    weights: CorrelationWeights = CorrelationWeights()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GCCI_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self):
        self.weights.validate_sum()
        if self.environment.lower() == "production":
            if not self.require_auth:
                raise ValueError("GCCI_REQUIRE_AUTH must be true in production")
            has_oidc = bool(self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url)
            if not self.auth_tokens and not has_oidc:
                raise ValueError(
                    "Production authentication requires GCCI_AUTH_TOKENS for service accounts "
                    "or a complete OIDC issuer/audience/JWKS configuration"
                )
            if not self.internal_service_token:
                raise ValueError("GCCI_INTERNAL_SERVICE_TOKEN must be configured in production")
            if not self.contact_vault_key_b64 or not self.contact_fingerprint_key:
                raise ValueError("Contact vault encryption and fingerprint keys are required in production")
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("Production CORS origins must be explicit and cannot contain '*'")
        return self


settings = Settings()
