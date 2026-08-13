"use client"
import React, { useState } from 'react';
import MapComponent from '@/components/Map';
import { toast } from 'sonner';

export default function HomePage() {
  const [wkt, setWkt] = useState<string | null>(null);
  const [aoiName, setAoiName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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

    setIsSaving(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/aoi/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: aoiName,
          geometry: wkt
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Kayıt işlemi başarısız oldu.");
      }

      const data = await response.json();
      toast.success("AOI başarıyla kaydedildi! ID: " + data.id);
      console.log("Saved AOI:", data);
      
      // Reset form
      setAoiName("");
      // Ideally we should also clear the drawn polygon on the map here, 
      // but for MVP this is enough.
    } catch (error: any) {
      toast.error(error.message);
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

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
              <h2 className="text-2xl font-semibold tracking-tight">Yeni AOI Oluştur</h2>
              <p className="text-sm text-muted-foreground mt-1">Harita üzerinden analiz edilecek tarlayı çokgen aracı ile çizin.</p>
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
                <label className="text-sm font-medium">Seçili Alan (WKT)</label>
                <textarea 
                  readOnly 
                  value={wkt || "Henüz alan çizilmedi..."}
                  className="flex min-h-[80px] w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-400 focus:outline-none"
                />
              </div>

              <button 
                onClick={handleSave}
                disabled={isSaving || !wkt}
                className="w-full h-10 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none"
              >
                {isSaving ? "Kaydediliyor..." : "Tarlayı Kaydet"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
