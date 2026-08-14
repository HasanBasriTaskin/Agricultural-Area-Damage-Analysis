"use client";
import React, { useState } from 'react';
import { toast } from 'sonner';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
}

export default function ExportModal({ isOpen, onClose, jobId }: ExportModalProps) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [rasterLayer, setRasterLayer] = useState<string>("fusion");

  if (!isOpen) return null;

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleDownload = async (type: string, url: string, filename: string) => {
    setDownloading(type);
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`İndirme başarısız (${response.status})`);
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success(`${filename} başarıyla indirildi!`);
    } catch (err: any) {
      toast.error(err.message || "Dosya indirilirken bir hata oluştu.");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-100">Dışa Aktarma & Raporlama Merkezi</h3>
              <p className="text-xs text-zinc-400">Analiz sonuçlarını farklı CBS, tablo ve rapor formatlarında indirin</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 p-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Primary Action: Official PDF Report */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-red-950/40 via-zinc-900 to-zinc-900 border border-red-500/30 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 uppercase">Resmi Belge</span>
                <h4 className="text-sm font-semibold text-zinc-100">Resmi Tarımsal Hasar Tespit Raporu (PDF)</h4>
              </div>
              <p className="text-xs text-zinc-400">A4 formatında, meteoroloji tablolu, grafikli ve ıslak imza onay alanlı rapor.</p>
            </div>
            <button
              onClick={() => handleDownload('pdf', `${apiUrl}/api/v1/jobs/${jobId}/export/pdf`, `hasar_raporu_${jobId.slice(0, 8)}.pdf`)}
              disabled={downloading === 'pdf'}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-xs transition-all shadow-lg shadow-red-900/20 disabled:opacity-50 shrink-0"
            >
              {downloading === 'pdf' ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Hazırlanıyor...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  PDF İndir
                </>
              )}
            </button>
          </div>

          {/* Raster & Spatial Formats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* GeoTIFF */}
            <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-400">Raster (GeoTIFF)</span>
                  <span className="text-[10px] text-zinc-500 font-mono">.TIF</span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">QGIS ve ArcGIS için 10m çözünürlüklü uydu piksel hasar matrisi.</p>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <select
                  value={rasterLayer}
                  onChange={(e) => setRasterLayer(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 text-xs rounded-lg px-2 py-1.5 text-zinc-200 focus:outline-none"
                >
                  <option value="fusion">Füzyon Skoru</option>
                  <option value="sar">Sentinel-1 (SAR)</option>
                  <option value="ms">Sentinel-2 (MS)</option>
                </select>
                <button
                  onClick={() => handleDownload('geotiff', `${apiUrl}/api/v1/jobs/${jobId}/export/geotiff?layer=${rasterLayer}`, `${rasterLayer}_${jobId.slice(0, 8)}.tif`)}
                  disabled={downloading === 'geotiff'}
                  className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium border border-zinc-700 transition-colors disabled:opacity-50 text-center"
                >
                  {downloading === 'geotiff' ? 'İndiriliyor...' : 'GeoTIFF İndir'}
                </button>
              </div>
            </div>

            {/* GeoJSON */}
            <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-blue-400">Vektör (GeoJSON)</span>
                  <span className="text-[10px] text-zinc-500 font-mono">.GEOJSON</span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">Web CBS ve Leaflet uyumlu H3 petekleri ve hasar öznitelikleri.</p>
              </div>
              <button
                onClick={() => handleDownload('geojson', `${apiUrl}/api/v1/jobs/${jobId}/export/geojson`, `hasar_grid_${jobId.slice(0, 8)}.geojson`)}
                disabled={downloading === 'geojson'}
                className="w-full px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {downloading === 'geojson' ? 'İndiriliyor...' : 'GeoJSON İndir'}
              </button>
            </div>

            {/* Shapefile */}
            <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-amber-400">ESRI Shapefile (.zip)</span>
                  <span className="text-[10px] text-zinc-500 font-mono">.ZIP</span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">Standart CBS yazılımları için .shp, .shx, .dbf, .prj arşiv paketi.</p>
              </div>
              <button
                onClick={() => handleDownload('shapefile', `${apiUrl}/api/v1/jobs/${jobId}/export/shapefile`, `hasar_shapefile_${jobId.slice(0, 8)}.zip`)}
                disabled={downloading === 'shapefile'}
                className="w-full px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {downloading === 'shapefile' ? 'İndiriliyor...' : 'Shapefile (.zip) İndir'}
              </button>
            </div>

            {/* GeoPackage */}
            <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-purple-400">OGC GeoPackage</span>
                  <span className="text-[10px] text-zinc-500 font-mono">.GPKG</span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">Tek dosya SQLite formatında H3 hücreleri ve Hotspot katmanları.</p>
              </div>
              <button
                onClick={() => handleDownload('geopackage', `${apiUrl}/api/v1/jobs/${jobId}/export/geopackage`, `hasar_geopackage_${jobId.slice(0, 8)}.gpkg`)}
                disabled={downloading === 'geopackage'}
                className="w-full px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-medium transition-colors disabled:opacity-50"
              >
                {downloading === 'geopackage' ? 'İndiriliyor...' : 'GeoPackage (.gpkg) İndir'}
              </button>
            </div>
          </div>

          {/* CSV Tabular */}
          <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-zinc-200">Excel & Tablo Verisi (CSV)</span>
                <span className="text-[10px] text-zinc-500 font-mono">.CSV</span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5">Tüm H3 peteklerinin enlem/boylam, hasar puanı ve z/p istatistikleri.</p>
            </div>
            <button
              onClick={() => handleDownload('csv', `${apiUrl}/api/v1/jobs/${jobId}/export/csv`, `hasar_verileri_${jobId.slice(0, 8)}.csv`)}
              disabled={downloading === 'csv'}
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium border border-zinc-700 transition-colors disabled:opacity-50 shrink-0"
            >
              {downloading === 'csv' ? 'İndiriliyor...' : 'CSV İndir'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-950/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          >
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
}
