import ee
from datetime import datetime, timedelta
from app.domain.interfaces.satellite_data_client import ISatelliteDataClient

class MsPipelineService:
    def __init__(self, satellite_client: ISatelliteDataClient):
        self.satellite_client = satellite_client

    def run_pipeline(self, aoi_wkt: str, event_date: datetime) -> str:
        """
        Runs the MS pipeline to generate NDMI, NDRE, EVI and Delta layers.
        Downloads the resulting image and returns its MinIO object key.
        """
        # 1. Define pre-event and post-event time windows
        # pre-event: 30 days before event up to the event date
        pre_start = event_date - timedelta(days=30)
        pre_end = event_date
        
        # post-event: event date + 5 days up to + 20 days
        post_start = event_date + timedelta(days=5)
        post_end = event_date + timedelta(days=20)

        # 2. Get MS images
        pre_img = self.satellite_client.get_ms_image(aoi_wkt, pre_start, pre_end)
        post_img = self.satellite_client.get_ms_image(aoi_wkt, post_start, post_end)

        # 3. Define calculation functions
        def calc_ndmi(img):
            # NDMI = (B8 - B11) / (B8 + B11)
            return img.normalizedDifference(['B8', 'B11']).rename('NDMI')

        def calc_ndre(img):
            # NDRE = (B8A - B5) / (B8A + B5)
            return img.normalizedDifference(['B8A', 'B5']).rename('NDRE')

        def calc_evi(img):
            # EVI = 2.5 * (B8 - B4) / (B8 + 6*B4 - 7.5*B2 + 1)
            # Sentinel-2 bands scale is 0-10000. We must scale to 0-1 for standard EVI formula,
            # BUT COPERNICUS/S2_SR_HARMONIZED uses 0.0001 scale factor.
            # We will apply the scale factor first.
            scaled = img.multiply(0.0001)
            
            evi = scaled.expression(
                '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
                    'NIR': scaled.select('B8'),
                    'RED': scaled.select('B4'),
                    'BLUE': scaled.select('B2')
                }
            ).rename('EVI')
            return evi

        # 4. Calculate indices for Pre and Post
        pre_ndmi = calc_ndmi(pre_img)
        pre_ndre = calc_ndre(pre_img)
        pre_evi = calc_evi(pre_img)

        post_ndmi = calc_ndmi(post_img)
        post_ndre = calc_ndre(post_img)
        post_evi = calc_evi(post_img)

        # 5. Calculate Deltas (Post - Pre)
        delta_ndmi = post_ndmi.subtract(pre_ndmi).rename('Delta_NDMI')
        delta_ndre = post_ndre.subtract(pre_ndre).rename('Delta_NDRE')
        delta_evi = post_evi.subtract(pre_evi).rename('Delta_EVI')

        # Rename Pre/Post layers to include prefix
        pre_ndmi = pre_ndmi.rename('Pre_NDMI')
        pre_ndre = pre_ndre.rename('Pre_NDRE')
        pre_evi = pre_evi.rename('Pre_EVI')

        post_ndmi = post_ndmi.rename('Post_NDMI')
        post_ndre = post_ndre.rename('Post_NDRE')
        post_evi = post_evi.rename('Post_EVI')

        # 6. Combine all bands into a single image
        final_image = ee.Image.cat([
            pre_ndmi, pre_ndre, pre_evi,
            post_ndmi, post_ndre, post_evi,
            delta_ndmi, delta_ndre, delta_evi
        ])

        # 7. Download to MinIO
        minio_key = self.satellite_client.download_image(final_image, aoi_wkt, scale=10, prefix='ms_result')
        
        return minio_key
