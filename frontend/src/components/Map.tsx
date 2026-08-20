"use client";
import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Tooltip, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { insertPointIntoPolygon } from '@/lib/polygonUtils';

const vertexIcon = L.divIcon({
    className: 'bg-white border-[3px] border-red-500 rounded-full shadow-md cursor-grab active:cursor-grabbing',
    iconSize: [14, 14],
    iconAnchor: [7, 7]
});

// Helper component to invalidate Leaflet map size on container mount & resize
function MapResizeHandler() {
    const map = useMap();
    useEffect(() => {
        const timer = setTimeout(() => {
            map.invalidateSize();
        }, 150);

        const resizeObserver = new ResizeObserver(() => {
            map.invalidateSize();
        });
        const container = map.getContainer();
        if (container) {
            resizeObserver.observe(container);
        }
        return () => {
            clearTimeout(timer);
            resizeObserver.disconnect();
        };
    }, [map]);
    return null;
}

// Helper component to automatically zoom and fit bounds to AOI polygon and H3 grid cells
function FitBoundsHandler({ gridFeatures, points }: { gridFeatures?: any[]; points?: [number, number][] }) {
    const map = useMap();
    useEffect(() => {
        if (points && points.length >= 3) {
            const bounds = L.latLngBounds(points);
            map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
        } else if (gridFeatures && gridFeatures.length > 0) {
            const latlngs: [number, number][] = [];
            gridFeatures.forEach((f: any) => {
                if (f.geometry && f.geometry.coordinates) {
                    const coords = f.geometry.coordinates[0];
                    coords.forEach((pt: [number, number]) => {
                        // GeoJSON is [lng, lat], Leaflet is [lat, lng]
                        latlngs.push([pt[1], pt[0]]);
                    });
                }
            });
            if (latlngs.length > 0) {
                const bounds = L.latLngBounds(latlngs);
                map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
            }
        }
    }, [gridFeatures, points, map]);
    return null;
}

// GeoJSON to WKT Polygon converter
function coordsToWkt(coordinates: [number, number][]): string | null {
    if (coordinates.length < 3) return null;
    const ring = [...coordinates];
    if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
        ring.push([...ring[0]] as [number, number]);
    }
    const points = ring.map((p) => `${p[1]} ${p[0]}`).join(', ');
    return `POLYGON((${points}))`;
}

// Area calculation in hectares
function calcAreaHa(coordinates: [number, number][]): number {
    if (coordinates.length < 3) return 0;
    const R = 6371000;
    const toRad = (d: number) => d * Math.PI / 180;
    const avgLat = coordinates.reduce((s, p) => s + p[0], 0) / coordinates.length;
    const latM = toRad(1) * R;
    const lngM = toRad(1) * R * Math.cos(toRad(avgLat));
    let area = 0;
    const n = coordinates.length;
    for (let i = 0; i < n; i++) {
        const [lat1, lng1] = coordinates[i];
        const [lat2, lng2] = coordinates[(i + 1) % n];
        area += (lng1 * lngM) * (lat2 * latM) - (lng2 * lngM) * (lat1 * latM);
    }
    return Math.abs(area / 2) / 10000;
}

const MAX_AREA_HA = 25000;

export type SpectralMode = 'fusion' | 'ndmi' | 'ndre' | 'sar' | 'hotspot_only';

interface MapComponentProps {
    onPolygonChange: (wkt: string | null, areaHa?: number) => void;
    gridFeatures?: any[];
    hotspotFeatures?: any[];
    clearKey?: number;
    isAnalyzing?: boolean;
    onResetAll?: () => void;
}

function DrawingHandler({
    isDrawing,
    onMapClick,
}: {
    isDrawing: boolean;
    onMapClick: (lat: number, lng: number) => void;
}) {
    useMapEvents({
        click(e) {
            if (isDrawing) {
                onMapClick(e.latlng.lat, e.latlng.lng);
            }
        },
    });
    return null;
}

