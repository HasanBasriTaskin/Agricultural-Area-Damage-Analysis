"use client"
import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';
import ExportModal from '@/components/ExportModal';
import TimeSeriesChart from '@/components/TimeSeriesChart';
import { Sidebar } from '@/components/Sidebar';

// Helper: single pipeline status row
function statusColor(status: string | null) {
  if (status === 'done') return 'text-emerald-600 dark:text-green-400';
  if (status === 'failed') return 'text-red-600 dark:text-red-400';
  if (status === 'processing') return 'text-blue-600 dark:text-blue-400';
  return 'text-zinc-400 dark:text-zinc-500';
}

function PipelineRow({ label, status }: { label: string; status: string | null }) {
  const isRunning = status && status !== 'done' && status !== 'failed';
  return (
    <div className="flex items-center justify-between py-1.5 border-t border-zinc-200 dark:border-zinc-800/60 mt-2">
      <span className="text-xs text-zinc-600 dark:text-zinc-400">{label}</span>
      <div className="flex items-center gap-2">
        {isRunning && (
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
        )}
        <span className={`text-xs font-semibold uppercase ${statusColor(status)}`}>
          {status || 'queued'}
        </span>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { data: session } = useSession();
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
  const [isExportOpen, setIsExportOpen] = useState(false);

  const MAX_AREA_HA = 25000;

  // Leaflet needs 'window' — load only on client
  const MapComponent = useMemo(
    () => dynamic(() => import('@/components/Map'), {
      ssr: false,
      loading: () => (
        <div className="w-full h-full rounded-xl bg-zinc-200 dark:bg-zinc-900 flex items-center justify-center text-zinc-500">
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
  };

  const handleResetFromMap = () => {
    handleResetAll(false);
  };

  // Helper to obtain a valid Bearer token (if present)
  const getAuthToken = (): string | null => {
    return session?.accessToken || null;
  };

  // Load job from URL search param if present (e.g., from /jobs page view link)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const qJobId = params.get("jobId");
      if (qJobId && qJobId !== activeJobId) {
        setActiveJobId(qJobId);
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        
        // Fetch job metadata
        fetch(`${apiUrl}/api/v1/jobs/${qJobId}`).then(async (res) => {
          if (res.ok) {
            const jData = await res.json();
            setAoiName(jData.aoi_name || "");
            if (jData.event_date) {
              setEventDate(jData.event_date.split("T")[0]);
            }
            setJobStatus(jData.status || "done");
            setSarStatus(jData.sar_status || "done");
            setMsStatus(jData.ms_status || "done");
            setWeatherStatus(jData.weather_status || "done");
          }
        }).catch(err => console.error("Job meta fetch error:", err));

        // Fetch analysis layers & summary
        Promise.all([
          fetch(`${apiUrl}/api/v1/jobs/${qJobId}/results/summary`),
          fetch(`${apiUrl}/api/v1/jobs/${qJobId}/results/grid`),
          fetch(`${apiUrl}/api/v1/jobs/${qJobId}/results/hotspots`)
        ]).then(async ([sRes, gRes, hRes]) => {
          if (sRes.ok) setSummaryData(await sRes.json());
          if (gRes.ok) {
            const g = await gRes.json();
            setGridData(g.features || []);
          }
          if (hRes.ok) {
            const h = await hRes.json();
            setHotspotData(h.features || []);
          }
          toast.success("Geçmiş analiz ve harita katmanları yüklendi.");
        }).catch(err => console.error(err));
      }
    }
  }, []);

  const handleCleanStorage = async () => {
    if (!confirm("Dikkat: Sadece yerel geçici raster ve cache dosyaları temizlenecektir. Devam etmek istiyor musunuz?")) {
      return;
    }
    setIsCleaning(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const token = getAuthToken();
      const res = await fetch(`${apiUrl}/api/v1/system/clean-storage`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Temizlik tamamlandı: ${data.cleaned_count || 0} geçici dosya temizlendi.`);
        handleResetAll(true);
      } else {
        toast.error("Temizlik işlemi sırasında hata oluştu.");
      }
    } catch (err) {
      toast.error("Sunucuya bağlanılamadı.");
    } finally {
      setIsCleaning(false);
    }
  };

  const handleSave = async () => {
    if (!wkt) {
      toast.error("Lütfen harita üzerinden bir alan çizin!");
      return;
    }
    if (!eventDate) {
      toast.error("Lütfen bir olay tarihi seçin!");
      return;
    }
    if (areaHa > MAX_AREA_HA) {
      toast.error(`Çizilen alan (${Math.round(areaHa).toLocaleString('tr-TR')} ha) maksimum 25.000 ha sınırını aşıyor!`);
      return;
    }

    // 1. Reset previous results & status
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
      const token = getAuthToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 2. Create AOI
      const aoiResponse = await fetch(`${apiUrl}/api/v1/aoi/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: aoiName || "İsimsiz Parsel", geometry: wkt })
      });

      if (!aoiResponse.ok) throw new Error("AOI kaydı başarısız.");
      const aoiData = await aoiResponse.json();
      toast.success("AOI kaydedildi, Analiz başlatılıyor...");

      // 3. Create Job
      const jobResponse = await fetch(`${apiUrl}/api/v1/jobs/`, {
        method: 'POST',
        headers,
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
        const token = getAuthToken();
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${apiUrl}/api/v1/jobs/${activeJobId}`, { headers });
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
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/summary`, { headers }),
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/grid`, { headers }),
                fetch(`${apiUrl}/api/v1/jobs/${activeJobId}/results/hotspots`, { headers })
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
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [activeJobId, jobStatus]);

  return (
    <div className="min-h-screen flex bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-200 selection:bg-emerald-500 selection:text-black">
      {/* Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col p-6 space-y-6 overflow-y-auto max-w-[1700px]">
        {/* Top Header Banner */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <span>🌾</span> SAR + MS Tarımsal Hasar Analiz Platformu
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Çoklu sensör uydu füzyonu, H3 uzamsal birikim ve meteorolojik afet değerlendirme sistemi.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleCleanStorage}
              disabled={isCleaning}
              className="px-3 py-1.5 rounded-xl border border-zinc-300 dark:border-zinc-800 bg-white dark:bg-zinc-900/80 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer disabled:opacity-50"
              title="Önbellek ve geçici dosyaları temizle"
            >
              <span>🧹</span>
              <span>{isCleaning ? "Temizleniyor..." : "Disk Temizliği"}</span>
            </button>
            <button
              onClick={() => handleResetAll(true)}
              className="px-3 py-1.5 rounded-xl border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-300 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
            >
              <span>🗑️</span>
              <span>Tümünü Sıfırla</span>
            </button>
          </div>
        </header>

        {/* Workspace: Map + Control Sidebar */}
        <section className="flex flex-col lg:flex-row gap-6 flex-1 min-h-[620px] items-stretch">
          {/* Map Area */}
          <div className="flex-1 min-h-[550px] rounded-2xl relative overflow-hidden border border-zinc-300 dark:border-zinc-800 shadow-xl">
            <MapComponent
              onPolygonChange={handlePolygonChange}
              gridFeatures={gridData}
              hotspotFeatures={hotspotData}
              clearKey={clearKey}
              isAnalyzing={isSaving || (activeJobId !== null && jobStatus === 'processing')}
              onResetAll={handleResetFromMap}
            />
          </div>

          {/* Form & Controls Panel */}
          <div className="w-full lg:w-96 flex flex-col gap-4 bg-white dark:bg-zinc-900/60 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800/80 shadow-lg backdrop-blur-md overflow-y-auto transition-colors">
            <div>
              <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <span>🎯</span> Yeni Analiz Başlat
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">Harita üzerinden parselinizi çizin ve afet tarihini seçin.</p>
            </div>

            <div className="space-y-3.5 mt-1">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Tarla / Alan Adı</label>
                <input
                  type="text"
                  value={aoiName}
                  onChange={(e) => setAoiName(e.target.value)}
                  placeholder="Örn: Manisa Buğday Parseli"
                  className="flex h-9 w-full rounded-xl border border-zinc-300 dark:border-zinc-700/80 bg-zinc-50 dark:bg-zinc-950 px-3 py-1.5 text-xs text-zinc-900 dark:text-zinc-200 placeholder:text-zinc-400 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Olay Tarihi (Afet)</label>
                <input
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="flex h-9 w-full rounded-xl border border-zinc-300 dark:border-zinc-700/80 bg-zinc-50 dark:bg-zinc-950 px-3 py-1.5 text-xs text-zinc-900 dark:text-zinc-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Seçili Alan (WKT)</label>
                  {areaHa > 0 && (
                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 font-mono">
                      {Math.round(areaHa).toLocaleString('tr-TR')} ha
                    </span>
                  )}
                </div>
                <textarea
                  readOnly
                  rows={2}
                  value={wkt || "Henüz alan çizilmedi..."}
                  className="flex w-full rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-950 px-3 py-1.5 text-[11px] text-zinc-600 dark:text-zinc-400 font-mono focus:outline-none resize-none"
                />
              </div>

              {/* Optional Weights Panel */}
              <div className="space-y-1 pt-1">
                <button
                  type="button"
                  onClick={() => setShowWeights(!showWeights)}
                  className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline font-semibold cursor-pointer"
                >
                  {showWeights ? "▲ Ağırlık Ayarlarını Gizle" : "▼ Füzyon Ağırlıklarını Ayarla (Opsiyonel)"}
                </button>

                {showWeights && (
                  <div className="grid grid-cols-2 gap-2 p-3 bg-zinc-100 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 rounded-xl mt-1 text-xs">
                    <div>
                      <label className="text-[10px] text-zinc-500 dark:text-zinc-400">SAR Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSar} onChange={e => setWeightSar(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-xs text-zinc-900 dark:text-zinc-200" />
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 dark:text-zinc-400">NDMI Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdmi} onChange={e => setWeightNdmi(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-xs text-zinc-900 dark:text-zinc-200" />
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 dark:text-zinc-400">NDRE Ağırlığı</label>
                      <input type="number" step="0.01" value={weightNdre} onChange={e => setWeightNdre(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-xs text-zinc-900 dark:text-zinc-200" />
                    </div>
                    <div>
                      <label className="text-[10px] text-zinc-500 dark:text-zinc-400">Yağış Ağırlığı</label>
                      <input type="number" step="0.01" value={weightPrecip} onChange={e => setWeightPrecip(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-xs text-zinc-900 dark:text-zinc-200" />
                    </div>
                    <div className="col-span-2">
                      <label className="text-[10px] text-zinc-500 dark:text-zinc-400">Toprak Nemi Ağırlığı</label>
                      <input type="number" step="0.01" value={weightSm} onChange={e => setWeightSm(parseFloat(e.target.value) || 0)} className="w-full h-7 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-xs text-zinc-900 dark:text-zinc-200" />
                    </div>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="pt-2">
                <button 
                  onClick={handleSave}
                  disabled={isSaving || !wkt || areaHa > MAX_AREA_HA || (activeJobId !== null && jobStatus !== 'done' && jobStatus !== 'failed')}
                  className="w-full h-11 inline-flex items-center justify-center rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-all shadow-lg shadow-emerald-950/20 disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                >
                  {isSaving ? "Analiz Başlatılıyor..." : "🚀 Analizi Başlat"}
                </button>
              </div>
            </div>

            {/* Pipeline Status Cards */}
            {activeJobId && (
              <div className="bg-zinc-100 dark:bg-zinc-950/80 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 space-y-2 mt-auto">
                <div className="flex items-center justify-between text-xs font-medium pb-2 border-b border-zinc-200 dark:border-zinc-800">
                  <span className="text-zinc-600 dark:text-zinc-400">İşlem Durumu</span>
                  <span className={`font-bold uppercase ${statusColor(jobStatus)}`}>
                    {jobStatus || "Bekleniyor"}
                  </span>
                </div>
                <PipelineRow label="Sentinel-1 SAR Radar" status={sarStatus} />
                <PipelineRow label="Sentinel-2 Optik (MS)" status={msStatus} />
                <PipelineRow label="ERA5 & Open-Meteo" status={weatherStatus} />
              </div>
            )}
          </div>
        </section>

        {/* 30-Day Meteorological Time Series Chart */}
        {activeJobId && summaryData && (
          <section className="mt-2">
            <TimeSeriesChart jobId={activeJobId} />
          </section>
        )}

        {/* Results & Statistical Dashboard */}
        {activeJobId && summaryData && (
          <section className="bg-white dark:bg-zinc-900/60 p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800/80 space-y-6 shadow-xl backdrop-blur-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
              <div>
                <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <span>📊</span> Hasar Değerlendirme & İstatistiksel Rapor
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">H3 Grid hücresel ayrıştırma ve çoklu sensör analiz sonuçları.</p>
              </div>
              <button
                onClick={() => setIsExportOpen(true)}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-emerald-950/30 transition-all cursor-pointer"
              >
                <span>📥</span>
                <span>Rapor & Çıktıları İndir</span>
              </button>
            </div>

            {/* Metric Overview Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 space-y-1">
                <span className="text-xs text-zinc-500 dark:text-zinc-400">Ortalama Hasar</span>
                <p className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  %{Math.round((summaryData.mean_damage_score || 0) * 100)}
                </p>
                <span className="text-[10px] text-zinc-500">Tüm Parsel Geneli</span>
              </div>
              <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 space-y-1">
                <span className="text-xs text-zinc-500 dark:text-zinc-400">Toplam Hücre</span>
                <p className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
                  {summaryData.total_cells || 0}
                </p>
                <span className="text-[10px] text-zinc-500">H3 Resolution 9</span>
              </div>
              <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 space-y-1">
                <span className="text-xs text-zinc-500 dark:text-zinc-400">🔥 Kritik Hotspot</span>
                <p className="text-2xl font-bold font-mono text-red-600 dark:text-red-400">
                  {summaryData.hotspot_cells_count || 0}
                </p>
                <span className="text-[10px] text-red-600/70 dark:text-red-400/70">Ağır Hasar Kümesi</span>
              </div>
              <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 space-y-1">
                <span className="text-xs text-zinc-500 dark:text-zinc-400">❄️ Soğuk Nokta</span>
                <p className="text-2xl font-bold font-mono text-blue-600 dark:text-blue-400">
                  {summaryData.coldspot_cells_count || 0}
                </p>
                <span className="text-[10px] text-blue-600/70 dark:text-blue-400/70">Sağlam Alan Kümesi</span>
              </div>
            </div>
          </section>
        )}

        {/* Export Modal */}
        {isExportOpen && activeJobId && (
          <ExportModal
            isOpen={isExportOpen}
            jobId={activeJobId}
            onClose={() => setIsExportOpen(false)}
          />
        )}
      </main>
    </div>
  );
}
