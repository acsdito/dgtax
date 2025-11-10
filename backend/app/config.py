from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações principais da aplicação.
    """

    api_title: str = "DGTAX QnA API"
    api_version: str = "0.1.0"

    ollama_base_url: str = "http://caitanserver:5010"
    ollama_model: str = "llama3"
    ollama_timeout_seconds: int = 120

    postgres_host: str = "caitanserver"
    postgres_port: int = 5432
    postgres_database: str = "dgtax"
    postgres_user: str = "admin"
    postgres_password: str = "admincaitan"
    postgres_min_pool_size: int = 1
    postgres_max_pool_size: int = 5

    max_rows: int = 200

    model_config = SettingsConfigDict(env_file=(".env",), env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância única de configurações.
    """

    return Settings()