// Spectral Mode Colormap Helper
function getSpectralColor(score: number, mode: SpectralMode) {
    if (mode === 'ndmi') {
        if (score < 0.20) return { color: '#0ea5e9', label: 'Nemli / Sağlam' };
        if (score < 0.45) return { color: '#eab308', label: 'Hafif Nem Kaybı' };
        if (score < 0.70) return { color: '#f97316', label: 'Orta Nem Stresi' };
        return { color: '#dc2626', label: 'Aşırı Su Kaybı' };
    }
    if (mode === 'ndre') {
        if (score < 0.20) return { color: '#16a34a', label: 'Klorofil Yüksek' };
        if (score < 0.45) return { color: '#f59e0b', label: 'Hafif Klorofil Düşüşü' };
        if (score < 0.70) return { color: '#ea580c', label: 'Orta Doku Hasarı' };
        return { color: '#b91c1c', label: 'Ağır Nekroz' };
    }
    if (mode === 'sar') {
        if (score < 0.20) return { color: '#64748b', label: 'Stabil Radar' };
        if (score < 0.45) return { color: '#8b5cf6', label: 'Hafif Geri Saçılım' };
        if (score < 0.70) return { color: '#d946ef', label: 'Orta Yapı Değişimi' };
        return { color: '#f43f5e', label: 'Ağır Yapısal Hasar' };
    }
    // Default Fusion
    if (score < 0.20) return { color: '#22c55e', label: 'Yok (<%20)' };
    if (score < 0.45) return { color: '#eab308', label: 'Hafif (%20-%45)' };
    if (score < 0.70) return { color: '#f97316', label: 'Orta (%45-%70)' };
    return { color: '#ef4444', label: 'Ağır (>%70)' };
}

