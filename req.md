
# SAR + MS Tarımsal Hasar Analizi — Web Platformu Teknik Planı
**Stack:** Python (FastAPI) Backend · Next.js Frontend · Docker Compose

---

## 1. Mimari Yaklaşım (Özet)

Orijinal proje zaten Python tabanlı olduğu için (GEE Python SDK, rasterio, geopandas, pysal, xarray), backend'i de Python üzerinde kurmak dil/kütüphane uyumsuzluğu riskini tamamen ortadan kaldırıyor. Tasarımın temel prensipleri:

- **Tek dil, katmanlı mimari:** FastAPI üzerine kurulu, Clean Architecture ilkeleriyle ayrılmış Entity / İş (Application) / Data (Infrastructure) / API (Presentation) katmanları.
- **Asenkron iş kuyruğu zorunlu:** SAR/MS indirme + GEE işleme + hotspot analizi dakikalar sürebilir. HTTP isteği içinde senkron çalıştırmak yerine, iş **Celery worker**'a devredilir; kullanıcı job durumu takibi yapar.
- **Konteynerleştirme:** Her bileşen (API, worker, veritabanı, cache/broker, nesne depolama, frontend) ayrı bir Docker servisi; `docker-compose.yml` ile tek komutla ayağa kalkar.
- **Coğrafi veri için doğru araçlar:** PostGIS (vektör/parsel sorguları) + MinIO/S3 (GeoTIFF, Shapefile, GeoPackage gibi büyük dosyalar için object storage — bunları veritabanına gömmeyiz).

---

## 2. Docker Servis Envanteri

| Servis | Amaç | Not |
|---|---|---|
| `api` | FastAPI uygulaması (REST + WebSocket) | Uvicorn/Gunicorn, otomatik OpenAPI docs |
| `worker` | Celery worker(ları) | GEE/SAR/MS/füzyon/hotspot işleri burada çalışır; CPU-yoğun olduğu için ölçeklenebilir (`--scale worker=3`) |
| `worker-beat` | Celery Beat (zamanlanmış görevler) | Örn. periyodik meteoroloji eşik kontrolü |
| `redis` | Celery broker + cache + job durumu | |
| `postgres` (PostGIS imajı) | İlişkisel + mekansal veri | `postgis/postgis` imajı |
| `minio` | S3 uyumlu nesne depolama | GeoTIFF/Shapefile/GeoPackage çıktıları |
| `frontend` | Next.js uygulaması | Prod'da `next build && next start`, dev'de hot-reload |
| `nginx` / `traefik` (ops.) | Reverse proxy + TLS | Prod ortamında önerilir |
| `flower` (ops.) | Celery izleme paneli | Geliştirme/ops için faydalı |

---

## 3. Fonksiyonel Gereksinimler (FR)

**Kimlik & Yetkilendirme**
- FR-1: Kullanıcı kayıt/giriş (JWT tabanlı), rol bazlı yetkilendirme (admin / analist / görüntüleyici).
- FR-2: Next-Auth üzerinden FastAPI'ye OAuth2 password/JWT akışı ile bağlanma.

**Proje / AOI Yönetimi**
- FR-3: Kullanıcı bir çalışma alanı (AOI — şehir sınırı veya özel polygon) tanımlayabilir (GeoJSON çizerek ya da yükleyerek).
- FR-4: Kentsel/tarım maskesi otomatik hesaplanır ve kullanıcıya önizleme olarak gösterilir (Faz 0).

**Analiz Tetikleme & İzleme**
- FR-5: Kullanıcı bir olay tarihi + AOI seçerek analiz job'ı başlatabilir.
- FR-6: Job durumu gerçek zamanlı izlenebilir (WebSocket veya polling): `queued → downloading → processing_sar → processing_ms → verifying_weather → fusing → aggregating → done/failed`.
- FR-7: Ağırlık katsayıları (SAR %35, ΔNDMI %25 vb.) analiz öncesi kullanıcı tarafından ayarlanabilir (varsayılan değerlerle).

**Sonuç Görüntüleme**
- FR-8: Hasar skoru haritası interaktif harita üzerinde katman olarak gösterilir (raster overlay + parsel/grid vektör katmanları).
- FR-9: Parsel/mahalle bazlı hasar tablosu, filtrelenebilir/sıralanabilir.
- FR-10: Hotspot (sıcak nokta) haritası ayrı bir katman olarak gösterilir.
- FR-11: Zaman serisi grafiği (NDMI/NBMI değişimi) ve yağış-hasar korelasyon grafiği.

