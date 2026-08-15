# Proje Gelişim Raporu (PROGRESS.md)

## Tamamlanan Sprintler

### Sprint 1: Temel Altyapı ve Veritabanı Mimarisi
- Docker altyapısı (PostgreSQL/PostGIS, Redis, MinIO, FastAPI API, Celery Worker, Next.js).
- Clean Architecture katmanları (Domain, Application, Infrastructure, Presentation).
- Veritabanı modelleri ve Alembic migrasyon altyapısı.

### Sprint 2: SAR Pipeline ve Google Earth Engine (GEE)
- GEE entegrasyonu (GEESatelliteClient ve Sentinel-1 ARD ön işleme akışı).
- Celery task'ı ile SAR indirme ve işleme.
- Leaflet haritası üzerinde AOI çizimi ve 25.000 ha alan koruması.

### Sprint 3: Optik (MS) Pipeline ve Paralel Celery Chord
- Sentinel-2 harmonized koleksiyonu üzerinden bulut maskeleme ve B2-B11 bantlarının çekilmesi.
- Celery chord mimarisiyle SAR ve MS pipeline'larının asenkron ve paralel çalıştırılması.
- Durum takibi için sar_status ve ms_status alanları.

### Sprint 4: Meteoroloji Doğrulama (Weather Pipeline)
- Open-Meteo Archive API entegrasyonu (openmeteo_client.py).
- Olay tarihi öncesi yağış, rüzgar hızı ve anomali tespiti (WeatherVerificationService).
- Celery chord'una 3. paralel görev olarak run_weather_pipeline entegrasyonu.
- UI üzerinde weather_status göstergesi.

### Sprint 5: Füzyon Skorlama (Strategy Pattern)
- ScoringStrategy (Protocol) ve WeightedFusionStrategy ile ağırlıklı hasar skorlama formülü:
  - Formül: 0.35 SAR + 0.25 NDMI + 0.20 NDRE + 0.12 Yağış + 0.08 Toprak Nemi
- 4 Sınıflı hasar sınıflandırması (Yok <0.20, Hafif 0.20-0.45, Orta 0.45-0.70, Ağır >0.70).
- FusionService: rasterio ve numpy kullanarak SAR ve MS GeoTIFF matrislerini piksel düzeyinde birleştirip sonuç hasar GeoTIFF'ini oluşturma.
- Docker ortamında libexpat1, libgomp1 ve rasterio kurulumu.
- Kullanıcı arayüzünde opsiyonel formül ağırlık ayarlama paneli.

### Sprint 6: Uzamsal Birikim (H3 Grid & Hotspot Analizi)
- H3 Hexagonal Grid altyapısı (h3-py, Resolution 9) ve raster zonal istatistik servisi (`GridAggregationService`).
- Getis-Ord Local G* mekansal otokorelasyon ve afet odak noktası tespiti (`HotspotService`).
- `grid_cells` ve `hotspot_results` tabloları ve Alembic migrasyonu (`a8d29f123456`).
- Celery pipeline'ında otomatik aggregation ve status'un `done` olarak tamamlanması.
- REST API endpoint'leri: `GET /jobs/{id}/results/summary`, `GET /jobs/{id}/results/grid`, `GET /jobs/{id}/results/hotspots`.
- Frontend arayüzünde özet kartları ve grid hücreleri listeleme tablosu.

### Sprint 7: Dışa Aktarma ve Raporlama (Export & PDF Damage Report)
- `ExportService`: GeoJSON, Shapefile (.zip), GeoPackage (.gpkg), CSV ve GeoTIFF raster indirme motoru.
- `PdfReportService`: ReportLab ile A4 formatında onaylı, meteoroloji tablolu, renkli dinamik pasta grafikli ve ıslak imza alanlı resmi Hasar Tespit Raporu üretimi.
- REST API Endpoint'leri: `GET /jobs/{id}/export/pdf`, `geotiff`, `geojson`, `shapefile`, `geopackage`, `csv`.
- Frontend `ExportModal` bileşeni ve tek tıkla dosya indirme arayüzü.
- Geniş açılı (16:9) uydu altlıklı harita görseli ve PostGIS `WKBElement` -> `to_shape()` tam uyumu.

### Sprint 8: İleri Görselleştirme, Spektral Katmanlar, Swipe (Perde) & Zaman Serisi Analizi
- **30 Günlük Meteorolojik İklim Zaman Serisi API'si:**
  - `GET /api/v1/jobs/{id}/results/timeseries`: ERA5 arşiv ve tahmin verisi üzerinden afet öncesi 28 gün ve sonrası 2 gün olmak üzere günlük yağış, toprak nemi (0-7cm), sıcaklık ve rüzgar hızı.
- **Frontend 30 Günlük Yağış & Nem Grafiği (Recharts):**
  - `TimeSeriesChart.tsx`: Birikimli yağış sütunları (Bar), toprak nemi eğrisi (Line), ortalama sıcaklık çizgisi ve afet gününü gösteren kırmızı dikey referans çizgisi.
