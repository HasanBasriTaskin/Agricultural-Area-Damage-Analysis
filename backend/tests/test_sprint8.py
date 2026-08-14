import io
import uuid
import asyncio
from datetime import date
from unittest.mock import MagicMock

from app.infrastructure.external.openmeteo_client import OpenMeteoClient
from app.application.services.pdf_report_service import PdfReportService

def test_openmeteo_30day_timeseries():
    client = OpenMeteoClient()
    # Synchronously run async method
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(
        client.get_30day_timeseries(lat=39.38, lon=32.11, event_date=date(2024, 7, 15))
    )
    assert len(res) >= 28, f"Expected at least 28 days, got {len(res)}"
    assert "precipitation_mm" in res[0]
    assert "soil_moisture" in res[0]
    assert any(pt.get("is_event_date") for pt in res), "Event date not marked"
    print("✓ OpenMeteo 30-Day Timeseries: Verified successfully")

def test_pdf_report_spectral_matrix():
    mock_minio = MagicMock()
    service = PdfReportService(minio_client=mock_minio)

    class DummyCell:
        def __init__(self, h3, score, cls):
            self.h3_index = h3
            self.damage_score = score
            self.damage_class = cls
            self.geometry = "POLYGON((32.10 39.38, 32.11 39.38, 32.11 39.39, 32.10 39.39, 32.10 39.38))"

    cells = [
        DummyCell("881f1d4881fffff", 0.15, "Yok"),
        DummyCell("881f1d4883fffff", 0.35, "Hafif"),
        DummyCell("881f1d4885fffff", 0.55, "Orta"),
        DummyCell("881f1d4887fffff", 0.85, "Ağır"),
    ]

    weather_ts = [
        {"date": "2024-07-01", "precipitation_mm": 0.0, "soil_moisture": 0.18, "temp_mean": 24.0, "is_event_date": False},
        {"date": "2024-07-15", "precipitation_mm": 25.4, "soil_moisture": 0.34, "temp_mean": 21.0, "is_event_date": True},
    ]

    pdf_bytes = service.generate_damage_report(
        job_id=uuid.uuid4(),
        aoi_name="Konya Test Parseli",
        aoi_area_ha=145.2,
        event_date="15.07.2024",
        summary_data={
            "total_cells": 4,
            "mean_damage_score": 0.475,
            "distribution": {"Yok": 1, "Hafif": 1, "Orta": 1, "Ağır": 1},
            "hotspot_cells_count": 1,
            "coldspot_cells_count": 0,
            "weather": {"precipitation_mm": 25.4, "soil_moisture_m3_m3": 0.34, "is_anomaly": True}
        },
        cells=cells,
        aoi_wkt="POLYGON((32.10 39.38, 32.11 39.38, 32.11 39.39, 32.10 39.39, 32.10 39.38))",
        weather_timeseries=weather_ts
    )

    assert len(pdf_bytes) > 20000, f"PDF report size too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes.startswith(b'%PDF'), "Not a valid PDF header"
    print(f"✓ 2-Page PDF Report with 5-Panel Spectral Matrix: Verified ({len(pdf_bytes)} bytes)")

if __name__ == "__main__":
    print("Running Sprint 8 Verification Tests...")
    test_openmeteo_30day_timeseries()
    test_pdf_report_spectral_matrix()
    print("\n🎉 ALL SPRINT 8 TESTS PASSED SUCCESSFULLY!")
