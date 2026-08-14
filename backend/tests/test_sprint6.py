import numpy as np
import rasterio
from rasterio.transform import from_origin
import shapely.geometry
from app.application.services.grid_aggregation_service import GridAggregationService
from app.application.services.hotspot_service import HotspotService

def test_grid_aggregation_and_hotspot():
    # 1. Create a synthetic GeoTIFF
    # Bounding box: 30.0 to 30.05 E, 39.0 to 39.05 N
    # 100x100 pixels
    transform = from_origin(30.0, 39.05, 0.0005, 0.0005)
    
    # Create fake damage scores with high clustering in one corner (hotspot)
    data = np.full((100, 100), 0.1, dtype=np.float32)
    # High damage cluster (hotspot)
    data[10:30, 10:30] = 0.85
    
    tif_path = "/tmp/test_synthetic_damage.tif"
    with rasterio.open(
        tif_path,
        'w',
        driver='GTiff',
        height=100,
        width=100,
        count=1,
        dtype=np.float32,
        crs='EPSG:4326',
        transform=transform,
    ) as dst:
        dst.write(data, 1)
        
    # 2. Define AOI covering this region
    aoi_wkt = "POLYGON((30.0 39.0, 30.05 39.0, 30.05 39.05, 30.0 39.05, 30.0 39.0))"
    
    # 3. Test Grid Aggregation Service
    grid_service = GridAggregationService(default_resolution=9)
    grid_cells = grid_service.aggregate_raster_to_grid(aoi_wkt, tif_path)
    
    print(f"Total grid cells generated: {len(grid_cells)}")
    assert len(grid_cells) > 0, "Grid cells should not be empty"
    
    high_damage_cells = [c for c in grid_cells if c["damage_score"] > 0.5]
    print(f"High damage cells count: {len(high_damage_cells)}")
    assert len(high_damage_cells) > 0, "Should have detected high damage cells in the clustered region"
    
    # 4. Test Hotspot Service (Getis-Ord G*)
    hotspot_service = HotspotService()
    hotspots = hotspot_service.calculate_getis_ord_g_star(grid_cells)
    
    print(f"Hotspot results count: {len(hotspots)}")
    assert len(hotspots) == len(grid_cells), "Every grid cell should have a hotspot result"
    
    detected_hotspots = [h for h in hotspots if h["is_hotspot"]]
    print(f"Detected statistically significant hotspots: {len(detected_hotspots)}")
    assert len(detected_hotspots) > 0, "Should have detected statistically significant hotspots in the high damage cluster"
    
    for h in detected_hotspots[:3]:
        print(f"  Hotspot {h['h3_index']}: z={h['intensity']}, p={h['confidence']}, class={h['classification']}")
        
    print("All Sprint 6 Unit Tests Passed Successfully!")

if __name__ == "__main__":
    test_grid_aggregation_and_hotspot()
