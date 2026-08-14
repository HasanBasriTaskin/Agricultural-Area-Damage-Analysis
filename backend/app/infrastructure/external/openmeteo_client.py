import httpx
from datetime import datetime, date
from typing import Dict, Any

class OpenMeteoClient:
    """
    Client for Open-Meteo Historical Weather API (ERA5 based).
    Documentation: https://open-meteo.com/en/docs/historical-weather-api
    """
    
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    
    async def get_historical_weather(self, lat: float, lon: float, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Fetches daily precipitation sum (mm), max wind speed (km/h) and soil moisture (m³/m³)
        for the given date range. Uses ERA5 data provided seamlessly by Open-Meteo archive API.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": "precipitation_sum,wind_speed_10m_max,soil_moisture_0_to_7cm_mean",
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("daily", {})
