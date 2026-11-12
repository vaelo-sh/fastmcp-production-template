"""Typed configuration, read from environment variables (and an optional .env).

Everything that changes between laptops, CI, and production lives here.
No secrets in code: tokens and keys only ever come from the environment.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

CommaList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCP_", env_file=".env", extra="ignore", populate_by_name=True
    )

    env: Literal["dev", "prod"] = "dev"
    name: str = "mcp-to-prod"

    # Transport
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    # Cloud Run (and most container hosts) inject PORT; it wins over MCP_PORT.
    port: int = Field(8000, validation_alias=AliasChoices("PORT", "MCP_PORT"))
    path: str = "/mcp"
    stateless_http: bool = True
    allowed_hosts: CommaList = []

    # Logging and limits
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    rate_limit_rps: float = 10.0

    # Auth (one switch)
    auth: Literal["none", "static", "jwt"] = "none"
    dev_token: str | None = None
    jwt_jwks_uri: str | None = None
    jwt_public_key: str | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    jwt_algorithm: str | None = None
    required_scopes: CommaList = []
    write_scope: str = "notes:write"
    auth_servers: CommaList = []
    base_url: str | None = None

    # Telemetry
    otel_console: bool = False

    @field_validator("allowed_hosts", "required_scopes", "auth_servers", mode="before")
    @classmethod
    def _split_commas(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator(
        "dev_token", "jwt_jwks_uri", "jwt_public_key", "jwt_issuer",
        "jwt_audience", "jwt_algorithm", "base_url", mode="before",
    )
    @classmethod
    def _empty_is_none(cls, v: object) -> object:
        return None if v == "" else v

    @model_validator(mode="after")
    def _check_auth(self) -> "Settings":
        if self.auth == "static" and not self.dev_token:
            raise ValueError("MCP_AUTH=static needs MCP_DEV_TOKEN")
        if self.auth == "static" and len(self.dev_token or "") < 16:
            raise ValueError("MCP_DEV_TOKEN must be at least 16 characters")
        if self.auth == "jwt" and not (self.jwt_jwks_uri or self.jwt_public_key):
            raise ValueError("MCP_AUTH=jwt needs MCP_JWT_JWKS_URI or MCP_JWT_PUBLIC_KEY")
        if self.auth_servers and not self.base_url:
            raise ValueError("MCP_AUTH_SERVERS needs MCP_BASE_URL (the public URL of this server)")
        if self.env == "prod" and self.transport == "http" and self.auth == "none":
            raise ValueError("Refusing to serve HTTP in prod with MCP_AUTH=none")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
