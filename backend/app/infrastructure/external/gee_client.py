import ee
import json
from datetime import datetime, timedelta
from typing import Any
from shapely.geometry.base import BaseGeometry
from shapely import wkt
from google.oauth2 import service_account
from app.domain.interfaces.satellite_data_client import ISatelliteDataClient
from app.infrastructure.external.gee_s1_ard import wrapper

class GEESatelliteClient(ISatelliteDataClient):
    def __init__(self, key_path: str = 'secrets/gee-service-account.json'):
        with open(key_path) as f:
            key_data = json.load(f)
        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=['https://www.googleapis.com/auth/earthengine']
        )
        ee.Initialize(creds, project=key_data['project_id'])

    def _geometry_to_ee_feature(self, aoi_wkt: str) -> ee.Geometry:
        geom = wkt.loads(aoi_wkt)
        if geom.geom_type == 'Polygon':
            coords = list(geom.exterior.coords)
            return ee.Geometry.Polygon(coords)
        elif geom.geom_type == 'MultiPolygon':
            coords = [list(poly.exterior.coords) for poly in geom.geoms]
            return ee.Geometry.MultiPolygon(coords)
        else:
            raise ValueError("Unsupported geometry type")

    def get_sar_image(self, aoi_wkt: str, start_date: datetime, end_date: datetime) -> Any:
        # Wrapper parameters for ARD
        parameter = {
            'START_DATE': start_date.strftime('%Y-%m-%d'),
            'STOP_DATE': end_date.strftime('%Y-%m-%d'),
            'POLARIZATION': 'VVVH',
            'ORBIT': 'BOTH',
            'ROI': self._geometry_to_ee_feature(aoi_wkt),
            'APPLY_BORDER_NOISE_CORRECTION': True,
            'APPLY_SPECKLE_FILTERING': True,
            'SPECKLE_FILTER_FRAMEWORK': 'MULTI',
            'SPECKLE_FILTER': 'LEE',
            'SPECKLE_FILTER_KERNEL_SIZE': 5,
            'SPECKLE_FILTER_NR_OF_IMAGES': 10,
            'APPLY_TERRAIN_FLATTENING': True,
            'DEM': ee.Image('USGS/SRTMGL1_003'),
            'TERRAIN_FLATTENING_MODEL': 'VOLUME',
            'TERRAIN_FLATTENING_ADDITIONAL_LAYERS': ['layover', 'shadow'],
            'FORMAT': 'LINEAR', # CRITICAL: MUST BE LINEAR FOR DPSVIm
            'CLIP_TO_ROI': True,
            'SAVE_ASSETS': False
        }
        
        # This wrapper returns an ee.ImageCollection
        s1_processed = wrapper.s1_preproc(parameter)
        
        # We mosaic or return the first image
        # Given we want the nearest pass, let's just mosaic
        image = s1_processed[0].mosaic().clip(parameter['ROI'])
        return image

    def download_image(self, image: Any, aoi_wkt: str, scale: int, prefix: str) -> str:
        """
        In a real scenario, this gets a download URL, downloads the tif to MinIO,
        and returns the MinIO key.
        """
        roi = self._geometry_to_ee_feature(aoi_wkt)
        url = image.getDownloadURL({
            'scale': scale,
            'region': roi,
            'format': 'GEO_TIFF'
        })
        
        import requests
        import uuid
        import os
        
        response = requests.get(url)
        response.raise_for_status()
        
        # For now, save locally (MinIO integration to be done in S2-T7/Sprint 7 properly, 
        # or we just write it to a local temp file and simulate MinIO)
        os.makedirs('temp_downloads', exist_ok=True)
        filename = f"temp_downloads/{prefix}_{uuid.uuid4()}.tif"
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        return filename
