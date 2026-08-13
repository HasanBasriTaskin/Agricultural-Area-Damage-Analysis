import ee
from typing import Any
from datetime import datetime
from app.domain.interfaces.satellite_data_client import ISatelliteDataClient
import uuid

class FakeSatelliteClient(ISatelliteDataClient):
    def __init__(self):
        try:
            import json
            from google.oauth2 import service_account
            key_path = 'secrets/gee-service-account.json'
            with open(key_path) as f:
                key_data = json.load(f)
            creds = service_account.Credentials.from_service_account_file(
                key_path, scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(creds, project=key_data['project_id'])
        except Exception as e:
            print(f"Failed to initialize EE in fake client: {e}")

    def get_sar_image(self, aoi_wkt: str, start_date: datetime, end_date: datetime) -> Any:
        # Returns a dummy constant image to simulate GEE response
        return ee.Image.constant(0.1).rename('VV').addBands(ee.Image.constant(0.01).rename('VH'))

    def download_image(self, image: Any, aoi_wkt: str, scale: int, prefix: str) -> str:
        # Returns a fake MinIO key
        return f"fake_minio_bucket/{prefix}_{uuid.uuid4()}.tif"
