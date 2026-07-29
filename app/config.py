from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Invoice Processing POC"
    environment: str = "development"

    oci_config_profile: str = "DEFAULT"
    oci_region: str = "us-phoenix-1"
    oci_compartment_id: str = ""

    input_bucket: str = "invoice-poc-input"
    output_bucket: str = "invoice-poc-output"
    output_prefix: str = "results/"

    upload_dir: Path = Path("uploads")
    output_dir: Path = Path("output")

    max_upload_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)