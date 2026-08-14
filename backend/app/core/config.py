import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/damage_analysis")

    # MinIO Storage Settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "damage-analysis-artifacts")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # Weather Verification Thresholds
    WEATHER_PRECIPITATION_THRESHOLD_MM: float = 30.0  # >30mm means flood/heavy rain anomaly
    WEATHER_WIND_SPEED_THRESHOLD_KMH: float = 60.0  # >60kmh means storm anomaly
    WEATHER_DAYS_TO_LOOK_BACK: int = 5  # Fetch weather data up to 5 days before the event_date

    # Fusion Classification Thresholds
    FUSION_THRESHOLD_SLIGHT: float = 0.20
    FUSION_THRESHOLD_MODERATE: float = 0.45
    FUSION_THRESHOLD_SEVERE: float = 0.70

    class Config:
        env_file = ".env"

settings = Settings()
