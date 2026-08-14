import os
import uuid
import rasterio
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
        Reads the SAR and MS GeoTIFFs, aligns them, applies the scoring strategy,
        and saves the resulting damage score and classes to a new GeoTIFF.
        """
        
        # 1. Read SAR and MS Rasters
        # Both should be exported at 10m scale with the same bounds (ROI)
        # However, to be robust, we assume they align perfectly because 
        # getDownloadURL was called with the exact same region and scale.
        
        with rasterio.open(sar_tif_path) as src_sar:
            # sar bands: 1=NBMI, 2=DPSVIm, 3=Ratio_dB
            # NBMI is band 1 (1-indexed in rasterio)
            # Actually, the strategy expects a single 'sar_array' representing SAR damage.
            # We can use NBMI as the primary indicator, or an average of them.
            # Let's use NBMI (band 1) for now, normalized between 0 and 1.
            # NBMI values range from -1 to 1.
            nbmi_band = src_sar.read(1)
            sar_meta = src_sar.meta.copy()
            
            # Normalize NBMI to [0, 1]. -1 -> 0, 1 -> 1
            sar_array = (nbmi_band + 1) / 2.0
            
        with rasterio.open(ms_tif_path) as src_ms:
            # ms bands: 1=B2, 2=B3, 3=B4, 4=B8, 5=B5, 6=B8A, 7=B11
            # NDMI = (B8A - B11) / (B8A + B11) -> (band 6 - band 7)
            # NDRE = (B8 - B5) / (B8 + B5) -> (band 4 - band 5)
            
            b4 = src_ms.read(3).astype(float)
            b5 = src_ms.read(5).astype(float)
            b8 = src_ms.read(4).astype(float)
            b8a = src_ms.read(6).astype(float)
            b11 = src_ms.read(7).astype(float)
            
            # Calculate NDMI
            # Add small epsilon to avoid division by zero
            eps = 1e-8
            ndmi_array = (b8a - b11) / (b8a + b11 + eps)
            # NDMI values range from -1 to 1. Normalize to 0-1
            ndmi_array = (ndmi_array + 1) / 2.0
            
            # Calculate NDRE
            ndre_array = (b8 - b5) / (b8 + b5 + eps)
            ndre_array = (ndre_array + 1) / 2.0
            
        # 2. Apply Scoring Strategy
        score_array = self.strategy.calculate_score(
            sar_array=sar_array,
            ndmi_array=ndmi_array,
            ndre_array=ndre_array,
            precipitation_mm=precipitation_mm,
            soil_moisture=soil_moisture,
            weights=weights
        )
        
        # 3. Classify Score
        classes_array = self.strategy.classify_score(score_array)
        
        # 4. Save to new GeoTIFF
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
            
            dst.write(classes_array.astype(rasterio.float32), 2) # classes as float32 to match meta dtype
            dst.set_band_description(2, 'Damage_Class')
            
        return {
            "fusion_tif_path": fusion_tif_path,
            "mean_score": float(np.nanmean(score_array))
        }
