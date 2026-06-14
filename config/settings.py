"""Application configuration via Pydantic Settings.

Configuration precedence (lowest to highest):
  1. Code defaults
  2. .env file
  3. Environment variables
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "ecommerce-smartops-agent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ── LLM Gateway ──
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 60

    # ── Embedding ──
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    embedding_device: str = "cpu"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── ChromaDB ──
    chroma_mode: Literal["embedded", "server"] = "embedded"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persist_dir: str = "./data/chroma"

    # ── Agent ──
    max_agent_steps: int = 10
    conversation_window_size: int = 5
    confidence_threshold: float = 0.55
    rate_limit_per_minute: int = 10

    # ── Security ──
    api_key_header: str = "X-API-Key"
    admin_api_keys: list[str] = Field(default_factory=list)
    tenant_header: str = "X-Tenant-ID"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ── Document Processing ──
    max_upload_size_mb: int = 50
    allowed_document_types: list[str] = Field(
        default_factory=lambda: ["pdf", "docx", "txt", "md", "html"]
    )
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ── External API Keys ──
    google_shopping_api_key: str = ""
    # Meta Ads (Facebook Graph API)
    meta_ads_access_token: str = ""
    meta_ads_account_id: str = ""
    # Shopify
    shopify_store_url: str = ""
    shopify_api_key: str = ""
    shopify_api_password: str = ""
    shopify_access_token: str = ""
    # Amazon
    amazon_seller_id: str = ""
    amazon_access_token: str = ""
    # Google Ads
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_customer_id: str = ""
    google_ads_login_customer_id: str = ""
    # ERP
    erp_api_url: str = ""
    erp_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"
