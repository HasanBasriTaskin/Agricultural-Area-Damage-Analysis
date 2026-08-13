"use client"
import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { toast } from 'sonner';

export default function HomePage() {
  const [wkt, setWkt] = useState<string | null>(null);
  const [aoiName, setAoiName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);

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

  const handlePolygonChange = (newWkt: string | null) => {
    setWkt(newWkt);
  };

  const handleSave = async () => {
    if (!wkt) {
      toast.error("Lütfen haritada bir alan (AOI) çizin.");
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
        })
      });

      if (!jobResponse.ok) throw new Error("Analiz işi başlatılamadı.");
      const jobData = await jobResponse.json();
      
      setActiveJobId(jobData.id);
      setJobStatus(jobData.status);
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
          if (data.status === "done") {
            toast.success("Analiz tamamlandı!");
          } else if (data.status === "failed") {
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

        <section className="flex flex-col md:flex-row gap-6 flex-1 min-h-[600px]">
          {/* Map Area */}
          <div className="flex-1 rounded-xl relative">
             <MapComponent onPolygonChange={handlePolygonChange} />
          </div>

          {/* Sidebar / Form */}
          <div className="w-full md:w-96 flex flex-col gap-4 bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
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

              <button 
                onClick={handleSave}
                disabled={isSaving || !wkt || activeJobId !== null}
                className="w-full h-10 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none"
              >
                {isSaving ? "İşleniyor..." : "Analizi Başlat"}
              </button>

              {/* Status Tracking */}
              {activeJobId && (
                <div className="mt-6 p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                  <h3 className="text-sm font-medium text-zinc-400 mb-2">İşlem Durumu</h3>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-white uppercase tracking-wider">
                      {jobStatus || "BİLİNMİYOR"}
                    </span>
                    {jobStatus !== "done" && jobStatus !== "failed" && (
                      <span className="flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-3 w-3 rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 mt-2 truncate" title={activeJobId}>
                    ID: {activeJobId}
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
