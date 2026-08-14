import math
import numpy as np
from scipy import stats
from typing import List, Dict, Any

try:
    import h3
    IS_H3_V4 = hasattr(h3, 'polygon_to_cells')
except ImportError:
    h3 = None
    IS_H3_V4 = False

class HotspotService:
    """
    Computes spatial hotspot analysis using Getis-Ord Local G* statistic
    on H3 hexagonal grid cells.
    """
    
    def _get_neighbors(self, cell: str, valid_cell_set: set) -> List[str]:
        """
        Returns the cell itself and its immediate hexagonal neighbors that exist in the analyzed dataset.
        """
        if not h3:
            return [cell]
            
        if IS_H3_V4:
            neighbors = h3.grid_disk(cell, 1)
        else:
            neighbors = h3.k_ring(cell, 1)
            
        # Filter only cells that are in our AOI dataset
        return [c for c in neighbors if c in valid_cell_set]

    def calculate_getis_ord_g_star(
        self,
        grid_cells: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Takes grid cells with 'h3_index' and 'damage_score'.
        Calculates z-score (G*), p-value and significance classification for each cell.
        """
        n = len(grid_cells)
        if n == 0:
            return []
            
        # Map cell index to score and cell object
        cell_map = {c["h3_index"]: c for c in grid_cells}
        valid_cells = set(cell_map.keys())
        
        scores = np.array([c["damage_score"] for c in grid_cells], dtype=float)
        mean_x = np.mean(scores)
        
        # Calculate standard deviation S
        variance = np.var(scores)
        std_s = np.sqrt(variance)
        
        results = []
        
        for cell_data in grid_cells:
            cell_id = cell_data["h3_index"]
            neighbors = self._get_neighbors(cell_id, valid_cells)
            
            # W_i is number of neighbors (including self)
            w_i = len(neighbors)
            sum_w_i = float(w_i)
            sum_w_i_sq = float(w_i) # Since weights are binary (1.0)
            
            # Sum of scores in local neighborhood
            sum_xj = sum(cell_map[nb]["damage_score"] for nb in neighbors)
            
            if n <= 1 or std_s < 1e-7:
                # No variance or single cell
                z_score = 0.0
                p_value = 1.0
            else:
                numerator = sum_xj - (mean_x * sum_w_i)
                denom_inner = (n * sum_w_i_sq - (sum_w_i ** 2)) / (n - 1)
                
                if denom_inner <= 0:
                    z_score = 0.0
                else:
                    denominator = std_s * math.sqrt(denom_inner)
                    z_score = numerator / denominator if denominator > 0 else 0.0
                    
                # 2-tailed p-value from normal distribution
                p_value = float(2 * (1 - stats.norm.cdf(abs(z_score))))
                
            # Classify significance
            if z_score > 2.576:
                classification = "Hotspot (%99 Güven)"
            elif z_score > 1.960:
                classification = "Hotspot (%95 Güven)"
            elif z_score > 1.645:
                classification = "Hotspot (%90 Güven)"
            elif z_score < -2.576:
                classification = "Coldspot (%99 Güven)"
            elif z_score < -1.960:
                classification = "Coldspot (%95 Güven)"
            elif z_score < -1.645:
                classification = "Coldspot (%90 Güven)"
            else:
                classification = "Anlamsız (Nötr)"
                
            results.append({
                "h3_index": cell_id,
                "centroid_wkt": cell_data.get("centroid_wkt"),
                "centroid_lat": cell_data.get("centroid_lat"),
                "centroid_lon": cell_data.get("centroid_lon"),
                "damage_score": cell_data["damage_score"],
                "intensity": round(float(z_score), 4),
                "confidence": round(float(p_value), 4),
                "classification": classification,
                "is_hotspot": z_score > 1.645
            })
            
        return results