**Dışa Aktarma**
- FR-12: GeoTIFF, GeoJSON, Shapefile, GeoPackage, CSV çıktıları indirilebilir.

**Yönetim**
- FR-13: Admin panel — kullanıcı yönetimi, job geçmişi, sistem sağlığı (Celery kuyruk durumu).
- FR-14: Açık/koyu tema geçişi, kullanıcı tercihi olarak saklanır.

---

## 4. Fonksiyonel Olmayan Gereksinimler (NFR)

| Kategori | Gereksinim |
|---|---|
| **Performans** | Ağır analiz işleri API isteğini bloklamaz (Celery); API yanıt süresi < 300ms (CRUD işlemleri için) |
| **Ölçeklenebilirlik** | Worker sayısı yatay ölçeklenebilir (`docker-compose scale` / K8s HPA); job kuyruğu birikimi izlenir |
| **Güvenilirlik** | Job'lar idempotent tasarlanır; hata durumunda retry (exponential backoff, Celery `autoretry_for`) |
| **Güvenlik** | JWT + refresh token; GEE servis hesabı kimlik bilgileri `.env`/secret manager'da, koda gömülmez; input validasyonu Pydantic ile zorunlu; rate limiting (`slowapi`) |
| **Gözlemlenebilirlik** | Yapılandırılmış loglama (`structlog`), health-check endpoint'leri, opsiyonel Prometheus + Grafana |
| **Test edilebilirlik** | Servis katmanı arayüzler (Protocol) üzerinden mock'lanabilir; `pytest` + `httpx` + `testcontainers` |
| **Taşınabilirlik** | Tüm bağımlılıklar container içinde; yerel geliştirme = prod parity (aynı `docker-compose.yml`, farklı `.env`) |
| **Veri saklama** | Ham uydu verisi cache'lenir ama süresiz saklanmaz (TTL/temizlik job'ı); üretilmiş sonuçlar MinIO'da versiyonlanır |
| **Erişilebilirlik/i18n** | UI bileşenleri WCAG AA hedefler; ileride çoklu dil için `next-intl` eklenebilir |

---

## 5. Backend Mimarisi (Python / FastAPI) — Katmanlı + SOLID

### 5.1 Klasör Yapısı

```
backend/
├── app/
│   ├── api/                      # Presentation / API katmanı
│   │   ├── v1/
│   │   │   ├── routers/          # aoi.py, jobs.py, results.py, auth.py, admin.py
│   │   │   ├── schemas/          # Pydantic request/response DTO'ları
│   │   │   └── deps.py           # FastAPI Depends() - DI wiring
│   │   └── websockets/           # job durumu real-time
│   ├── domain/                   # Entity katmanı (framework'ten bağımsız)
│   │   ├── entities/             # AOI, AnalysisJob, DamageResult, HotspotResult...
│   │   ├── value_objects/        # DamageScore, WeightConfig, GeoBoundingBox...
│   │   └── interfaces/           # Protocol/ABC — repository & servis arayüzleri
│   ├── application/               # İş (Business) katmanı — use case'ler
│   │   ├── services/              # aoi_service.py, fusion_service.py, hotspot_service.py
│   │   ├── pipelines/             # sar_pipeline.py, ms_pipeline.py, weather_pipeline.py
│   │   └── use_cases/             # StartAnalysisJob, GetJobStatus, ExportResult...
│   ├── infrastructure/            # Data / Dış servis katmanı
│   │   ├── db/                    # SQLAlchemy models, session, Alembic migrations
│   │   ├── repositories/          # AoiRepository, JobRepository (interface impl.)
│   │   ├── external/               # gee_client.py, openmeteo_client.py, era5_client.py
│   │   ├── storage/                # MinIO/S3 client wrapper
│   │   └── tasks/                  # Celery task tanımları (application servislerini çağırır)
│   ├── core/                       # config, security, logging, exceptions
│   └── main.py                     # FastAPI app factory
├── tests/
├── Dockerfile
├── Dockerfile.worker
└── pyproject.toml
```

### 5.2 Katmanların Sorumlulukları

