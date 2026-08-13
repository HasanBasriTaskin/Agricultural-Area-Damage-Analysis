import ee
import math
from datetime import datetime, timedelta
from app.domain.interfaces.satellite_data_client import ISatelliteDataClient

class SarPipelineService:
    def __init__(self, satellite_client: ISatelliteDataClient):
        self.satellite_client = satellite_client

    def run_pipeline(self, aoi_wkt: str, event_date: datetime) -> str:
        """
        Runs the SAR pipeline to generate NBMI, DPSVIm, and Ratio_dB layers.
        Downloads the resulting image and returns its MinIO object key.
        """
        # 1. Define pre-event and post-event time windows
        # pre-event: 30 days before event up to the event date
        pre_start = event_date - timedelta(days=30)
        pre_end = event_date
        
        # post-event: event date up to 12 days after
        post_start = event_date
        post_end = event_date + timedelta(days=12)

        # 2. Get ARD images (Linear Units)
        # Note: The client uses gee_s1_ard which outputs LINEAR units since FORMAT='LINEAR'
        pre_img = self.satellite_client.get_sar_image(aoi_wkt, pre_start, pre_end)
        post_img = self.satellite_client.get_sar_image(aoi_wkt, post_start, post_end)

        # Select VV and VH bands from POST image for DPSVIm and Ratio
        vv = post_img.select('VV')
        vh = post_img.select('VH')

        # 3. Calculate NBMI = (σ°post - σ°pre) / (σ°post + σ°pre)
        # We use VV band for NBMI as it is sensitive to soil moisture
        vv_pre = pre_img.select('VV')
        vv_post = post_img.select('VV')
        
        nbmi = vv_post.subtract(vv_pre).divide(vv_post.add(vv_pre)).rename('NBMI')

        # 4. Calculate DPSVIm (dos Santos et al. 2021)
        # DPDD = (VV - VH) / sqrt(2)
        # CR = VV / VH
        # DPSVIm = DPDD * CR * VH
        # VV and VH must be linear!
        dpdd = vv.subtract(vh).divide(ee.Number(math.sqrt(2)))
        cr = vv.divide(vh)
        dpsvim = dpdd.multiply(cr).multiply(vh).rename('DPSVIm')

        # 5. Calculate Ratio_dB = VV_dB - VH_dB
        # We need to convert linear to dB for this: 10 * log10(Linear)
        vv_db = vv.log10().multiply(10)
        vh_db = vh.log10().multiply(10)
        ratio_db = vv_db.subtract(vh_db).rename('Ratio_dB')

        # 6. Combine bands into a single image
        final_image = ee.Image.cat([nbmi, dpsvim, ratio_db])

        # 7. Download to MinIO
        # Using a default scale of 10m for Sentinel-1
        minio_key = self.satellite_client.download_image(final_image, aoi_wkt, scale=10, prefix='sar_result')
        
        return minio_key
