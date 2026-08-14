"use client"
import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { toast } from 'sonner';
import ExportModal from '@/components/ExportModal';
import TimeSeriesChart from '@/components/TimeSeriesChart';

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
  const [isCleaning, setIsCleaning] = useState(false);
  const [clearKey, setClearKey] = useState(0);

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

  const handleResetAll = (resetMap: boolean = true) => {
    setWkt(null);
    setAoiName("");
    setEventDate("");
    setAreaHa(0);
    setActiveJobId(null);
    setJobStatus(null);
    setSarStatus(null);
    setMsStatus(null);
    setWeatherStatus(null);
    setSummaryData(null);
    setGridData([]);
    setHotspotData([]);
    setErrorMessage(null);
    if (resetMap) {
      setClearKey(prev => prev + 1);
    }
    toast.info("Harita ve analiz paneli sıfırlandı.");
  };

  const handleResetFromMap = () => {
    handleResetAll(false);
  };

  const handleStorageCleanup = async () => {
    setIsCleaning(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/v1/system/cleanup`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Geçici disk dosyaları temizlendi! (${data.freed_mb} MB yer açıldı, ${data.local_files_removed} dosya silindi)`);
      } else {
        toast.error("Temizleme işlemi tamamlanamadı.");
      }
    } catch (err: any) {
      toast.error("Temizleme sırasında hata oluştu: " + err.message);
    } finally {
      setIsCleaning(false);
    }
  };

  const handleSave = async () => {
    if (!wkt) {
      toast.error("Lütfen haritada en az 3 nokta ile bir alan (AOI) çizin.");
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

    // 1. Immediately reset previous analysis and clear old grid hexagons
    setSummaryData(null);
    setGridData([]);
    setHotspotData([]);
    setJobStatus("processing");
    setSarStatus("pending");
    setMsStatus("pending");
    setWeatherStatus("pending");
    setErrorMessage(null);
    setIsSaving(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // 2. Create AOI
      const aoiResponse = await fetch(`${apiUrl}/api/v1/aoi/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: aoiName, geometry: wkt })
      });

      if (!aoiResponse.ok) throw new Error("AOI kaydı başarısız.");
      const aoiData = await aoiResponse.json();
      toast.success("AOI kaydedildi, Analiz başlatılıyor...");

      // 3. Create Job
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
      setWeatherStatus(jobData.weather_status);
      setErrorMessage(null);
      toast.info("Analiz sıraya alındı.");

    } catch (error: any) {
      toast.error(error.message);
      setJobStatus("failed");
      setErrorMessage(error.message);
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
            } catch (rErr) {
              console.error("Results fetch error:", rErr);
            }
          } else if (data.status === "failed") {
            setErrorMessage(data.error_message || "Analiz sırasında bir hata oluştu.");
            toast.error("Analiz başarısız oldu.");
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeJobId, jobStatus]);

  return (
    <main className="min-h-screen bg-background text-foreground p-8 flex flex-col">
      <div className="max-w-7xl mx-auto space-y-6 flex-1 w-full flex flex-col">
        {/* Header & Quick Action Buttons */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-extrabold tracking-tight text-zinc-100">SAR + MS Tarımsal Hasar Analiz Platformu</h1>
            <p className="text-muted-foreground text-sm">
              Çoklu sensör uydu füzyonu, H3 uzamsal birikim ve meteorolojik afet değerlendirme sistemi.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleStorageCleanup}
              disabled={isCleaning}
              className="px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              title="Geçici raster dosyalarını ve disk önbelleğini temizler"
            >
              {isCleaning ? (
                <>
                  <span className="w-3 h-3 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin" />
                  Temizleniyor...
                </>
              ) : (
                <>
                  <span>🗑️</span> Diski & Önbelleği Temizle
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => handleResetAll(true)}
              className="px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer"
              title="Haritadaki çizimi, hücreleri ve sonuçları sıfırlar"
            >
              <span>🧹</span> Haritayı Sıfırla
            </button>
          </div>
        </header>

        <section className="flex flex-col md:flex-row gap-6 flex-1 h-[calc(100vh-170px)] min-h-[600px] items-stretch">
          {/* Map Area */}
          <div className="flex-1 h-full rounded-xl relative">
            <MapComponent
              onPolygonChange={handlePolygonChange}
              gridFeatures={gridData}
              hotspotFeatures={hotspotData}
              clearKey={clearKey}
              isAnalyzing={isSaving || (activeJobId !== null && jobStatus === 'processing')}
              onResetAll={handleResetFromMap}
            />
          </div>

          {/* Sidebar / Form */}
          <div className="w-full md:w-96 flex flex-col gap-4 bg-zinc-900/50 p-6 rounded-xl border border-zinc-800 h-full overflow-y-auto custom-scrollbar">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-zinc-100">Yeni Analiz Başlat</h2>
              <p className="text-xs text-muted-foreground mt-1">Harita üzerinden tarlayı çizin ve tarihi seçin.</p>
            </div>

            <div className="space-y-4 mt-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">AOI / Tarla Adı</label>
                <input
                  type="text"
                  value={aoiName}
                  onChange={(e) => setAoiName(e.target.value)}
                  placeholder="Örn: Çukurova Buğday Tarlası"
                  className="flex h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Olay Tarihi (Afet)</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  style={{ colorScheme: 'dark' }}
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-300">Seçili Alan (WKT)</label>
                  {areaHa > 0 && (
                    <span className="text-[11px] font-semibold text-emerald-400">
                      {Math.round(areaHa).toLocaleString('tr-TR')} ha
                    </span>
                  )}
                </div>
                <textarea
                  readOnly
                  rows={2}
                  value={wkt || "Henüz alan çizilmedi..."}
                  className="flex w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-[11px] text-zinc-400 font-mono focus:outline-none resize-none"
                />
              </div>

              <div className="space-y-1.5">
                <button
                  type="button"
                  onClick={() => setShowWeights(!showWeights)}
                  className="text-xs text-blue-400 hover:text-blue-300 font-medium"
                >
                  {showWeights ? "Ağırlık Ayarlarını Gizle" : "Ağırlık Ayarlarını Göster (Opsiyonel)"}
                </button>

                {showWeights && (
                  <div className="grid grid-cols-2 gap-2.5 p-3 bg-zinc-950 border border-zinc-800 rounded-md mt-1.5">
                    <div className="space-y-1">
                      <label className="text-[10px] text-zinc-400">SAR Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSar} onChange={e => setWeightSar(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] text-zinc-400">NDMI Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdmi} onChange={e => setWeightNdmi(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] text-zinc-400">NDRE Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdre} onChange={e => setWeightNdre(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] text-zinc-400">Yağış Ağırlığı</label>
                      <input type="number" step="0.01" value={weightPrecip} onChange={e => setWeightPrecip(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                    <div className="space-y-1 col-span-2">
                      <label className="text-[10px] text-zinc-400">Toprak Nemi Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSm} onChange={e => setWeightSm(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-300" />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2 pt-1">
                <button 
                  onClick={handleSave}
                  disabled={isSaving || !wkt || areaHa > MAX_AREA_HA || (activeJobId !== null && jobStatus !== 'done' && jobStatus !== 'failed')}
                  className="flex-1 h-10 inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-semibold transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                >
                  {isSaving ? "Analiz Başlatılıyor..." : "🚀 Analizi Başlat"}
                </button>
                <button 
                  type="button"
                  onClick={() => handleResetAll(true)}
                  className="px-3 h-10 inline-flex items-center justify-center rounded-md text-xs font-medium text-zinc-400 bg-zinc-800 hover:bg-zinc-700 hover:text-white transition-colors cursor-pointer"
                  title="Temizle"
                >
                  Temizle
                </button>
              </div>

              {/* Area too large warning */}
              {wkt && areaHa > MAX_AREA_HA && (
                <div className="p-3 bg-red-950/40 border border-red-700/60 rounded-lg">
                  <p className="text-xs text-red-300 font-medium">⚠️ Alan Sınırı Aşıldı</p>
                  <p className="text-[11px] text-red-400/90 mt-1">
                    Seçilen alan <strong>{Math.round(areaHa).toLocaleString('tr-TR')} ha</strong>.
                    Maksimum <strong>~{MAX_AREA_HA.toLocaleString('tr-TR')} ha</strong> desteklenmektedir.
                  </p>
                </div>
              )}

              {/* Status Tracking */}
              {activeJobId && (
                <div className="mt-4 p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                  <h3 className="text-xs font-semibold text-zinc-400 mb-2">İşlem Durumu</h3>
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-bold uppercase tracking-wider ${jobStatus === 'failed' ? 'text-red-500' : jobStatus === 'done' ? 'text-green-400' : 'text-blue-400'}`}>
                      {jobStatus || "BİLİNMİYOR"}
                    </span>
                    {jobStatus !== "done" && jobStatus !== "failed" && (
                      <span className="flex h-2.5 w-2.5 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
                      </span>
                    )}
                  </div>

                  {/* SAR Pipeline row */}
                  <PipelineRow label="🛰️ SAR Pipeline" status={sarStatus} />

                  {/* MS Pipeline row */}
                  <PipelineRow label="🌿 MS Pipeline" status={msStatus} />

                  {/* Weather Pipeline row */}
                  <PipelineRow label="🌤️ Weather Pipeline" status={weatherStatus} />

                  <p className="text-[10px] text-zinc-500 mt-2 truncate font-mono" title={activeJobId}>
                    ID: {activeJobId}
                  </p>
                  {jobStatus === 'failed' && errorMessage && (
                    <div className="mt-3 p-2.5 bg-red-950/30 border border-red-900/50 rounded-md">
                      <p className="text-[11px] text-red-400 break-words font-mono">
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
                        <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">Ortalama Hasar</p>
                          <p className="text-sm font-bold text-amber-400">%{Math.round(summaryData.mean_damage_score * 100)}</p>
                        </div>
                        <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">Toplam Grid</p>
                          <p className="text-sm font-bold text-zinc-200">{summaryData.total_cells}</p>
                        </div>
                        <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">🔥 Hotspot Odak</p>
                          <p className="text-sm font-bold text-red-400">{summaryData.hotspot_cells_count}</p>
                        </div>
                        <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                          <p className="text-[10px] text-zinc-400">❄️ Coldspot</p>
                          <p className="text-sm font-bold text-emerald-400">{summaryData.coldspot_cells_count}</p>
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

        {/* Sprint 8: 30-Day Meteorological Time Series Chart */}
        {activeJobId && summaryData && (
          <div className="pt-2">
            <TimeSeriesChart jobId={activeJobId} />
          </div>
        )}
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
