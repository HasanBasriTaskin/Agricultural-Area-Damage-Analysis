import pytest
from datetime import datetime
from app.application.pipelines.sar_pipeline import SarPipelineService
from app.infrastructure.external.fake_satellite_client import FakeSatelliteClient

def test_sar_pipeline_with_fake_client():
    fake_client = FakeSatelliteClient()
    pipeline = SarPipelineService(fake_client)
    
    # Fake WKT polygon
    aoi_wkt = "POLYGON((30 10,40 40,20 40,10 20,30 10))"
    event_date = datetime(2021, 8, 11)
    
    # Run pipeline
    minio_key = pipeline.run_pipeline(aoi_wkt, event_date)
    
    # Assertions
    assert minio_key.startswith("fake_minio_bucket/sar_result_")
    assert minio_key.endswith(".tif")
