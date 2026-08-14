from typing import Dict, Any, List
from app.core.config import settings

class WeatherVerificationService:
    def __init__(self):
        self.precip_threshold = settings.WEATHER_PRECIPITATION_THRESHOLD_MM
        self.wind_threshold = settings.WEATHER_WIND_SPEED_THRESHOLD_KMH

    def verify(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the historical weather data from Open-Meteo.
        Data format expected:
        {
            "time": ["2022-01-01", ...],
            "precipitation_sum": [1.2, ...],
            "wind_speed_10m_max": [15.5, ...]
        }
        """
        if not weather_data:
            return {
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 0.0,
                "is_anomaly": False
            }

        precip_sums = weather_data.get("precipitation_sum", [])
        wind_speeds = weather_data.get("wind_speed_10m_max", [])
        soil_moistures = weather_data.get("soil_moisture_0_to_7cm_mean", [])
        temp_maxs = weather_data.get("temperature_2m_max", [])
        temp_mins = weather_data.get("temperature_2m_min", [])
        temp_means = weather_data.get("temperature_2m_mean", [])

        # Filter out None values
        precip_sums = [p for p in precip_sums if p is not None]
        wind_speeds = [w for w in wind_speeds if w is not None]
        soil_moistures = [s for s in soil_moistures if s is not None]
        temp_maxs = [t for t in temp_maxs if t is not None]
        temp_mins = [t for t in temp_mins if t is not None]
        temp_means = [t for t in temp_means if t is not None]

        max_precip = max(precip_sums) if precip_sums else 0.0
        max_wind = max(wind_speeds) if wind_speeds else 0.0
        max_soil_moisture = max(soil_moistures) if soil_moistures else 0.0
        max_temp = max(temp_maxs) if temp_maxs else None
        min_temp = min(temp_mins) if temp_mins else None
        mean_temp = round(sum(temp_means) / len(temp_means), 1) if temp_means else None

        is_anomaly = (max_precip > self.precip_threshold) or (max_wind > self.wind_threshold)

        return {
            "precipitation_mm": max_precip,
            "wind_speed_kmh": max_wind,
            "soil_moisture_m3_m3": max_soil_moisture,
            "temperature_max_c": max_temp,
            "temperature_min_c": min_temp,
            "temperature_mean_c": mean_temp,
            "is_anomaly": is_anomaly
        }
