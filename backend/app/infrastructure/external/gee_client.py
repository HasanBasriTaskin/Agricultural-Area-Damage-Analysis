import ee
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any
from shapely.geometry.base import BaseGeometry
from shapely import wkt
from google.oauth2 import service_account
from app.domain.interfaces.satellite_data_client import ISatelliteDataClient

# Add gee_s1_ard to sys.path so its internal imports work
gee_s1_ard_path = os.path.join(os.path.dirname(__file__), 'gee_s1_ard')
if gee_s1_ard_path not in sys.path:
    sys.path.insert(0, gee_s1_ard_path)

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
            'TERRAIN_FLATTENING_ADDITIONAL_LAYOVER_SHADOW_BUFFER': 0,
            'FORMAT': 'LINEAR', # CRITICAL: MUST BE LINEAR FOR DPSVIm
            'CLIP_TO_ROI': True,
            'SAVE_ASSET': False,
            'ASSET_ID': None
        }
        
        # This wrapper returns an ee.ImageCollection
        s1_processed = wrapper.s1_preproc(parameter)
        
        # Validate that we actually found images
        count = s1_processed.size().getInfo()
        if count == 0:
            raise ValueError(f"No Sentinel-1 images found in this area between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.")
        
        # We mosaic or return the first image
        # Given we want the nearest pass, let's just mosaic
        image = s1_processed.mosaic().clip(parameter['ROI'])
        
        # Faz 0: Apply Agriculture Mask (ESA WorldCover v200 - class 40 is cropland)
        world_cover = ee.ImageCollection("ESA/WorldCover/v200").first().clip(parameter['ROI'])
        agri_mask = world_cover.eq(40)
        image = image.updateMask(agri_mask)
        
        return image

    def get_ms_image(self, aoi_wkt: str, start_date: datetime, end_date: datetime) -> Any:
        roi = self._geometry_to_ee_feature(aoi_wkt)
        
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))
                      
        count = collection.size().getInfo()
        if count == 0:
            raise ValueError(f"No Sentinel-2 images found in this area between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.")
            
        def apply_scl_mask(image):
            scl = image.select('SCL')
            # Mask out 3 (cloud shadow), 8 (cloud medium prob), 9 (cloud high prob), 10 (cirrus), 11 (snow/ice)
            mask = (scl.neq(3)
                    .And(scl.neq(8))
                    .And(scl.neq(9))
                    .And(scl.neq(10))
                    .And(scl.neq(11)))
            return image.updateMask(mask)
            
        # Apply mask and median mosaic
        image = collection.map(apply_scl_mask).median().clip(roi)
        
        # Resample 20m bands to 10m
        b10m = image.select(['B2', 'B3', 'B4', 'B8'])
        # Get the projection of a native 10m band
        proj10m = collection.first().select('B2').projection()
        
        b20m = image.select(['B5', 'B8A', 'B11']).resample('bilinear').reproject(
            crs=proj10m,
            scale=10
        )
        
        ms_image = ee.Image.cat([b10m, b20m])
        
        # Faz 0: Apply Agriculture Mask
        world_cover = ee.ImageCollection("ESA/WorldCover/v200").first().clip(roi)
        agri_mask = world_cover.eq(40)
        
        return ms_image.updateMask(agri_mask)

    def download_image(self, image: Any, aoi_wkt: str, scale: int, prefix: str) -> str:
        """
        In a real scenario, this gets a download URL, downloads the tif to MinIO,
        and returns the MinIO key.

        # TODO (Sprint sonrası / Mentor sunumu öncesi):
        # GEE'nin getDownloadURL() metodu maksimum 32768 piksel/kenar sınırına sahip.
        # 10m çözünürlükte bu ~25,000 ha'a karşılık geliyor.
        # Daha büyük AOI'ler için şu yöntemlerden biri uygulanmalı:
        #   1. AOI'yi küçük tile'lara (ızgara) böl, her birini ayrı indir, sonra birleştir (mosaic).
        #   2. ee.batch.Export.image.toCloudStorage() API'sine geç (asenkron, GCS/MinIO hedef).
        # Frontend tarafında alan sınırı kontrolü eklendi (25,000 ha) ancak
        # büyük alan desteği için backend tile-split mimarisine geçilmesi gerekiyor.
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
        from app.infrastructure.external.minio_client import MinioStorageClient
        
        response = requests.get(url)
        response.raise_for_status()
        
        os.makedirs('temp_downloads', exist_ok=True)
        unique_id = uuid.uuid4()
        filename = f"temp_downloads/{prefix}_{unique_id}.tif"
        object_name = f"rasters/{prefix}_{unique_id}.tif"
        
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        # Upload to MinIO
        try:
            minio_client = MinioStorageClient()
            minio_client.upload_file(
                local_path=filename,
                object_name=object_name,
                content_type="image/tiff"
            )
        except Exception as e:
            # Fallback if MinIO is temporarily unreachable
            pass
            
        return filename