- **Domain (Entity):** Saf Python sınıfları/`dataclass`/Pydantic modelleri. Hiçbir framework veya veritabanı bağımlılığı yok. `AnalysisJob`, `DamageResult`, `AOI`, `WeightConfig` gibi iş nesneleri burada.
- **Application (İş katmanı):** Use case'ler ve pipeline orkestrasyonu (`StartAnalysisJobUseCase`, `FusionService`). Sadece **domain arayüzlerine** bağımlı — hangi veritabanının veya GEE istemcisinin kullanıldığını bilmez (Dependency Inversion).
- **Infrastructure (Data + Dış servisler):** SQLAlchemy repository implementasyonları, GEE/Open-Meteo/ERA5 istemcileri, MinIO storage adapter'ı. Domain'deki arayüzleri (`IAoiRepository`, `IJobRepository`, `ISatelliteDataClient`) **implemente eder**.
- **API (Presentation):** FastAPI router'ları sadece HTTP/WebSocket ↔ use case çevirisi yapar; iş mantığı burada olmaz. Pydantic şemaları request/response validasyonu sağlar.
- **Workers:** Celery task'ları application katmanındaki use case'leri çağırır; kendileri iş mantığı içermez, sadece orkestrasyon + retry/hata yönetimi.

### 5.3 Python'da SOLID Uygulaması

- **SRP:** Her servis tek bir sorumluluk taşır (`SarPipelineService` sadece SAR işler, `FusionService` sadece skor birleştirir).
- **OCP:** Ağırlıklı füzyon formülü bir `Strategy` (`ScoringStrategy` Protocol) olarak tanımlanır — yeni bir skorlama yöntemi eklemek mevcut kodu değiştirmeden yeni bir strateji sınıfı eklemekle olur.
- **LSP:** Tüm repository implementasyonları aynı `Protocol` sözleşmesine (`IAoiRepository`) uyar, birbirinin yerine geçebilir (örn. test'te in-memory repo, prod'da Postgres repo).
- **ISP:** Büyük "God interface" yerine küçük, odaklı arayüzler (`IJobStatusReader`, `IJobWriter` ayrı ayrı).
- **DIP:** Application katmanı somut sınıflara değil `Protocol`/`ABC` arayüzlerine bağımlı; FastAPI'nin `Depends()` sistemi (veya `dependency-injector` kütüphanesi) somut implementasyonu runtime'da enjekte eder.

### 5.4 Kullanılacak Tasarım Desenleri

- **Repository + Unit of Work** — veri erişimini soyutlamak için.
- **Strategy** — skorlama ağırlıkları / eşik konfigürasyonları için.
- **Result/Either pattern** — hata yönetimini exception yerine tip güvenli sonuç nesneleriyle yapmak (opsiyonel, `returns` kütüphanesi ile).
- **CQRS-lite** — okuma (job durumu, sonuç listeleme) ve yazma (job başlatma) use case'lerini ayrı tutmak.

---

## 6. Asenkron İş Orkestrasyonu

```
Kullanıcı → POST /jobs → API job kaydı oluşturur (status=queued) → Celery task kuyruğa girer
                                                                        │
                                                                        ▼
                                                        Worker: SAR + MS pipeline'ları paralel çalıştırır (Celery group/chord)
                                                                        │
                                                                        ▼
                                                        Meteoroloji doğrulama → Füzyon → Uzamsal birikim
                                                                        │
                                                                        ▼
                                                Sonuçlar Postgres'e (metadata) + MinIO'ya (raster/vektör dosyalar) yazılır
                                                                        │
                                                                        ▼
                                        WebSocket ile frontend'e "done" bildirimi + job durumu her adımda güncellenir
```

