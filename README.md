# 🌾 SAR + MS Tarımsal Hasar Analizi Platformu (AgriDamage Web)

> **Çoklu Sensör Uydu Füzyonu (Sentinel-1 SAR + Sentinel-2 Optik), ERA5 Meteorolojik Afet Doğrulaması, H3 Heksagonal Uzamsal Birikim ve Otomatik Hasar Tespit Platformu**

![Python](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-blue?logo=fastapi)
![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20React%2019-black?logo=next.js)
![Docker](https://img.shields.io/badge/Container-Docker%20Compose-2496ED?logo=docker)
![Celery](https://img.shields.io/badge/Async%20Queue-Celery%20%2B%20Redis-37814A?logo=celery)
![PostGIS](https://img.shields.io/badge/Spatial%20DB-PostgreSQL%20%2B%20PostGIS-336791?logo=postgresql)
![MinIO](https://img.shields.io/badge/Object%20Storage-MinIO%20S3-C72C48?logo=minio)

---

## 🎯 Projenin Amacı ve Bilimsel Metodoloji

Geleneksel tarımsal hasar tespiti süreçleri (yerinde eksper incelemesi) zaman alıcı, maliyetli ve geniş coğrafyalarda yetersiz kalmaktadır. Bu platform;
1. **Sentinel-1 SAR (Sentetik Açıklıklı Radar):** Bulut ve gece/gündüz koşullarından bağımsız olarak arazi pürüzlülüğü ve geometrik bitki yapısı hasarını (VV, VH, RVI),
2. **Sentinel-2 Çoklu Spektral (MS):** Yüksek çözünürlüklü vejetasyon sağlığı, su/nem stresi ($\Delta\text{NDMI}$) ve doku klorofil kaybını ($\Delta\text{NDRE}$),
3. **ERA5 & Open-Meteo:** Afet tarihindeki aşırı yağış, taşkın ve fırtına/şiddetli rüzgar anomalilerini,
4. **Strategy Pattern Ağırlıklı Piksel Füzyonu:** $0.35\,\text{SAR} + 0.25\,\Delta\text{NDMI} + 0.20\,\Delta\text{NDRE} + 0.12\,\text{Yağış} + 0.08\,\text{Toprak Nemi}$,
5. **Uber H3 Hexagonal Grid (Resolution 9):** Raster hasar matrislerini ~100m çözünürlüklü homojen altıgen hücrelere indirgeme,
6. **Getis-Ord Gi\* Mekansal İstatistik:** Afetin en yoğun vurduğu sıcak noktaları (Hotspot $p < 0.01$) ve sağlam kalan soğuk alanları (Coldspot)

matematiksel olarak birleştirerek saniyeler içerisinde resmi onaylı hasar raporları ve CBS çıktısı üretir.

---

## 🏗️ Sistem Mimarisi & Servis Envanteri

```
                               ┌────────────────────────────────────────┐
                               │           Next.js 16 Frontend          │
                               │   (Leaflet + Recharts + NextAuth)     │
                               └──────────────────┬─────────────────────┘
                                                  │ HTTP / REST
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │        FastAPI REST API Gateway        │
                               │     (Clean Architecture + RBAC)        │
                               └────────┬───────────────────┬───────────┘
                                        │                   │
                     ┌──────────────────┴────────┐          │
                     ▼                           ▼          ▼
           ┌───────────────────┐       ┌────────────────────────┐
           │ PostGIS (DB)      │       │ Redis (Broker & Cache) │
           │ - AOI & Parsel    │       └───────────┬────────────┘
           │ - H3 Grid Hücre   │                   │ Celery Chord Task
           │ - RBAC Kullanıcı  │                   ▼
           └───────────────────┘       ┌────────────────────────┐
                     ▲                 │ Celery Asenkron Worker │
                     │                 │ - SAR Pipeline (GEE)   │
                     │                 │ - MS Pipeline (GEE)    │
           ┌─────────┴─────────┐       │ - Weather (ERA5)       │
           │ MinIO S3 Storage  │       │ - Fusion + H3 + Hotspot│
           │ - GeoTIFF / GPKG  │       │ - ReportLab PDF Rapor  │
           │ - PDF Raporları   │       └────────────────────────┘
           └───────────────────┘
```

| Servis Adı | Teknoloji | Görevi & Port |
|---|---|---|
| `frontend` | Next.js 16, React 19, Tailwind CSS | Kullanıcı Harita Arayüzü, Analiz Geçmişi, Admin Paneli (`:3000`) |
| `api` | FastAPI, Pydantic, SQLAlchemy Async | REST API, Yetkilendirme, Servis İletişimi (`:8000`) |
| `worker` | Celery, Rasterio, Geopandas, H3 | GEE Uydu İndirme, Füzyon Skorlama, Mekansal İstatistik, PDF Motoru |
| `worker-beat`| Celery Beat | Periyodik temizlik ve arka plan görevleri |
| `postgres` | PostgreSQL 16 + PostGIS 3.4 | Mekansal parsel geometrileri ve H3 hücre depolama (`:5432`) |
| `redis` | Redis 7 Alpine | Celery asenkron görev kuyruğu ve önbellek (`:6379`) |
| `minio` | MinIO S3 Object Storage | Büyük GeoTIFF, Shapefile ve PDF dosya depolama (`:9000`, Konsol: `:9001`) |
| `pgadmin` | pgAdmin 4 | Veritabanı yönetim arayüzü (`:8081`) |

---

## ✨ Öne Çıkan Özellikler

- 🛰️ **Çoklu Spektral & Radar Katman Yöneticisi:** Harita üzerinde Füzyon Skoru, $\Delta\text{NDMI}$ Nem Kaybı, $\Delta\text{NDRE}$ Klorofil ve SAR Radar katmanları arasında anında geçiş ve şeffaflık ayarı.
- 🪟 **Swipe (Dikey Perde) Karşılaştırma Aracı:** Afet öncesi doğal optik uydu görüntüsü ile afet sonrası H3 hasar dağılımını interaktif perdeyle ikiye bölerek kıyaslama.
- 📈 **30 Günlük Meteorolojik İklim Zaman Serisi:** ERA5 ve Open-Meteo verileriyle birikimli yağış sütunları, 0-7cm toprak nemi eğrisi ve sıcaklık grafiği.
- 📄 **Resmi 2 Sayfalık Hasar Tespit Raporu (PDF):** ReportLab motoruyla üretilen, Esri uydu haritası, spektral matris panelleri, meteoroloji tablosu ve onay/ıslak imza alanları içeren A4 rapor.
- 💾 **6 Farklı CBS Formatında Dışa Aktarma:** PDF, GeoTIFF, GeoJSON, ESRI Shapefile (.zip), OGC GeoPackage (.gpkg) ve Excel uyumlu CSV.
- 🔐 **Rol Tabanlı Erişim Denetimi (RBAC):** Admin (Tam yetki & Celery canlı kuyruk/kullanıcı yönetimi), Analist (Analiz başlatma ve dışa aktarma), İzleyici (Yalnızca geçmiş analizleri görüntüleme).
- 🌓 **Dinamik Açık / Koyu Tema Desteği:** `next-themes` ile tek tıkla gece/gündüz modu.

---

## 🚀 Hızlı Başlangıç (Kurulum)

### 1. Gereksinimler
- [Docker](https://www.docker.com/) ve [Docker Compose](https://docs.docker.com/compose/) kurulu olmalıdır.

### 2. Projeyi Klonlayın ve Ayağa Kaldırın
```bash
git clone https://github.com/HasanBasriTaskin/Agricultural-Area-Damage-Analysis.git
cd Agricultural-Area-Damage-Analysis

# Tüm servisleri derleyip arka planda başlatın
docker compose up --build -d
```

Servisler hazır olduğunda tarayıcınızdan erişebilirsiniz:
- 🌐 **Web Uygulaması:** [http://localhost:3000](http://localhost:3000)
- 📚 **Swagger REST API Dokümantasyonu:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Sistem Sağlığı (Healthcheck):** [http://localhost:8000/api/v1/health/](http://localhost:8000/api/v1/health/)
- 📦 **MinIO S3 Konsolu:** [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)
- 🐘 **pgAdmin Veritabanı:** [http://localhost:8081](http://localhost:8081)

---

## 👤 Önceden Tanımlı Test Hesapları (RBAC)

Sistem başlangıçta aşağıdaki test hesaplarını otomatik olarak tohumlar:

| Rol | E-posta | Şifre | Yetkiler |
|---|---|---|---|
| 🔴 **Admin** | `admin@damage.org` | `Admin123!` | Kullanıcı CRUD, Celery canlı cluster izleme, tüm işleri yönetme |
| 🔵 **Analist** | `analyst@damage.org` | `Analyst123!` | Yeni analiz başlatma, haritada çizim yapma, rapor ve CBS indirme |
| ⚪ **İzleyici** | `viewer@damage.org` | `Viewer123!` | Yalnızca analiz sonuçlarını ve raporları görüntüleme |

*Not: Giriş yapılmadığında sistem varsayılan olarak Analist yetkileriyle misafir deneyimi sunar.*

---

## 🧪 Test Paketini Çalıştırma

Tüm platform servislerini, asenkron Celery görevlerini, veri füzyonunu, PDF üretimini ve RBAC yetkilendirmelerini tek komutla doğrulamak için:

```bash
# Uçtan Uca (E2E) Kapsamlı Entegrasyon Testi (Sprint 10)
docker compose exec -e PYTHONPATH=. api python tests/test_e2e_full.py

# Sprint 9 RBAC & Yetkilendirme Testi
docker compose exec -e PYTHONPATH=. api python tests/test_sprint9.py

# Pytest Birim Testleri
docker compose exec -e PYTHONPATH=. api pytest tests/
```

---

## 📂 Proje Dizin Yapısı

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/        # auth, admin_users, admin_jobs, aoi, job, results, export, health
│   │   │   ├── schemas.py     # Pydantic DTO modelleri
│   │   │   └── deps.py        # RBAC get_current_user dependency'leri
│   │   ├── application/       # FusionService, HotspotService, ExportService, PdfReportService
│   │   ├── core/              # config.py, security.py (Bcrypt, JWT)
│   │   ├── domain/            # Entities, Value Objects, Scoring Protocols
│   │   └── infrastructure/    # GEE client, OpenMeteo client, Celery tasks, PostGIS DB
│   └── tests/                 # test_e2e_full.py, test_sprint9.py, test_sprint8.py
├── frontend/
│   ├── src/
│   │   ├── app/               # /, /jobs, /login, /admin/users, /admin/jobs
│   │   └── components/        # Map (Leaflet), Sidebar, TimeSeriesChart, ExportModal, ThemeToggle
├── docker-compose.yml         # 8 microservice orchestrator
└── req.md                     # Teknik şartname ve mimari kararlar
```

---

## 📄 Lisans ve Telif Hakkı
Bu proje Hasan Basri Taşkın tarafından geliştirilmiştir. Tüm hakları saklıdır.
