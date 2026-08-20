import os
import uuid
import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
from app.domain.interfaces.scoring_strategy import ScoringStrategy
from typing import Dict, Any

class FusionService:
    def __init__(self, scoring_strategy: ScoringStrategy):
        self.strategy = scoring_strategy

    def run_fusion(
        self,
        job_id: uuid.UUID,
        sar_tif_path: str,
            ms_tif_path: str,
            precipitation_mm: float,
        soil_moisture: float,
        weights: dict
    ) -> Dict[str, Any]:
        """
        Reads the SAR and MS GeoTIFFs, spatially aligns and resamples them onto
        the reference grid, applies the scoring strategy, and saves the resulting
        damage score and classes to a new GeoTIFF.
        """
        
        # 1. Read SAR Raster as the spatial reference template
        with rasterio.open(sar_tif_path) as src_sar:
            # sar bands: 1=NBMI, 2=DPSVIm, 3=Ratio_dB
            nbmi_band = src_sar.read(1).astype(np.float32)
            sar_meta = src_sar.meta.copy()
            sar_shape = (src_sar.height, src_sar.width)
            sar_transform = src_sar.transform
            sar_crs = src_sar.crs
            
            # Normalize NBMI to [0, 1]. Range: [-1, 1] -> [0, 1]
            sar_array = np.clip((nbmi_band + 1.0) / 2.0, 0.0, 1.0)
            sar_array = np.nan_to_num(sar_array, nan=0.0)

        # 2. Read and spatially reproject/align MS Raster to SAR grid
        with rasterio.open(ms_tif_path) as src_ms:
            # ms_result.tif bands from ms_pipeline:
            # 1: Pre_NDMI, 2: Pre_NDRE, 3: Pre_EVI
            # 4: Post_NDMI, 5: Post_NDRE, 6: Post_EVI
            # 7: Delta_NDMI, 8: Delta_NDRE, 9: Delta_EVI
            
            ndmi_aligned = np.zeros(sar_shape, dtype=np.float32)
            ndre_aligned = np.zeros(sar_shape, dtype=np.float32)
            
            if src_ms.count >= 5:
                # Read precomputed Post_NDMI (band 4) and Post_NDRE (band 5)
                reproject(
                    source=rasterio.band(src_ms, 4),
                    destination=ndmi_aligned,
                    src_transform=src_ms.transform,
                    src_crs=src_ms.crs,
                    dst_transform=sar_transform,
                    dst_crs=sar_crs,
                    resampling=Resampling.bilinear
                )
                reproject(
                    source=rasterio.band(src_ms, 5),
                    destination=ndre_aligned,
                    src_transform=src_ms.transform,
                    src_crs=src_ms.crs,
                    dst_transform=sar_transform,
                    dst_crs=sar_crs,
                    resampling=Resampling.bilinear
                )
            elif src_ms.count >= 2:
                reproject(
                    source=rasterio.band(src_ms, 1),
                    destination=ndmi_aligned,
                    src_transform=src_ms.transform,
                    src_crs=src_ms.crs,
                    dst_transform=sar_transform,
                    dst_crs=sar_crs,
                    resampling=Resampling.bilinear
                )
                reproject(
                    source=rasterio.band(src_ms, 2),
                    destination=ndre_aligned,
                    src_transform=src_ms.transform,
                    src_crs=src_ms.crs,
                    dst_transform=sar_transform,
                    dst_crs=sar_crs,
                    resampling=Resampling.bilinear
                )
            else:
                reproject(
                    source=rasterio.band(src_ms, 1),
                    destination=ndmi_aligned,
                    src_transform=src_ms.transform,
                    src_crs=src_ms.crs,
                    dst_transform=sar_transform,
                    dst_crs=sar_crs,
                    resampling=Resampling.bilinear
                )
                ndre_aligned = ndmi_aligned.copy()

            # Normalize NDMI & NDRE from [-1, 1] to [0, 1]
            ndmi_array = np.clip((ndmi_aligned + 1.0) / 2.0, 0.0, 1.0)
            ndmi_array = np.nan_to_num(ndmi_array, nan=0.0)
            
            ndre_array = np.clip((ndre_aligned + 1.0) / 2.0, 0.0, 1.0)
            ndre_array = np.nan_to_num(ndre_array, nan=0.0)

        # 3. Apply Scoring Strategy
        score_array = self.strategy.calculate_score(
            sar_array=sar_array,
            ndmi_array=ndmi_array,
            ndre_array=ndre_array,
            precipitation_mm=precipitation_mm,
            soil_moisture=soil_moisture,
            weights=weights
        )
        
        # 4. Classify Score
        classes_array = self.strategy.classify_score(score_array)
        
        # 5. Save to new GeoTIFF
        os.makedirs('temp_downloads', exist_ok=True)
        fusion_tif_path = f"temp_downloads/fusion_result_{job_id}.tif"
        
        # Update meta for writing
        sar_meta.update({
            "count": 2, # Band 1: Continuous Score, Band 2: Discrete Classes
            "dtype": rasterio.float32,
            "nodata": None
        })
        
        with rasterio.open(fusion_tif_path, 'w', **sar_meta) as dst:
            dst.write(score_array.astype(rasterio.float32), 1)
            dst.set_band_description(1, 'Damage_Score')
            
            dst.write(classes_array.astype(rasterio.float32), 2)
            dst.set_band_description(2, 'Damage_Class')
            
        object_name = f"fusion/fusion_result_{job_id}.tif"
        try:
            from app.infrastructure.external.minio_client import MinioStorageClient
            minio_client = MinioStorageClient()
            minio_client.upload_file(
                local_path=fusion_tif_path,
                object_name=object_name,
                content_type="image/tiff"
            )
        except Exception:
            pass

        return {
            "fusion_tif_path": fusion_tif_path,
            "minio_key": object_name,
            "mean_score": float(np.nanmean(score_array))
        }