- Faz 1 (SAR) ve Faz 2 (MS) ve Faz 3 (Meteoroloji) orijinal mimaride paralel yürüdüğü için, Celery'de bir **`chord`** (paralel `group` + callback) ile modellenir: üç pipeline paralel çalışır, hepsi bitince füzyon adımı otomatik tetiklenir.
- Uzun süren GEE çağrıları için timeout + retry politikası (`Task.retry`, `Retry-After` header'ı ile GEE rate-limit durumuna saygı).

---

## 7. Veri Katmanı

- **PostgreSQL + PostGIS:** AOI polygonları, parsel sınırları, grid hücreleri, hotspot sonuçları — mekansal sorgular (`ST_Intersects`, `ST_Area`) doğrudan veritabanında.
- **SQLAlchemy 2.0 + GeoAlchemy2:** ORM + geometri tipi desteği.
- **Alembic:** Şema migration yönetimi.
- **MinIO (S3 uyumlu):** GeoTIFF, Shapefile, GeoPackage gibi büyük binary çıktılar; veritabanında sadece referans (URL/key) tutulur.
- **Redis:** Celery broker + job durumu cache + (opsiyonel) API response cache.

### Örnek Entity Listesi
`User`, `Project`, `AOI`, `AnalysisJob` (status, weights, created_by), `ParcelDamageResult`, `GridCell`, `HotspotResult`, `WeatherEvent`, `OutputArtifact` (dosya tipi, MinIO key, job_id).

---

## 8. API Tasarımı (Özet)

```
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/aois
POST   /api/v1/aois
GET    /api/v1/aois/{id}/mask-preview

POST   /api/v1/jobs                     # analiz başlat
GET    /api/v1/jobs/{id}                # durum sorgula
WS     /api/v1/jobs/{id}/stream         # real-time ilerleme

GET    /api/v1/jobs/{id}/results/summary
GET    /api/v1/jobs/{id}/results/parcels
GET    /api/v1/jobs/{id}/results/hotspots
GET    /api/v1/jobs/{id}/export?format=geotiff|geojson|shapefile|geopackage|csv

GET    /api/v1/admin/queue-health
```

FastAPI'nin otomatik ürettiği `/docs` (Swagger UI) ve `/redoc` bu listeyi canlı ve interaktif olarak zaten sağlar — ayrı bir dokümantasyon aracına gerek yok.

---

## 9. Frontend Mimarisi (Next.js)

### 9.1 Verilen Kütüphanelerin Kullanım Haritası

| Kütüphane | Kullanım Alanı |
|---|---|
| `next` (16) / `react` (19) | App Router, Server Components + Client Components karışımı |
| `next-auth` | FastAPI JWT ile kimlik doğrulama entegrasyonu (Credentials provider) |
| `next-themes` | Açık/koyu tema — orijinal mimarideki renk paletini (Faz 0-6 renkleri) CSS değişkeni olarak koruyup tema token'ı yapabiliriz |
| `react-hook-form` + `@hookform/resolvers` + `zod` | AOI oluşturma formu, ağırlık konfigürasyon formu, login formu — validasyon şeması backend Pydantic şemasıyla birebir örtüşecek şekilde tasarlanmalı |
| `zustand` | Global state: seçili AOI, aktif job, harita katman görünürlüğü |
| `nuqs` | URL'de senkron filtre state'i (tarih aralığı, hasar sınıfı filtresi) — paylaşılabilir link üretir |
| `sonner` | Job tamamlandı/hata bildirimleri (toast) |
| `framer-motion` | Faz pipeline'ının görsel akışı (orijinal HTML'deki gibi) ve job progress animasyonu |
| `radix-ui` (label, slot) + `class-variance-authority` + `clsx` + `tailwind-merge` | shadcn/ui tarzı bileşen sistemi temeli |
| `date-fns` | Olay tarihi / zaman serisi formatlamaları |
| `lucide-react` | İkon seti |

### 9.2 Klasör Yapısı (özet)

```
frontend/
├── app/
│   ├── (auth)/login/
│   ├── (dashboard)/
│   │   ├── aois/
│   │   ├── jobs/[id]/          # harita + sonuç görünümü
│   │   └── admin/
│   ├── api/                     # (gerekirse) BFF route handler'ları
│   └── layout.tsx
├── components/
│   ├── ui/                      # shadcn/ui tabanlı primitive bileşenler
│   ├── map/                     # harita katmanları
│   └── pipeline/                # faz akış görselleştirmesi
├── lib/
│   ├── api-client.ts            # FastAPI ile tip güvenli iletişim
│   ├── stores/                  # zustand store'ları
│   └── schemas/                 # zod şemaları (backend Pydantic ile senkron)
└── styles/theme.css              # açık/koyu tema CSS değişkenleri
```

---

## 10. Ek Öneriler (Eklenmesini Önerdiğim Kütüphaneler)

**Backend**
- `celery` + `redis` — asenkron job kuyruğu (zorunlu, yukarıda açıklandı)
- `SQLAlchemy 2.0` + `GeoAlchemy2` + `alembic` — ORM + spatial + migration
- `pydantic-settings` — ortam değişkeni tabanlı config yönetimi
- `structlog` — yapılandırılmış loglama
- `slowapi` — rate limiting
- `dependency-injector` (opsiyonel) — daha büyük DI ihtiyaçları için
- `pytest` + `pytest-asyncio` + `httpx` + `testcontainers` — test altyapısı
- `python-jose` + `passlib[bcrypt]` — JWT/şifre yönetimi

