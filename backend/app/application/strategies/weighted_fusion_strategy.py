import numpy as np
from app.domain.interfaces.scoring_strategy import ScoringStrategy
from app.core.config import settings

class WeightedFusionStrategy(ScoringStrategy):
    """
    Implements a weighted sum fusion formula for crop damage assessment.
    Formula: w1*SAR + w2*NDMI + w3*NDRE + w4*Precipitation + w5*SoilMoisture
    """
    
    def calculate_score(
        self,
        sar_array: np.ndarray,
        ndmi_array: np.ndarray,
        ndre_array: np.ndarray,
        precipitation_mm: float,
        soil_moisture: float,
        weights: dict
    ) -> np.ndarray:
        # Defaults if weights are missing
        w_sar = weights.get('sar', 0.35)
        w_ndmi = weights.get('ndmi', 0.25)
        w_ndre = weights.get('ndre', 0.20)
        w_precip = weights.get('precipitation', 0.12)
        w_sm = weights.get('soil_moisture', 0.08)

        # Ensure total weights sum to 1.0 (approximately)
        total_weight = w_sar + w_ndmi + w_ndre + w_precip + w_sm
        if total_weight > 0:
            w_sar /= total_weight
            w_ndmi /= total_weight
            w_ndre /= total_weight
            w_precip /= total_weight
            w_sm /= total_weight

        # Normalize scalar weather data to [0, 1] range to avoid blowing up the score.
        # Max precipitation assumed to be ~100mm for extreme floods.
        precip_norm = min(precipitation_mm / 100.0, 1.0)
        
        # Soil moisture is typically 0.0 - 0.5 m3/m3. 
        # We normalize it relative to 0.5.
        sm_norm = min(soil_moisture / 0.5, 1.0)

        # Apply weights pixel-wise
        # sar_array, ndmi_array, ndre_array should ideally be normalized [0,1] already 
        # or representing proportional damage.
        
        base_score = (w_sar * sar_array) + (w_ndmi * ndmi_array) + (w_ndre * ndre_array)
        weather_score = (w_precip * precip_norm) + (w_sm * sm_norm)
        
        # The weather score is constant across all pixels for the same AOI/Event.
        # We add it to every pixel.
        final_score = base_score + weather_score
        
        # Clip to [0, 1] range
        final_score = np.clip(final_score, 0.0, 1.0)
        
        return final_score

    def classify_score(self, score_array: np.ndarray) -> np.ndarray:
        """
        Classifies score [0, 1] into:
        1: None (<0.2)
        2: Slight (0.2 - 0.45)
        3: Moderate (0.45 - 0.70)
        4: Severe (>0.70)
        
        Note: Using 1,2,3,4 as integer classes (0 can be nodata).
        """
        classes = np.ones_like(score_array, dtype=np.uint8) # Default to 1 (None)
        
        # Slight
        classes = np.where(
            (score_array >= settings.FUSION_THRESHOLD_SLIGHT) & (score_array < settings.FUSION_THRESHOLD_MODERATE), 
            2, 
            classes
        )
        # Moderate
        classes = np.where(
            (score_array >= settings.FUSION_THRESHOLD_MODERATE) & (score_array < settings.FUSION_THRESHOLD_SEVERE), 
            3, 
            classes
        )
        # Severe
        classes = np.where(
            score_array >= settings.FUSION_THRESHOLD_SEVERE, 
            4, 
            classes
        )
        
        return classes
