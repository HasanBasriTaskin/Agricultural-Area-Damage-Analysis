import json
import numpy as np
import rasterio
from rasterio.mask import mask
import shapely.wkt
from shapely.geometry import mapping, Polygon, Point
from typing import List, Dict, Any

try:
    import h3
    # Check if v4 or v3
    IS_H3_V4 = hasattr(h3, 'polygon_to_cells')
except ImportError:
    h3 = None
    IS_H3_V4 = False

class GridAggregationService:
    def __init__(self, default_resolution: int = 9):
        """
        H3 Resolution 9: ~100m edge length, ~0.1 km2 area (Ideal for agricultural field grid)
        H3 Resolution 8: ~460m edge length, ~0.7 km2 area
        """
        self.default_res = default_resolution

    def _get_optimal_resolution(self, geom: Polygon) -> int:
        """
        Dynamically select H3 resolution based on polygon area so that
        both small fields (e.g. 10-50 ha) and large regions (e.g. 5,000 ha)
        get an optimal, aesthetically pleasing, and statistically rich hexagon tiling.
        """
        # Calculate approx area in ha (degrees to m2)
        bounds = geom.bounds # minx, miny, maxx, maxy
        avg_lat = (bounds[1] + bounds[3]) / 2.0
        import math
        lat_m = 111132.954 - 559.822 * math.cos(2 * math.radians(avg_lat))
        lng_m = 111412.84 * math.cos(math.radians(avg_lat))
        area_m2 = geom.area * lat_m * lng_m
        area_ha = area_m2 / 10000.0

        if area_ha < 100:
            return 10  # ~40m edge length, ~1.5 ha/hex (Ideal for small parcels)
        elif area_ha < 2500:
            return 9   # ~105m edge length, ~10 ha/hex (Standard agricultural grid)
        else:
            return 8   # ~460m edge length, ~70 ha/hex (Regional macro scale)

    def _get_h3_cells_from_polygon(self, geom: Polygon, res: int) -> List[str]:
        if not h3:
            raise ImportError("h3 library is not installed.")
        
        geojson_geom = mapping(geom)
        
        if IS_H3_V4:
            # H3 v4 API
            h3_polygon = h3.geo_to_h3shape(geojson_geom)
            cells = set(h3.polygon_to_cells(h3_polygon, res))
            
            # Also ensure all boundary vertex points have their cell included
            for coord in geom.exterior.coords:
                v_cell = h3.latlng_to_cell(coord[1], coord[0], res)
                cells.add(v_cell)
        else:
            # H3 v3 API
            cells = set(h3.polyfill(geojson_geom, res, geo_json_conformant=True))
            for coord in geom.exterior.coords:
                v_cell = h3.geo_to_h3(coord[1], coord[0], res)
                cells.add(v_cell)
            
        # If polygon is small and polyfill returned 0 cells, get cell at centroid
        if not cells:
            centroid = geom.centroid
            if IS_H3_V4:
                cell = h3.latlng_to_cell(centroid.y, centroid.x, res)
            else:
                cell = h3.geo_to_h3(centroid.y, centroid.x, res)
            cells = {cell}
            
        return list(cells)

    def _cell_to_polygon(self, cell: str) -> Polygon:
        if IS_H3_V4:
            # cell_to_boundary returns tuple of (lat, lng) pairs
            boundary = h3.cell_to_boundary(cell)
            # convert to (lng, lat) for GeoJSON/WKT standard
            coords = [(lng, lat) for lat, lng in boundary]
        else:
            # geo_json=True returns (lng, lat) pairs
            coords = h3.h3_to_geo_boundary(cell, geo_json=True)
            
        # Ensure closed polygon ring
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
            
        return Polygon(coords)

    def _cell_to_centroid(self, cell: str) -> Point:
        if IS_H3_V4:
            lat, lng = h3.cell_to_latlng(cell)
        else:
            lat, lng = h3.h3_to_geo(cell)
        return Point(lng, lat)

    def aggregate_raster_to_grid(
        self,
        aoi_wkt: str,
        fusion_tif_path: str,
        resolution: int = None
    ) -> List[Dict[str, Any]]:
        """
        Divides the AOI into H3 hexagonal cells, extracts zonal stats from the fusion GeoTIFF,
        and returns a list of grid cells with calculated damage scores.
        """
        aoi_geom = shapely.wkt.loads(aoi_wkt)
        res = resolution or self._get_optimal_resolution(aoi_geom)
        
        # 1. Get H3 cells covering AOI
        cells = self._get_h3_cells_from_polygon(aoi_geom, res)
        
        grid_results = []
        
        # 2. Open GeoTIFF and calculate zonal statistics for each cell
        with rasterio.open(fusion_tif_path) as src:
            for cell in cells:
                cell_poly = self._cell_to_polygon(cell)
                centroid = self._cell_to_centroid(cell)
                
                try:
                    # Mask raster with cell polygon
                    out_image, out_transform = mask(
                        src, 
                        [mapping(cell_poly)], 
                        crop=True, 
                        all_touched=True, 
                        nodata=np.nan
                    )
                    
                    # Band 1 is Damage Score (0.0 to 1.0)
                    scores = out_image[0]
                    valid_scores = scores[~np.isnan(scores)]
                    
                    if valid_scores.size > 0:
                        mean_score = float(np.mean(valid_scores))
                    else:
                        mean_score = 0.0
                        
                except Exception:
                    mean_score = 0.0
                
                # Classify score
                if mean_score < 0.20:
                    damage_class = "Yok"
                elif mean_score < 0.45:
                    damage_class = "Hafif"
                elif mean_score < 0.70:
                    damage_class = "Orta"
                else:
                    damage_class = "Ağır"
                    
                grid_results.append({
                    "h3_index": cell,
                    "geometry_wkt": cell_poly.wkt,
                    "damage_score": round(mean_score, 4),
                    "damage_class": damage_class,
                    "centroid_lat": centroid.y,
                    "centroid_lon": centroid.x,
                    "centroid_wkt": centroid.wkt
                })
                
        return grid_results
