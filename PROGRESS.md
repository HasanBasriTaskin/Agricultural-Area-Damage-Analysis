# Proje Gelisim Raporu (PROGRESS.md)

## Tamamlanan Sprintler

### Sprint 1: Temel Altyapi ve Veritabani Mimarisi
- Docker altyapisi (PostgreSQL/PostGIS, Redis, MinIO, FastAPI API, Celery Worker, Next.js).
- Clean Architecture katmanlari (Domain, Application, Infrastructure, Presentation).
- Veritabani modelleri ve Alembic migrasyon altyapisi.

### Sprint 2: SAR Pipeline ve Google Earth Engine (GEE)
- GEE entegrasyonu (GEESatelliteClient ve Sentinel-1 ARD on isleme akisi).
- Celery task'i ile SAR indirme ve isleme.
- Leaflet haritasi uzerinde AOI cizimi ve 25.000 ha alan korumasi.

### Sprint 3: Optik (MS) Pipeline ve Paralel Celery Chord
- Sentinel-2 harmonized koleksiyonu uzerinden bulut maskeleme ve B2-B11 bantlarinin cekilmesi.
- Celery chord mimarisiyle SAR ve MS pipeline'larinin asenkron ve paralel calistirilmasi.
- Durum takibi icin sar_status ve ms_status alanlari.

### Sprint 4: Meteoroloji Dogrulama (Weather Pipeline)
- Open-Meteo Archive API entegrasyonu (openmeteo_client.py).
- Olay tarihi oncesi yagis, ruzgar hizi ve anomali tespiti (WeatherVerificationService).
- Celery chord'una 3. paralel gorev olarak run_weather_pipeline entegrasyonu.
- UI uzerinde weather_status gostergesi.

### Sprint 5: Fuzyon Skorlama (Strategy Pattern)
- ScoringStrategy (Protocol) ve WeightedFusionStrategy ile agirlikli hasar skorlama formulu:
  - Formul: 0.35 SAR + 0.25 NDMI + 0.20 NDRE + 0.12 Yagis + 0.08 Toprak Nemi
- 4 Sinifli hasar siniflandirmasi (Yok <0.20, Hafif 0.20-0.45, Orta 0.45-0.70, Agir >0.70).
- FusionService: rasterio ve numpy kullanarak SAR ve MS GeoTIFF matrislerini piksel duzeyinde birlestirip sonuc hasar GeoTIFF'ini olusturma.
- Docker ortaminda libexpat1, libgomp1 ve rasterio kurulumu.
- Kullanici arayuzunde opsiyonel formul agirlik ayarlama paneli.

### Sprint 6: Uzamsal Birikim (H3 Grid & Hotspot Analizi)
- H3 Hexagonal Grid altyapisi (h3-py, Resolution 9) ve raster zonal istatistik servisi (`GridAggregationService`).
- Getis-Ord Local G* mekansal otokorelasyon ve afet odak noktasi tespiti (`HotspotService`).
- `grid_cells` ve `hotspot_results` tablolari ve Alembic migrasyonu (`a8d29f123456`).
- Celery pipeline'inda otomatik aggregation ve status'un `done` olarak tamamlanmasi.
- REST API endpoint'leri: `GET /jobs/{id}/results/summary`, `GET /jobs/{id}/results/grid`, `GET /jobs/{id}/results/hotspots`.
- Frontend arayuzunde ozet kartlari ve grid hucreleri listeleme tablosu (MVP).

### Sprint 7: Dışa Aktarma ve Raporlama (Export & PDF Damage Report)
- `ExportService`: GeoJSON, Shapefile (.zip), GeoPackage (.gpkg), CSV ve GeoTIFF raster indirme motoru.
- `PdfReportService`: ReportLab ile A4 formatında onaylı, meteoroloji tablolu, renkli dinamik pasta grafikli ve ıslak imza alanlı resmi Hasar Tespit Raporu üretimi.
- REST API Endpoint'leri:
  - `GET /jobs/{id}/export/pdf`
  - `GET /jobs/{id}/export/geotiff?layer=fusion|sar|ms`
  - `GET /jobs/{id}/export/geojson`
  - `GET /jobs/{id}/export/shapefile`
  - `GET /jobs/{id}/export/geopackage`
  - `GET /jobs/{id}/export/csv`
- Frontend `ExportModal` bileşeni ve tek tıkla dosya indirme arayüzü.
- Otomatik unit ve entegrasyon testleri (`test_sprint7.py`) ile tüm formatların byte doğrulaması.

---

## Sıradaki Adım
- Sprint 8: İleri Görselleştirme & Harita Katmanları (Sentinel-2 RGB Katmanı, NDMI Nem Haritası, SAR Radar Katmanı, Afet Öncesi/Sonrası Swipe/Perde Karşılaştırma Aracı).
