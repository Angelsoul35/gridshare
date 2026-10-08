"""Application configuration, loaded from environment variables (prefix ``GS_``)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GS_", env_file=".env", extra="ignore")

    environment: str = "local"
    n_houses: int = 20
    grid_buy_cents: float = 80.0
    grid_sell_cents: float = 20.0

    chain_enabled: bool = True
    chain_rpc_url: str = "http://anvil:8545"
    contract_address: str = ""
    chain_private_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
