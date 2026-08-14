import os
import io
import uuid
import zipfile
import json
from unittest.mock import MagicMock
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
import shapely.wkt

from app.application.services.export_service import ExportService
from app.application.services.pdf_report_service import PdfReportService

class MockGridCell:
    def __init__(self, h3_index, damage_score, damage_class, wkt):
        self.id = uuid.uuid4()
        self.h3_index = h3_index
        self.damage_score = damage_score
        self.damage_class = damage_class
        self.geometry = WKTElement(wkt, srid=4326)

class MockHotspot:
    def __init__(self, h3_index, intensity, confidence, classification, wkt):
        self.id = uuid.uuid4()
        self.h3_index = h3_index
        self.intensity = intensity
        self.confidence = confidence
        self.classification = classification
        self.geometry = WKTElement(wkt, srid=4326)

def test_sprint7_exports():
    # 1. Prepare synthetic mock data
    cells = [
        MockGridCell("8a2d35756267fff", 0.75, "Ağır", "POLYGON((30.91 40.69, 30.92 40.69, 30.92 40.70, 30.91 40.70, 30.91 40.69))"),
        MockGridCell("8a2d3575624ffff", 0.52, "Orta", "POLYGON((30.92 40.69, 30.93 40.69, 30.93 40.70, 30.92 40.70, 30.92 40.69))"),
        MockGridCell("8a2d35756257fff", 0.15, "Yok", "POLYGON((30.93 40.69, 30.94 40.69, 30.94 40.70, 30.93 40.70, 30.93 40.69))")
    ]

    hotspots = [
        MockHotspot("8a2d35756267fff", 3.85, 0.001, "Hotspot (%99 Güven)", "POINT(30.915 40.695)"),
        MockHotspot("8a2d3575624ffff", 1.98, 0.045, "Hotspot (%95 Güven)", "POINT(30.925 40.695)")
    ]

    mock_minio = MagicMock()
    mock_minio.upload_bytes.return_value = "mock_key"
    mock_minio.upload_file.return_value = "mock_key"

    export_service = ExportService(minio_client=mock_minio)

    # 2. Test GeoJSON
    geojson = export_service.generate_geojson(cells, hotspots)
    assert geojson["type"] == "FeatureCollection"
    assert geojson["count"] == 3
    assert len(geojson["features"]) == 3
    assert geojson["features"][0]["properties"]["damage_class"] == "Ağır"
    assert geojson["features"][0]["properties"]["hotspot_class"] == "Hotspot (%99 Güven)"
    print("✓ GeoJSON Export: Verified successfully")

    # 3. Test CSV
    csv_text = export_service.generate_csv(cells, hotspots)
    assert "H3_Indeks" in csv_text
    assert "Hasar_Skoru" in csv_text
    assert "8a2d35756267fff" in csv_text
    assert "Ağır" in csv_text
    print("✓ CSV Export: Verified successfully")

    # 4. Test Shapefile Zip
    zip_bytes = export_service.generate_shapefile_zip(cells, hotspots)
    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        assert any(n.endswith(".shp") for n in namelist)
        assert any(n.endswith(".shx") for n in namelist)
        assert any(n.endswith(".dbf") for n in namelist)
        assert any(n.endswith(".prj") for n in namelist)
    print(f"✓ Shapefile Zip Export: Verified successfully ({len(zip_bytes)} bytes)")

    # 5. Test GeoPackage
    gpkg_bytes = export_service.generate_geopackage(cells, hotspots)
    assert len(gpkg_bytes) > 0
    assert gpkg_bytes.startswith(b"SQLite format 3")
    print(f"✓ GeoPackage Export: Verified successfully ({len(gpkg_bytes)} bytes)")

    # 6. Test PDF Damage Report
    pdf_service = PdfReportService(minio_client=mock_minio)
    summary_data = {
        "total_cells": 3,
        "mean_damage_score": 0.4733,
        "distribution": {"Yok": 1, "Hafif": 0, "Orta": 1, "Ağır": 1},
        "hotspot_cells_count": 2,
        "coldspot_cells_count": 0,
        "weather": {
            "precipitation_mm": 45.2,
            "soil_moisture_m3_m3": 0.42,
            "is_anomaly": True
        }
    }
    pdf_bytes = pdf_service.generate_damage_report(
        job_id=uuid.uuid4(),
        aoi_name="Deneme Mısır Tarlası",
        aoi_area_ha=24.5,
        event_date="14.07.2026",
        summary_data=summary_data,
        weather_data=summary_data["weather"],
        weights={"sar": 0.35, "ndmi": 0.25, "ndre": 0.20, "precip": 0.12, "sm": 0.08}
    )
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")
    print(f"✓ PDF Damage Report: Generated successfully ({len(pdf_bytes)} bytes)")

    print("\n🎉 ALL SPRINT 7 EXPORT & REPORTING TESTS PASSED!")

if __name__ == "__main__":
    test_sprint7_exports()