export default function MapComponent({
    onPolygonChange,
    gridFeatures = [],
    hotspotFeatures = [],
    clearKey = 0,
    isAnalyzing = false,
    onResetAll
}: MapComponentProps) {
    const [isDrawing, setIsDrawing] = useState(false);
    const [points, setPoints] = useState<[number, number][]>([]);
    const [showGridLayer, setShowGridLayer] = useState(true);
    const [spectralMode, setSpectralMode] = useState<SpectralMode>('fusion');
    const [gridOpacity, setGridOpacity] = useState<number>(0.65);
    const [baseMap, setBaseMap] = useState<'esri' | 'dark' | 'osm'>('esri');
    const [isSwipeMode, setIsSwipeMode] = useState(false);
    const [swipePos, setSwipePos] = useState<number>(50); // 0-100 percentage

    useEffect(() => {
        if (clearKey > 0) {
            setIsDrawing(false);
            setPoints([]);
        }
    }, [clearKey]);

    useEffect(() => {
        if (isAnalyzing) {
            setIsDrawing(false);
        }
    }, [isAnalyzing]);

    const handleMapClick = (lat: number, lng: number) => {
        const newPoints = insertPointIntoPolygon(points, [lat, lng]);
        setPoints(newPoints);

        if (newPoints.length >= 3) {
            const ha = calcAreaHa(newPoints);
            onPolygonChange(coordsToWkt(newPoints), ha);
        } else {
            onPolygonChange(null, 0);
        }
    };

    const handleStartDrawing = () => {
        setIsDrawing(true);
        setPoints([]);
        onPolygonChange(null, 0);
    };

    const handleFinish = () => {
        setIsDrawing(false);
    };

    const handleClear = () => {
        setIsDrawing(false);
        setPoints([]);
        onPolygonChange(null, 0);
        if (onResetAll) {
            onResetAll();
        }
    };

    const areaHa = points.length >= 3 ? calcAreaHa(points) : 0;
    const areaTooLarge = areaHa > MAX_AREA_HA;

    // Build map of hotspot classifications
    const hotspotMap = useMemo(() => {
        const map: Record<string, any> = {};
        hotspotFeatures.forEach(h => {
            if (h.properties && h.properties.h3_index) {
                map[h.properties.h3_index] = h.properties;
            }
        });
        return map;
    }, [hotspotFeatures]);

    // Calculate longitudes for swipe filtering
    const minMaxLng = useMemo(() => {
        if (gridFeatures.length === 0) return { min: 0, max: 0 };
        let min = 180, max = -180;
        gridFeatures.forEach(f => {
            if (f.geometry && f.geometry.coordinates) {
                const coords = f.geometry.coordinates[0];
                coords.forEach((pt: [number, number]) => {
                    min = Math.min(min, pt[0]);
                    max = Math.max(max, pt[0]);
                });
            }
        });
        return { min, max };
    }, [gridFeatures]);

    const swipeThresholdLng = minMaxLng.min + (minMaxLng.max - minMaxLng.min) * (swipePos / 100.0);

    return (
        <div className="w-full h-full min-h-[550px] rounded-xl overflow-hidden border border-zinc-700/50 shadow-2xl relative bg-zinc-900">
            {/* Left Drawing Toolbar */}
            <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2 bg-zinc-900/90 p-2.5 rounded-xl border border-zinc-700 shadow-xl backdrop-blur-md">
                {!isDrawing && points.length === 0 && (
                    <button
                        onClick={handleStartDrawing}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors shadow cursor-pointer flex items-center gap-1.5"
                    >
                        <span>🖊️</span> Yeni Çokgen Çiz
                    </button>
                )}
                {isDrawing && (
                    <div className="flex flex-col gap-2">
                        <span className="text-[11px] text-zinc-300 px-1">
                            Haritaya tıklayarak köşeleri seçin ({points.length} nokta)
                        </span>
                        <button
                            onClick={handleFinish}
                            disabled={points.length < 3}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-600 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg transition-colors shadow cursor-pointer flex items-center justify-center gap-1"
                        >
                            <span>✅</span> Çizimi Bitir
                        </button>
                    </div>
                )}
                {points.length > 0 && (
                    <button
                        onClick={handleClear}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg transition-colors shadow cursor-pointer flex items-center justify-center gap-1"
                    >
                        <span>🗑️</span> Temizle
                    </button>
                )}

                {/* Live area feedback */}
                {points.length >= 3 && (
                    <div className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border ${
                        areaTooLarge
                            ? 'bg-red-950/60 border-red-700 text-red-300'
                            : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                    }`}>
                        📐 {areaHa.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ha
                        {areaTooLarge && (
                            <div className="mt-1 text-red-400 font-normal leading-tight text-[10px]">
                                ⚠️ Alan çok büyük!<br/>Maks: ~{MAX_AREA_HA.toLocaleString('tr-TR')} ha
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Right Multi-Layer & Swipe Controller (Sprint 8) */}
            {gridFeatures.length > 0 && (
                <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2 bg-zinc-950/90 p-3 rounded-xl border border-zinc-800 shadow-2xl backdrop-blur-md max-w-xs text-xs space-y-2">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <span className="font-bold text-zinc-100 flex items-center gap-1.5">
                            <span>🛰️</span> Spektral Katmanlar
                        </span>
                        <button
                            onClick={() => setIsSwipeMode(!isSwipeMode)}
                            className={`px-2 py-1 rounded text-[10px] font-bold transition-all flex items-center gap-1 cursor-pointer ${
                                isSwipeMode
                                    ? 'bg-emerald-500 text-zinc-950 shadow-md shadow-emerald-500/30'
                                    : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
                            }`}
                            title="Afet öncesi ve sonrası dikey perde karşılaştırması"
                        >
                            <span>🪟</span> {isSwipeMode ? "Swipe Açık" : "Swipe (Perde)"}
                        </button>
                    </div>

                    {/* Spectral Mode Selector */}
                    <div className="space-y-1">
                        <label className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider">İndeks / Sensör</label>
                        <div className="grid grid-cols-2 gap-1.5">
                            <button
                                onClick={() => setSpectralMode('fusion')}
                                className={`px-2 py-1.5 rounded text-[11px] font-medium transition-all text-left truncate cursor-pointer ${
                                    spectralMode === 'fusion'
                                        ? 'bg-blue-600 text-white font-semibold shadow-sm'
                                        : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'
                                }`}
                            >
                                🎯 Füzyon Skoru
                            </button>
                            <button
                                onClick={() => setSpectralMode('ndmi')}
                                className={`px-2 py-1.5 rounded text-[11px] font-medium transition-all text-left truncate cursor-pointer ${
                                    spectralMode === 'ndmi'
                                        ? 'bg-cyan-600 text-white font-semibold shadow-sm'
                                        : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'
                                }`}
                            >
                                💧 ΔNDMI (Nem)
                            </button>
                            <button
                                onClick={() => setSpectralMode('ndre')}
                                className={`px-2 py-1.5 rounded text-[11px] font-medium transition-all text-left truncate cursor-pointer ${
                                    spectralMode === 'ndre'
                                        ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                                        : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'
                                }`}
                            >
                                🌿 ΔNDRE (Klorofil)
                            </button>
                            <button
                                onClick={() => setSpectralMode('sar')}
                                className={`px-2 py-1.5 rounded text-[11px] font-medium transition-all text-left truncate cursor-pointer ${
                                    spectralMode === 'sar'
                                        ? 'bg-purple-600 text-white font-semibold shadow-sm'
                                        : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-800'
                                }`}
                            >
                                📡 SAR Radar
                            </button>
                        </div>
                    </div>

                    {/* Opacity Slider */}
                    <div className="space-y-1 pt-1 border-t border-zinc-800">
                        <div className="flex items-center justify-between text-[10px] text-zinc-400 font-semibold">
                            <span>Katman Şeffaflığı</span>
                            <span className="font-mono text-zinc-200">%{Math.round(gridOpacity * 100)}</span>
                        </div>
                        <input
                            type="range"
                            min="0.2"
                            max="1.0"
                            step="0.05"
                            value={gridOpacity}
                            onChange={(e) => setGridOpacity(parseFloat(e.target.value))}
                            className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                    </div>

                    {/* Base Map Selector */}
                    <div className="flex items-center justify-between pt-1 border-t border-zinc-800 text-[10px]">
                        <span className="text-zinc-400 font-semibold">Altlık:</span>
                        <div className="flex gap-1">
                            <button
                                onClick={() => setBaseMap('esri')}
                                className={`px-1.5 py-0.5 rounded ${baseMap === 'esri' ? 'bg-blue-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400'}`}
                            >
                                Uydu
                            </button>
                            <button
                                onClick={() => setBaseMap('dark')}
                                className={`px-1.5 py-0.5 rounded ${baseMap === 'dark' ? 'bg-blue-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400'}`}
                            >
                                Koyu
                            </button>
                            <button
                                onClick={() => setBaseMap('osm')}
                                className={`px-1.5 py-0.5 rounded ${baseMap === 'osm' ? 'bg-blue-600 text-white font-bold' : 'bg-zinc-900 text-zinc-400'}`}
                            >
                                Sokak
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Swipe Interactive Bar & Overlay Banner (Sprint 8) */}
            {gridFeatures.length > 0 && isSwipeMode && (
                <>
                    {/* Vertical Dividing Laser Line on Map Canvas */}
                    <div
                        className="absolute top-0 bottom-0 z-[990] pointer-events-none transition-all duration-75 flex items-center justify-center"
                        style={{ left: `${swipePos}%` }}
                    >
                        <div className="w-[2px] h-full bg-white shadow-[0_0_10px_#38bdf8,0_0_20px_#ffffff] relative">
                            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 bg-zinc-950/95 border-2 border-white rounded-full flex items-center justify-center shadow-2xl text-xs font-bold text-white backdrop-blur-md">
                                ⇄
                            </div>
                        </div>
                    </div>

                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[1000] w-11/12 max-w-md bg-zinc-950/95 p-3 rounded-2xl border border-zinc-700 shadow-2xl backdrop-blur-md space-y-2">
                        <div className="flex items-center justify-between text-xs font-bold">
                            <span className="text-sky-400 flex items-center gap-1">
                                <span>⬅️</span> Afet Öncesi (Doğal Uydu)
                            </span>
                            <span className="text-red-400 flex items-center gap-1">
                                Hasar Katmanı <span>➡️</span>
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={swipePos}
                            onChange={(e) => setSwipePos(parseInt(e.target.value))}
                            className="w-full h-2 bg-gradient-to-r from-sky-500 via-zinc-600 to-red-500 rounded-lg appearance-none cursor-pointer accent-white"
                        />
                        <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                            <span>%0 (Tam Uydu)</span>
                            <span className="font-bold text-zinc-200">Perde: %{swipePos}</span>
                            <span>%100 (Tam Hasar)</span>
                        </div>
                    </div>
                </>
            )}

            {/* Grid Legend Overlay */}
            {gridFeatures.length > 0 && showGridLayer && !isSwipeMode && (
                <div className="absolute bottom-4 left-4 z-[1000] bg-zinc-950/90 p-3 rounded-xl border border-zinc-800 shadow-2xl backdrop-blur-md text-[11px] space-y-1.5">
                    <p className="font-bold text-zinc-200 pb-1 border-b border-zinc-800 flex items-center gap-1.5">
                        <span>📊</span> {spectralMode === 'ndmi' ? 'ΔNDMI Nem Skalası' : spectralMode === 'ndre' ? 'ΔNDRE Klorofil Skalası' : spectralMode === 'sar' ? 'SAR Radar Skalası' : 'H3 Hasar Dağılımı'}
                    </p>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded" style={{ backgroundColor: getSpectralColor(0.1, spectralMode).color }}></span>
                        <span className="text-zinc-300">{getSpectralColor(0.1, spectralMode).label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded" style={{ backgroundColor: getSpectralColor(0.35, spectralMode).color }}></span>
                        <span className="text-zinc-300">{getSpectralColor(0.35, spectralMode).label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded" style={{ backgroundColor: getSpectralColor(0.55, spectralMode).color }}></span>
                        <span className="text-zinc-300">{getSpectralColor(0.55, spectralMode).label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded" style={{ backgroundColor: getSpectralColor(0.85, spectralMode).color }}></span>
                        <span className="text-zinc-300">{getSpectralColor(0.85, spectralMode).label}</span>
                    </div>
                    <div className="flex items-center gap-2 pt-1 border-t border-zinc-800/80">
                        <span className="w-3 h-3 rounded border-2 border-red-500 bg-red-500/30 animate-pulse"></span>
                        <span className="text-red-300 font-semibold">🔥 Hotspot Kümesi</span>
                    </div>
                </div>
            )}

            {/* Leaflet Map Canvas */}
            <MapContainer
                center={[39.0, 35.0]}
                zoom={6}
                scrollWheelZoom={true}
                className="w-full h-full z-0"
                style={{ height: "100%", width: "100%", minHeight: "550px" }}
            >
                <MapResizeHandler />
                <FitBoundsHandler gridFeatures={gridFeatures} points={points} />

                {/* Dynamic Base Tile Layer */}
                {baseMap === 'esri' && (
                    <TileLayer
                        attribution='&copy; <a href="https://www.esri.com">Esri</a> World Imagery'
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                        maxZoom={19}
                    />
                )}
                {baseMap === 'dark' && (
                    <TileLayer
                        attribution='&copy; <a href="https://carto.com">CARTO</a> Dark Matter'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                        maxZoom={19}
                    />
                )}
                {baseMap === 'osm' && (
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        maxZoom={19}
                    />
                )}

                <DrawingHandler isDrawing={isDrawing} onMapClick={handleMapClick} />

                {/* Drawn Polygon Preview */}
                {points.length >= 3 && (
                    <Polygon
                        positions={points}
                        pathOptions={{
                            color: areaTooLarge ? '#ef4444' : '#38bdf8',
                            fillColor: areaTooLarge ? '#ef4444' : '#38bdf8',
                            fillOpacity: 0.25,
                            weight: 2.5,
                            dashArray: '6, 6'
                        }}
                    />
                )}

                {/* Drawing Vertices Markers */}
                {points.map((pos, idx) => (
                    <Marker
                        key={idx}
                        position={pos}
                        icon={vertexIcon}
                        draggable={!isDrawing}
                        eventHandlers={{
                            drag: (e) => {
                                const latlng = e.target.getLatLng();
                                setPoints(prev => {
                                    const newPts = [...prev];
                                    newPts[idx] = [latlng.lat, latlng.lng];
                                    return newPts;
                                });
                            },
                            dragend: (e) => {
                                const latlng = e.target.getLatLng();
                                const newPts = [...points];
                                newPts[idx] = [latlng.lat, latlng.lng];
                                if (newPts.length >= 3) {
                                    const ha = calcAreaHa(newPts);
                                    onPolygonChange(coordsToWkt(newPts), ha);
                                }
                            }
                        }}
                    />
                ))}

                {/* H3 Hexagonal Grid Features */}
                {showGridLayer && gridFeatures.map((f, idx) => {
                    if (!f.geometry || !f.geometry.coordinates) return null;
                    const ring = f.geometry.coordinates[0];
                    const positions: [number, number][] = ring.map((pt: [number, number]) => [pt[1], pt[0]]);
                    const centroidLng = ring.reduce((sum: number, pt: [number, number]) => sum + pt[0], 0) / ring.length;

                    // Swipe Curtain Filtering (Hide cells on the left side of the curtain if swipe is active)
                    if (isSwipeMode && centroidLng < swipeThresholdLng) {
                        return null;
                    }

                    const score = f.properties.damage_score || 0;
                    const h3Idx = f.properties.h3_index;
                    const spectralInfo = getSpectralColor(score, spectralMode);

                    // Hotspot Check
                    const hsProp = hotspotMap[h3Idx];
                    const isHotspot = hsProp && hsProp.classification && hsProp.classification.includes("Hotspot");
                    const isColdspot = hsProp && hsProp.classification && hsProp.classification.includes("Coldspot");

                    let strokeColor = '#ffffff';
                    let strokeWidth = 0.8;
                    let fillOpacity = gridOpacity;

                    if (isHotspot) {
                        strokeColor = '#ef4444';
                        strokeWidth = 2.8;
                        fillOpacity = Math.min(1.0, gridOpacity + 0.15);
                    } else if (isColdspot) {
                        strokeColor = '#10b981';
                        strokeWidth = 2.0;
                    }

                    return (
                        <Polygon
                            key={idx}
                            positions={positions}
                            pathOptions={{
                                color: strokeColor,
                                fillColor: spectralInfo.color,
                                fillOpacity: fillOpacity,
                                weight: strokeWidth
                            }}
                        >
                            <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                                <div className="text-xs space-y-1 bg-zinc-900/95 text-zinc-100 p-2.5 rounded-lg border border-zinc-700 shadow-2xl">
                                    <div className="flex items-center justify-between gap-3 border-b border-zinc-700 pb-1">
                                        <span className="font-mono text-[10px] text-zinc-400">{h3Idx}</span>
                                        {isHotspot && (
                                            <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-bold text-[10px]">
                                                🔥 Hotspot
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex justify-between gap-4 font-semibold">
                                        <span>Hasar Skoru:</span>
                                        <span className="text-amber-400 font-mono">%{Math.round(score * 100)}</span>
                                    </div>
                                    <div className="flex justify-between gap-4 text-zinc-400 text-[10px]">
                                        <span>Sınıf:</span>
                                        <span className="font-medium text-zinc-200">{spectralInfo.label}</span>
                                    </div>
                                    {hsProp && (
                                        <div className="flex justify-between gap-4 text-zinc-400 text-[10px]">
                                            <span>Z-Skoru:</span>
                                            <span className="font-mono text-zinc-300">{Number(hsProp.intensity_z_score).toFixed(2)}</span>
                                        </div>
                                    )}
                                </div>
                            </Tooltip>
                        </Polygon>
                    );
                })}
            </MapContainer>
        </div>
    );
}
