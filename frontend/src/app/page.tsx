"use client"
import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { toast } from 'sonner';
import ExportModal from '@/components/ExportModal';

// Helper: single pipeline status row
function statusColor(status: string | null) {
  if (status === 'done') return 'text-green-400';
  if (status === 'failed') return 'text-red-400';
  if (status === 'processing') return 'text-blue-400';
  return 'text-zinc-500';
}

function PipelineRow({ label, status }: { label: string; status: string | null }) {
  const isRunning = status && status !== 'done' && status !== 'failed';
  return (
    <div className="flex items-center justify-between py-1.5 border-t border-zinc-800/60 mt-2">
      <span className="text-xs text-zinc-400">{label}</span>
      <div className="flex items-center gap-2">
        {isRunning && (
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
        )}
        <span className={`text-xs font-semibold uppercase ${statusColor(status)}`}>
          {status || 'queued'}
        </span>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [wkt, setWkt] = useState<string | null>(null);
  const [aoiName, setAoiName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [sarStatus, setSarStatus] = useState<string | null>(null);
  const [msStatus, setMsStatus] = useState<string | null>(null);
  const [weatherStatus, setWeatherStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [areaHa, setAreaHa] = useState<number>(0);

  // Weights state
  const [showWeights, setShowWeights] = useState(false);
  const [weightSar, setWeightSar] = useState(0.35);
  const [weightNdmi, setWeightNdmi] = useState(0.25);
  const [weightNdre, setWeightNdre] = useState(0.20);
  const [weightPrecip, setWeightPrecip] = useState(0.12);
  const [weightSm, setWeightSm] = useState(0.08);

  // Results state
  const [summaryData, setSummaryData] = useState<any | null>(null);
  const [gridData, setGridData] = useState<any[]>([]);
  const [hotspotData, setHotspotData] = useState<any[]>([]);
  const [showGridList, setShowGridList] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  const MAX_AREA_HA = 25000;

  // Leaflet needs 'window' — load only on client
  const MapComponent = useMemo(
    () => dynamic(() => import('@/components/Map'), {
      ssr: false,
      loading: () => (
        <div className="w-full h-full rounded-xl bg-zinc-900 flex items-center justify-center text-zinc-500">
          Harita yükleniyor...
        </div>
      ),
    }),
    []
  );

  const handlePolygonChange = (newWkt: string | null, ha?: number) => {
    setWkt(newWkt);
    setAreaHa(ha ?? 0);
  };

  const handleSave = async () => {
    if (!wkt) {
      toast.error("Lütfen haritada bir alan (AOI) çizin.");
      return;
    }
    if (areaHa > MAX_AREA_HA) {
      toast.error(`Alan çok büyük (${Math.round(areaHa).toLocaleString('tr-TR')} ha). Lütfen ${MAX_AREA_HA.toLocaleString('tr-TR')} ha'dan küçük bir alan seçin.`);
      return;
    }
    if (!aoiName.trim()) {
      toast.error("Lütfen AOI için bir isim girin.");
      return;
    }
    if (!eventDate) {
      toast.error("Lütfen olay tarihini girin.");
      return;
    }

    setIsSaving(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // 1. Create AOI
      const aoiResponse = await fetch(`${apiUrl}/api/v1/aoi/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: aoiName, geometry: wkt })
      });

      if (!aoiResponse.ok) throw new Error("AOI kaydı başarısız.");
      const aoiData = await aoiResponse.json();
      toast.success("AOI kaydedildi, Analiz başlatılıyor...");

      // 2. Create Job
      const jobResponse = await fetch(`${apiUrl}/api/v1/jobs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aoi_id: aoiData.id,
          event_date: new Date(eventDate).toISOString(),
          weights: {
            sar: weightSar,
            ndmi: weightNdmi,
            ndre: weightNdre,
            precipitation: weightPrecip,
            soil_moisture: weightSm
          }
        })
      });

      if (!jobResponse.ok) throw new Error("Analiz işi başlatılamadı.");
      const jobData = await jobResponse.json();

      setActiveJobId(jobData.id);
      setJobStatus(jobData.status);
      setSarStatus(jobData.sar_status);
      setMsStatus(jobData.ms_status);
      setErrorMessage(null);
      toast.info("Analiz sıraya alındı.");

    } catch (error: any) {
      toast.error(error.message);
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  // Poll for job status
  useEffect(() => {
    if (!activeJobId) return;
    if (jobStatus === "done" || jobStatus === "failed") return;

    const interval = setInterval(async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/jobs/${activeJobId}`);
        if (res.ok) {
          const data = await res.json();
          setJobStatus(data.status);
          setSarStatus(data.sar_status);
          setMsStatus(data.ms_status);
          setWeatherStatus(data.weather_status);
          if (data.status === "done") {
            toast.success("Analiz tamamlandı!");
            // Fetch summary, grid, and hotspots results
            try {
              const [summaryRes, gridRes, hsRes] = await Promise.all([
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/summary`),
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/grid`),
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/hotspots`)
              ]);
              if (summaryRes.ok) {
                const sData = await summaryRes.json();
                setSummaryData(sData);
              }
              if (gridRes.ok) {
                const gData = await gridRes.json();
                setGridData(gData.features || []);
              }
              if (hsRes.ok) {
                const hData = await hsRes.json();
                setHotspotData(hData.features || []);
              }
            } catch (err) {
              console.error("Failed to load results", err);
            }
          } else if (data.status === "failed") {
            setErrorMessage(data.error_message);
            toast.error("Analiz başarısız oldu.");
          }
        }
      } catch (e) {
        console.error("Failed to fetch job status", e);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [activeJobId, jobStatus]);

  return (
    <main className="min-h-screen bg-background text-foreground p-8 flex flex-col">
      <div className="max-w-7xl mx-auto space-y-8 flex-1 w-full flex flex-col">
        <header className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">SAR + MS Analiz Platformu</h1>
          <p className="text-muted-foreground text-lg">
            Tarımsal hasar tespiti için Alan Seçimi (AOI) ve gerçek zamanlı izleme.
          </p>
        </header>

        <section className="flex flex-col md:flex-row gap-6 flex-1 h-[calc(100vh-170px)] min-h-[600px] items-stretch">
          {/* Map Area */}
          <div className="flex-1 h-full rounded-xl relative">
            <MapComponent
              onPolygonChange={handlePolygonChange}
              gridFeatures={gridData}
              hotspotFeatures={hotspotData}
            />
          </div>

          {/* Sidebar / Form */}
          <div className="w-full md:w-96 flex flex-col gap-4 bg-zinc-900/50 p-6 rounded-xl border border-zinc-800 h-full overflow-y-auto custom-scrollbar">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Yeni Analiz Başlat</h2>
              <p className="text-sm text-muted-foreground mt-1">Harita üzerinden tarlayı çizin ve tarihi seçin.</p>
            </div>

            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">AOI Adı</label>
                <input
                  type="text"
                  value={aoiName}
                  onChange={(e) => setAoiName(e.target.value)}
                  placeholder="Örn: Çukurova Buğday Tarlası"
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Olay Tarihi (Afet)</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  style={{ colorScheme: 'dark' }}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Seçili Alan (WKT)</label>
                <textarea
                  readOnly
                  value={wkt || "Henüz alan çizilmedi..."}
                  className="flex min-h-[80px] w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-400 focus:outline-none"
                />
              </div>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setShowWeights(!showWeights)}
                  className="text-xs text-blue-400 hover:text-blue-300 font-medium"
                >
                  {showWeights ? "Ağırlık Ayarlarını Gizle" : "Ağırlık Ayarlarını Göster (Opsiyonel)"}
                </button>

                {showWeights && (
                  <div className="grid grid-cols-2 gap-3 p-3 bg-zinc-950 border border-zinc-800 rounded-md mt-2">
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">SAR Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSar} onChange={e => setWeightSar(parseFloat(e.target.value) || 0)} className="w-full h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">NDMI Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdmi} onChange={e => setWeightNdmi(parseFloat(e.target.value) || 0)} className="w-full h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">NDRE Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdre} onChange={e => setWeightNdre(parseFloat(e.target.value) || 0)} className="w-full h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-zinc-400">Yağış Ağırlığı</label>
                      <input type="number" step="0.01" value={weightPrecip} onChange={e => setWeightPrecip(parseFloat(e.target.value) || 0)} className="w-full h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1 col-span-2">
                      <label className="text-xs text-zinc-400">Toprak Nemi Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSm} onChange={e => setWeightSm(parseFloat(e.target.value) || 0)} className="w-full h-8 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                  </div>
                )}
              </div>

              <button 
                onClick={handleSave}
                disabled={isSaving || !wkt || areaHa > MAX_AREA_HA || (activeJobId !== null && jobStatus !== 'done' && jobStatus !== 'failed')}
                className="w-full h-10 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none"
              >
                {isSaving ? "İşleniyor..." : "Analizi Başlat"}
              </button>

              {/* Area too large warning */}
              {wkt && areaHa > MAX_AREA_HA && (
                <div className="p-3 bg-amber-950/40 border border-amber-700/60 rounded-lg">
                  <p className="text-xs text-amber-300 font-medium">⚠️ Alan Sınırı Aşıldı</p>
                  <p className="text-xs text-amber-400/80 mt-1">
                    Seçilen alan <strong>{Math.round(areaHa).toLocaleString('tr-TR')} ha</strong>.
                    GEE indirme limiti nedeniyle maksimum <strong>~{MAX_AREA_HA.toLocaleString('tr-TR')} ha</strong> desteklenmektedir.
                    Lütfen haritada daha küçük bir alan çizin.
                  </p>
                </div>
              )}

              {/* Status Tracking */}
              {activeJobId && (
                <div className="mt-6 p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">İşlem Durumu</h3>
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-bold uppercase tracking-wider ${jobStatus === 'failed' ? 'text-red-500' : 'text-white'}`}>
                      {jobStatus || "BİLİNMİYOR"}
                    </span>
                    {jobStatus !== "done" && jobStatus !== "failed" && (
                      <span className="flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                      </span>
                    )}
                  </div>

                  {/* SAR Pipeline row */}
                  <PipelineRow label="🛰️ SAR Pipeline" status={sarStatus} />

                  {/* MS Pipeline row */}
                  <PipelineRow label="🌿 MS Pipeline" status={msStatus} />

                  {/* Weather Pipeline row */}
                  <PipelineRow label="🌤️ Weather Pipeline" status={weatherStatus} />

                  <p className="text-xs text-zinc-500 mt-2 truncate" title={activeJobId}>
                    ID: {activeJobId}
                  </p>
                  {jobStatus === 'failed' && errorMessage && (
                    <div className="mt-3 p-3 bg-red-950/30 border border-red-900/50 rounded-md">
                      <p className="text-xs text-red-400 break-words font-mono">
                        {errorMessage}
                      </p>
                    </div>
                  )}

                  {/* Sprint 6: Results Summary & MVP Grid Table */}
                  {summaryData && (
                    <div className="mt-4 pt-4 border-t border-zinc-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-zinc-300">📊 Uzamsal Birikim Özeti</span>
                        <span className="text-[10px] bg-blue-950 text-blue-300 border border-blue-800 px-1.5 py-0.5 rounded">H3 Hex</span>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">Ortalama Hasar</p>
                          <p className="text-base font-bold text-amber-400">%{Math.round(summaryData.mean_damage_score * 100)}</p>
                        </div>
                        <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">Toplam Grid Hücresi</p>
                          <p className="text-base font-bold text-zinc-200">{summaryData.total_cells}</p>
                        </div>
                        <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">🔥 Hotspot Odak</p>
                          <p className="text-base font-bold text-red-400">{summaryData.hotspot_cells_count}</p>
                        </div>
                        <div className="p-2.5 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">❄️ Coldspot (Güvenli)</p>
                          <p className="text-base font-bold text-emerald-400">{summaryData.coldspot_cells_count}</p>
                        </div>
                      </div>

                      {/* Class Distribution Badges */}
                      <div className="space-y-1 pt-1">
                        <p className="text-[10px] text-zinc-400 font-medium">Hasar Sınıf Dağılımı</p>
                        <div className="flex flex-wrap gap-1">
                          <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded">
                            Yok: {summaryData.distribution?.Yok || 0}
                          </span>
                          <span className="text-[10px] bg-yellow-950 text-yellow-300 border border-yellow-800 px-2 py-0.5 rounded">
                            Hafif: {summaryData.distribution?.Hafif || 0}
                          </span>
                          <span className="text-[10px] bg-orange-950 text-orange-300 border border-orange-800 px-2 py-0.5 rounded">
                            Orta: {summaryData.distribution?.Orta || 0}
                          </span>
                          <span className="text-[10px] bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded">
                            Ağır: {summaryData.distribution?.Ağır || 0}
                          </span>
                        </div>
                      </div>

                      {/* Export & Download Hub Button */}
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={() => setIsExportOpen(true)}
                          className="w-full py-2.5 px-4 flex items-center justify-center gap-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-lg shadow-lg shadow-emerald-950/40 border border-emerald-500/30 transition-all cursor-pointer"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          📥 Rapor & Çıktıları İndir (PDF, GeoTIFF, Vektör)
                        </button>
                      </div>

                      {/* Toggle Grid Table */}
                      <div className="pt-1">
                        <button
                          type="button"
                          onClick={() => setShowGridList(!showGridList)}
                          className="w-full py-1.5 text-xs text-zinc-400 bg-zinc-900 hover:bg-zinc-850 border border-zinc-800 rounded font-medium transition-colors"
                        >
                          {showGridList ? "Grid Listesini Gizle" : `Grid Hücrelerini Listele (${gridData.length})`}
                        </button>

                        {showGridList && (
                          <div className="mt-2 max-h-48 overflow-y-auto space-y-1.5 pr-1 text-[11px]">
                            {gridData.map((f, i) => (
                              <div key={i} className="p-2 bg-zinc-900/80 rounded border border-zinc-800/80 flex items-center justify-between">
                                <div>
                                  <p className="font-mono text-[10px] text-zinc-300">{f.properties.h3_index}</p>
                                  <p className="text-zinc-500 text-[9px]">{f.properties.damage_class}</p>
                                </div>
                                <span className={`font-semibold ${f.properties.damage_score > 0.45 ? 'text-red-400' : 'text-zinc-300'}`}>
                                  %{Math.round(f.properties.damage_score * 100)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Sprint 7: Export & Reporting Modal */}
      {activeJobId && (
        <ExportModal
          isOpen={isExportOpen}
          onClose={() => setIsExportOpen(false)}
          jobId={activeJobId}
        />
      )}
    </main>
  );
}
