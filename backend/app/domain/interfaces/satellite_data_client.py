from typing import Protocol, Any
from datetime import datetime

class ISatelliteDataClient(Protocol):
    def get_sar_image(self, aoi_wkt: str, start_date: datetime, end_date: datetime) -> Any:
        """
        Retrieves a pre-processed SAR image for the given AOI and time range.
        The image should be in linear units (gamma0), not dB.
        """
        ...
        
    def get_ms_image(self, aoi_wkt: str, start_date: datetime, end_date: datetime) -> Any:
        """
        Retrieves a pre-processed Multispectral (Optical) image (e.g., Sentinel-2) 
        for the given AOI and time range.
        """
        ...
        
    def download_image(self, image: Any, aoi_wkt: str, scale: int, prefix: str) -> str:
        """
        Downloads the EE image to MinIO and returns the MinIO object key.
        """
        ...