**Frontend**
- `@tanstack/react-query` — job polling, cache invalidation, server state yönetimi (react-hook-form form state'i yönetir ama **veri çekme** için bu şart)
- `maplibre-gl` veya `react-map-gl` — hasar haritası, parsel/grid/hotspot katmanları; büyük GeoTIFF'ler için Cloud-Optimized GeoTIFF (COG) + `titiler` tile servisi önerilir
- `recharts` — korelasyon grafiği, zaman serisi grafiği
- `@tanstack/react-table` — parsel hasar tablosu (sıralama/filtreleme)
- `vitest` + `@testing-library/react` + `playwright` — unit + e2e test

**Altyapı**
- `titiler` (Docker servisi) — COG raster dosyalarını doğrudan haritada tile olarak sunmak için (GeoTIFF'i her seferinde tam indirmek yerine)
- `flower` — Celery izleme paneli (dev/staging'de faydalı)

---

## 11. Docker Compose İskeleti (Örnek)

```yaml
services:
  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    env_file: .env
    depends_on: [postgres, redis, minio]
    ports: ["8000:8000"]

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    command: celery -A app.infrastructure.tasks worker -l info
    env_file: .env
    depends_on: [postgres, redis, minio]
    deploy:
      replicas: 2

  worker-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    command: celery -A app.infrastructure.tasks beat -l info
    env_file: .env
    depends_on: [redis]

  redis:
    image: redis:7-alpine

  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: damage_analysis
    volumes: ["pgdata:/var/lib/postgresql/data"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: ["minio_data:/data"]
    ports: ["9000:9000", "9001:9001"]

  frontend:
    build: ./frontend
    env_file: ./frontend/.env
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pgdata:
  minio_data:
```

---

## 12. PR / Sprint Planı (Faz Eşlemesi)

| Sprint | Kapsam | Orijinal Faz Karşılığı |
|---|---|---|
| **Sprint 0** | Repo iskeleti, Docker Compose, CI/CD, auth iskeleti, boş katman yapısı | — |
| **Sprint 1** | AOI/mask yönetimi, entity + repository katmanı, temel CRUD API | Faz 0 |
| **Sprint 2** | SAR pipeline entegrasyonu (Celery task + GEE client) | Faz 1 |
| **Sprint 3** | MS pipeline entegrasyonu (paralel çalışacak şekilde) | Faz 2 |
| **Sprint 4** | Meteoroloji doğrulama entegrasyonu + eşik mantığı | Faz 3 |
| **Sprint 5** | Füzyon skorlama (Strategy pattern) + sınıflandırma | Faz 4 |
| **Sprint 6** | Uzamsal birikim (parsel/grid/hotspot) | Faz 5 |
| **Sprint 7** | Export/çıktı üretimi + MinIO entegrasyonu | Faz 6 |
| **Sprint 8** | Frontend: harita görünümü, job progress UI, sonuç tabloları | Web-özel |
| **Sprint 9** | Tema (açık/koyu), dashboard, admin paneli | Web-özel |
| **Sprint 10** | Test kapsamı, güvenlik sıkılaştırma, performans, prod deployment | Web-özel |

---

## 13. Riskler & Notlar

- **GEE kota/limit riski:** Google Earth Engine API çağrı limitleri var; worker'larda retry + backoff şart, aksi halde çoklu job aynı anda tetiklendiğinde rate-limit hatası alınır.
- **Büyük dosya transferi:** GeoTIFF'ler onlarca-yüzlerce MB olabilir; bunları API response'unda değil, MinIO üzerinden presigned URL ile sunmak gerekir.
- **Job progress granülerliği:** Kullanıcı deneyimi için job durumunu sadece "queued/done" değil, ara adımlarla (SAR indiriliyor, MS işleniyor vb.) güncellemek UI/UX açısından önemli — Celery task'larında ara `update_state()` çağrıları planlanmalı.
- **Test verisi:** GEE'ye gerçek çağrı yapmadan test edebilmek için mock/fixture stratejisi (VCR.py veya kayıtlı response fixture'ları) baştan kurulmalı, yoksa test süreci çok yavaş/kırılgan olur.