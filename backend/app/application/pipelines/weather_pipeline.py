import uuid
from datetime import datetime, timedelta
import shapely.wkt
from app.infrastructure.external.openmeteo_client import OpenMeteoClient
from app.application.services.weather_verification_service import WeatherVerificationService
from app.core.config import settings

class WeatherPipelineService:
    def __init__(self, openmeteo_client: OpenMeteoClient, verification_service: WeatherVerificationService):
        self.client = openmeteo_client
        self.verification_service = verification_service

    async def run_pipeline(self, job_id: uuid.UUID, aoi_wkt: str, event_date: datetime) -> dict:
        """
        Runs the weather verification pipeline.
        Calculates centroid of the AOI, fetches weather data for X days before event_date,
        verifies thresholds, and returns the result to be saved as WeatherEvent.
        """
        # 1. Calculate centroid from WKT
        polygon = shapely.wkt.loads(aoi_wkt)
        centroid = polygon.centroid
        lat = centroid.y
        lon = centroid.x

        # 2. Determine date range
        end_date = event_date.date()
        start_date = end_date - timedelta(days=settings.WEATHER_DAYS_TO_LOOK_BACK)

        # 3. Fetch data
        weather_data = await self.client.get_historical_weather(lat, lon, start_date, end_date)

        # 4. Verify thresholds
        result = self.verification_service.verify(weather_data)
        
        return result
