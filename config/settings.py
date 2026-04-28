from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Local PostgreSQL ──────────────────────────────────────
    db_host:     str = Field(default="localhost")
    db_port:     int = Field(default=5432)
    db_name:     str = Field(default="Innovatics_Retail")
    db_user:     str = Field(default="postgres")
    db_password: str = Field(default="changeme")

    @property
    def database_url(self) -> str:
        """Single connection string used everywhere in the project."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Scraper ───────────────────────────────────────────────
    scraper_headless:    bool  = Field(default=True)
    scraper_slow_mo:     int   = Field(default=800)
    scraper_timeout:     int   = Field(default=30000)
    scraper_max_retries: int   = Field(default=3)
    scraper_delay_min:   float = Field(default=2.0)
    scraper_delay_max:   float = Field(default=5.0)

    # ── POC metadata ──────────────────────────────────────────
    data_label: str = Field(default="demonstration_data")
    poc_run_id: str = Field(default="poc_run_001")


# Single import used by every module
settings = Settings()
