"""Frank AI OS — Configurações centrais do sistema."""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ─── App ────────────────────────────────────────────────
    app_name: str = "Frank AI OS"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # ─── AI ─────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-5"
    max_tokens: int = 8192

    # ─── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://frank:frank@localhost:5432/frankdb"
    database_sync_url: str = "postgresql+psycopg2://frank:frank@localhost:5432/frankdb"
    db_pool_size: int = 20
    db_max_overflow: int = 40

    # ─── Redis ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    cache_ttl: int = 3600  # 1 hora

    # ─── Email ──────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "Frank AI OS <frank@davvero.com.br>"
    alert_email: str = "ceo@davvero.com.br"

    # ─── WhatsApp ───────────────────────────────────────────
    whatsapp_api_url: str = ""
    whatsapp_token: str = ""
    whatsapp_admin_number: str = ""
    alert_whatsapp: str = ""

    # ─── Meta Ads ───────────────────────────────────────────
    meta_access_token: str = ""
    meta_ad_account_id: str = ""
    meta_page_id: str = ""

    # ─── LinkedIn ───────────────────────────────────────────
    linkedin_access_token: str = ""
    linkedin_organization_id: str = ""

    # ─── ERP Sults ──────────────────────────────────────────
    sults_api_url: str = "https://api.sults.com.br"
    sults_api_key: str = ""
    sults_tenant_id: str = "davvero"

    # ─── Security ───────────────────────────────────────────
    secret_key: str = "change-in-production"

    # ─── Feature Flags ──────────────────────────────────────
    enable_whatsapp: bool = False
    enable_meta_ads: bool = False
    enable_linkedin: bool = False
    enable_email: bool = True
    mock_external_apis: bool = True

    # ─── Davvero Network ────────────────────────────────────
    network_units_str: str = "DVR-SP-001,DVR-SP-002,DVR-SP-003,DVR-SP-004,DVR-RJ-001,DVR-MG-001,DVR-RS-001"

    @property
    def network_units(self) -> List[str]:
        return self.network_units_str.split(",")

    # ─── CEO Hard Rules ─────────────────────────────────────
    ceo_rule_cmv_max: float = 30.0
    ceo_rule_ebitda_min: float = 10.0
    ceo_rule_rent_max: float = 12.0
    ceo_rule_payback_max: int = 30
    ceo_rule_roi_min: float = 1.5


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
