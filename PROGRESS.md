# Proje İlerleme Durumu

> **MİMARİ KARAR (MapLibre vs Leaflet):** B Seçeneği (Leaflet'te kalmak) seçildi. Çünkü MapLibre GL v6 ile Next.js 15+ Turbopack arasında WebGL render sorunları yaşanıyor. Projemizin raster katman ihtiyacı `leaflet-geotiff` veya `georaster-layer-for-leaflet` ile karşılanabilir, vektör-tile şimdilik şart değil.

## SPRINT 0 — KALAN İŞLER
- [x] S0-T1: docker-compose.yml'ye worker-beat servisini ekle
- [x] S0-T2: Eksik frontend paketlerini kur
- [x] S0-T3: CI/CD iskeletini oluştur
- [x] S0-T4: Docker Compose'u gerçekten ayağa kaldır
- [x] S0-T5: .env.example dosyalarını oluştur

## SPRINT 1 — ATOMİK TASK'LARA BÖLÜNDÜ
- [x] S1-T1: SQLAlchemy modelleri
- [x] S1-T2: Alembic kurulumu + ilk migration
- [x] S1-T3: Domain Entity'leri (framework'ten bağımsız)
- [x] S1-T4: Repository arayüzleri
- [x] S1-T5: Repository implementasyonları
- [x] S1-T6: AOI use case'leri
- [x] S1-T7: Pydantic şemaları
- [x] S1-T8: AOI router
- [x] S1-T9: Dependency Injection wiring
- [x] S1-T10: Frontend AOI ekranı
- [x] S1-T11: Uçtan uca entegrasyon testi

## SPRINT 2 � SAR PIPELINE (Celery + GEE)
- [x] S2-T1: AnalysisJob domain entity + WeightConfig value object
- [x] S2-T2: IJobRepository aray�z�
- [x] S2-T3: JobRepository implementasyonu
- [x] S2-T4: Job API
- [x] S2-T5: Satellite data client aray�z� + GEE implementasyonu
- [x] S2-T6: Celery altyapi kurulumu
- [x] S2-T7: SAR pipeline servisi
- [x] S2-T8: Celery task + job tetikleme
- [x] S2-T9: Job durumu izleme endpoint'i
- [x] S2-T10: Frontend � job tetikleme + durum g�sterimi (MVP)

> **MIMARI KARAR (DPSVI vs DPSVIm):** DPSVI yerine DPSVIm kullanildi � orijinal DPSVI'nin VVmax parametresi manuel/ampirik tuning gerektirdigi i�in otomatik pipeline'a uygun degildi.
