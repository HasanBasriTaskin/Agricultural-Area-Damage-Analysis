from typing import Protocol
import numpy as np

class ScoringStrategy(Protocol):
    """
    Protocol for raster-based damage scoring strategies.
    All fusion strategies must implement the `calculate_score` method.
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
        """
        Calculates the damage score array based on SAR, MS arrays and Weather scalars.
        Returns a float numpy array with scores between 0 and 1.
        """
        pass

    def classify_score(self, score_array: np.ndarray) -> np.ndarray:
        """
        Classifies the continuous damage score into discrete classes.
        Returns an integer numpy array (e.g. 0=None, 1=Slight, 2=Moderate, 3=Severe).
        """
        pass