- **Çoklu Spektral Katman Yöneticisi & Şeffaflık Denetimi:**
  - Harita üzerinde anlık mod değiştirme:
    - 🎯 **Füzyon Hasar Skoru**
    - 💧 **ΔNDMI Nem Kaybı İndeksi**
    - 🌿 **ΔNDRE Klorofil & Doku Hasarı**
    - 📡 **SAR Radar Geri Saçılımı**
  - Opacity Slider (%20 - %100) ve Altlık Seçici (Esri Uydu, Carto Koyu, OpenStreetMap).
- **Harita Üzerinde Swipe (Dikey Perde) Karşılaştırma Aracı:**
  - Sol taraf: Doğal Optik Uydu Altlığı (Afet Öncesi)
  - Sağ taraf: Spektral H3 Hexagon Hasar Katmanı (Afet Sonrası)
  - Lazer ayırıcı hat (`⇄`) ve interaktif sürükleme mekanizması.
- **PDF Raporuna 2. Sayfa (5 Panelli Spektral Matris Paneli):**
  - Gerçek Esri World Imagery uydu altlığı ve raster projeksiyon dönüşümleri ile yüksek kaliteli EK-1 panelleri.
- **Sprint 8 Otomatik Test Paketi (`test_sprint8.py`):** Başarıyla tamamlandı.

### Sprint 9: Yetkilendirme (Auth), Rol Tabanlı Erişim (RBAC), Admin Yönetimi & Dashboard Deneyimi
- **S9-T1: JWT & Kimlik Doğrulama:**
  - `core/security.py` (Bcrypt şifreleme + `python-jose` HS256 JWT üretimi ve doğrulaması).
  - `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/me`.
  - Başlangıçta otomatik sistem hesapları tohumlama: `admin@damage.org`, `analyst@damage.org`, `viewer@damage.org`.
- **S9-T2 & S9-T3: get_current_user & RBAC Guard:**
  - `api/deps.py` üzerinden `get_current_user` ve `require_role([RoleEnum.ADMIN])` dependency'leri.
  - `AOI` ve `Job` kayıtları gerçek `current_user.id`'ye bağlandı, izinsiz isteklere `401 Unauthorized` / `403 Forbidden` yanıtı verildi.
- **S9-T4: Admin Kullanıcı Yönetimi (CRUD):**
  - `UserService` ve `POST/GET/PATCH/DELETE /api/v1/admin/users/` endpoint'leri.
  - Self-lockout koruması (Admin kullanıcısının kendi rolünü düşürmesi veya hesabını silmesi engellendi).
- **S9-T5: Celery Kuyruk & Sistem İzleme API'si:**
  - `GET /api/v1/admin/queue-stats` (Celery cluster `inspect()` ile online worker sayısı, aktif ve bekleyen görevler).
  - `GET /api/v1/admin/jobs` (Tüm kullanıcıların analiz işlerinin zenginleştirilmiş dökümü).
- **S9-T6: Frontend NextAuth Entegrasyonu:**
  - `[...nextauth]/route.ts` gerçek FastAPI `/auth/login` backend'ine bağlandı; kullanıcı rolü (`token.role`) ve `accessToken` oturuma aktarıldı.
- **S9-T7: Dashboard Navigasyonu & Analiz Geçmişi:**
  - `Sidebar.tsx` modern navigasyon bileşeni.
  - `/jobs` sayfası ile tüm geçmiş analizlerin filtrelenmesi, durumu ve tek tıkla haritaya yüklenmesi.
- **S9-T8: Admin Paneli UI:**
  - `/admin/users` (Kullanıcı ekleme, rol değiştirme, aktiflik açma/kapama, silme).
  - `/admin/jobs` (Canlı Celery kuyruk metrik kartları ve sistem genelindeki tüm işlerin izlenmesi).
- **S9-T9: Tema Deneyimi (Next-Themes):**
  - `theme-provider.tsx` ve `theme-toggle.tsx` ile koyu/açık tema geçişi.
- **S9-T10: Mimari Karar Kaydı (ADR):**
  - *Parsel çıktısı bilinçli olarak ertelendi — TKGM kurumsal sözleşme gerektiriyor, iş hedefi (sigorta/resmi rapor mu, iç izleme mi) netleşmeden yatırım yapılmadı.*
- **Sprint 9 Test Paketi (`test_sprint9.py`):** %100 başarıyla tamamlandı.

---

## Tüm Sprintler Tamamlandı 🚀
Platform, gereksinim belgesinde (req.md) belirtilen tüm analiz, radar/optik füzyon, uzamsal birikim, dışa aktarma, ileri görselleştirme, kimlik doğrulama, RBAC ve yönetim gereksinimlerini eksiksiz karşılamaktadır.
