"""
config.py

GCS configuration for medical records pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigError(Exception):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class GCSConfig:
    """GCS configuration for patient records storage."""

    project_id: str
    bucket_name: str
    raw_prefix: str = "raw"
    summaries_prefix: str = "summaries"
    index_file: str = "index.json"

    @property
    def bucket_uri(self) -> str:
        """Return the GCS bucket URI."""
        return f"gs://{self.bucket_name}"

    @property
    def raw_uri(self) -> str:
        """Return the GCS URI for raw patient records."""
        return f"{self.bucket_uri}/{self.raw_prefix}"

    @property
    def summaries_uri(self) -> str:
        """Return the GCS URI for patient summaries."""
        return f"{self.bucket_uri}/{self.summaries_prefix}"

    @property
    def index_uri(self) -> str:
        """Return the GCS URI for the patient index."""
        return f"{self.bucket_uri}/{self.index_file}"


@lru_cache(maxsize=1)
def get_config() -> GCSConfig:
    """Get GCS configuration from environment variables.

    Returns:
        GCSConfig instance with values from environment.

    Raises:
        ConfigError: If required environment variables are missing.
    """
    project_id = os.getenv("GCS_PROJECT_ID")
    bucket_name = os.getenv("GCS_BUCKET_NAME")

    missing = []
    if not project_id:
        missing.append("GCS_PROJECT_ID")
    if not bucket_name:
        missing.append("GCS_BUCKET_NAME")

    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in your .env file or environment."
        )

    # Type narrowing: at this point we know these are not None
    assert project_id is not None
    assert bucket_name is not None

    return GCSConfig(
        project_id=project_id,
        bucket_name=bucket_name,
        raw_prefix=os.getenv("GCS_RAW_PREFIX", "raw"),
        summaries_prefix=os.getenv("GCS_SUMMARIES_PREFIX", "summaries"),
        index_file=os.getenv("GCS_INDEX_FILE", "index.json"),
    )
