"use client"
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Polyline, Tooltip, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const vertexIcon = L.divIcon({
    className: 'bg-white border-[3px] border-red-500 rounded-full shadow-md cursor-grab active:cursor-grabbing',
    iconSize: [14, 14],
    iconAnchor: [7, 7]
});

// Helper component to invalidate Leaflet map size on container resize
function MapResizeHandler() {
    const map = useMap();
    useEffect(() => {
        const resizeObserver = new ResizeObserver(() => {
            map.invalidateSize();
        });
        const container = map.getContainer();
        if (container) {
            resizeObserver.observe(container);
        }
        return () => {
            resizeObserver.disconnect();
        };
    }, [map]);
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

// Area calculation
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

// Color helper for grid damage score
function getDamageColor(score: number) {
    if (score < 0.20) return { color: '#22c55e', label: 'Yok' };       // Green
    if (score < 0.45) return { color: '#eab308', label: 'Hafif' };     // Yellow
    if (score < 0.70) return { color: '#f97316', label: 'Orta' };      // Orange
    return { color: '#ef4444', label: 'Ağır' };                         // Red
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
        const newPoints: [number, number][] = [...points, [lat, lng]];
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
    const hotspotMap = React.useMemo(() => {
        const map: Record<string, any> = {};
        hotspotFeatures.forEach(h => {
            if (h.properties && h.properties.h3_index) {
                map[h.properties.h3_index] = h.properties;
            }
        });
        return map;
    }, [hotspotFeatures]);

    return (
        <div className="w-full h-full min-h-[550px] rounded-xl overflow-hidden border border-zinc-700/50 shadow-2xl relative bg-zinc-900 flex flex-col">
            {/* Drawing Toolbar */}
            <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2 bg-zinc-900/90 p-2.5 rounded-lg border border-zinc-700 shadow-lg backdrop-blur-sm">
                {!isDrawing && points.length === 0 && (
                    <button
                        onClick={handleStartDrawing}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded transition-colors shadow cursor-pointer"
                    >
                        🖊️ Yeni Çokgen Çiz
                    </button>
                )}
                {isDrawing && (
                    <div className="flex flex-col gap-2">
                        <span className="text-xs text-zinc-300 px-1">
                            Haritaya tıklayarak köşeleri seçin ({points.length} nokta)
                        </span>
                        <button
                            onClick={handleFinish}
                            disabled={points.length < 3}
                            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-zinc-600 disabled:cursor-not-allowed text-white text-sm font-medium rounded transition-colors shadow cursor-pointer"
                        >
                            ✅ Çizimi Bitir
                        </button>
                    </div>
                )}
                {points.length > 0 && (
                    <button
                        onClick={handleClear}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded transition-colors shadow cursor-pointer"
                    >
                        🗑️ Temizle
                    </button>
                )}

                {/* Live area feedback */}
                {points.length >= 3 && (
                    <div className={`px-2 py-1.5 rounded text-xs font-semibold border ${
                        areaTooLarge
                            ? 'bg-red-950/60 border-red-700 text-red-300'
                            : 'bg-green-950/60 border-green-800 text-green-300'
                    }`}>
                        📐 {areaHa.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ha
                        {areaTooLarge && (
                            <div className="mt-1 text-red-400 font-normal leading-tight">
                                ⚠️ Çok büyük!<br/>Önerilen maks: ~{MAX_AREA_HA.toLocaleString('tr-TR')} ha
                            </div>
                        )}
                    </div>
                )}

                {/* Grid Layer Toggle if results exist */}
                {gridFeatures.length > 0 && (
                    <div className="pt-2 border-t border-zinc-700/80 flex items-center justify-between gap-2">
                        <label className="text-xs text-zinc-300 flex items-center gap-1.5 cursor-pointer select-none">
                            <input
                                type="checkbox"
                                checked={showGridLayer}
                                onChange={(e) => setShowGridLayer(e.target.checked)}
                                className="rounded border-zinc-700 bg-zinc-800 text-blue-500 focus:ring-0 cursor-pointer"
                            />
                            <span>H3 Grid Katmanı ({gridFeatures.length})</span>
                        </label>
                    </div>
                )}
            </div>

            {/* Grid Legend Overlay if grid is active */}
            {gridFeatures.length > 0 && showGridLayer && (
                <div className="absolute bottom-4 left-4 z-[1000] bg-zinc-950/90 p-2.5 rounded-lg border border-zinc-800 shadow-xl backdrop-blur-sm text-[11px] space-y-1">
                    <p className="font-semibold text-zinc-300 pb-1 border-b border-zinc-800">H3 Hasar Dağılımı</p>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded bg-emerald-500 opacity-80 border border-emerald-400"></span>
                        <span className="text-zinc-400">Yok (&lt;%20)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded bg-yellow-500 opacity-80 border border-yellow-400"></span>
                        <span className="text-zinc-400">Hafif (%20 - %45)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded bg-orange-500 opacity-80 border border-orange-400"></span>
                        <span className="text-zinc-400">Orta (%45 - %70)</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded bg-red-500 opacity-80 border border-red-400"></span>
                        <span className="text-zinc-400">Ağır (&gt;%70)</span>
                    </div>
                    <div className="flex items-center gap-2 pt-1 border-t border-zinc-800/80">
                        <span className="w-3 h-3 rounded border-2 border-red-500 bg-red-950"></span>
                        <span className="text-red-400 font-medium">🔥 Hotspot Kümesi</span>
                    </div>
                </div>
            )}

            <div className="flex-1 w-full h-full min-h-[550px] relative">
                <MapContainer
                    center={[39.0, 35.0]}
                    zoom={6}
                    style={{ height: '100%', width: '100%', position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
                    attributionControl={false}
                >
                    <MapResizeHandler />
                    <TileLayer
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                        maxZoom={18}
                    />

                    <DrawingHandler isDrawing={isDrawing} onMapClick={handleMapClick} />

                    {/* Render polygon when 3+ points */}
                    {points.length >= 3 && (
                        <Polygon
                            positions={points}
                            pathOptions={{
                                color: areaTooLarge ? '#ef4444' : '#3b82f6',
                                fillColor: areaTooLarge ? '#ef4444' : '#3b82f6',
                                fillOpacity: 0.15,
                                weight: 2,
                            }}
                        />
                    )}

                    {/* Render lines between points */}
                    {points.length >= 2 && (
                        <Polyline
                            positions={[...points, points[0]]}
                            pathOptions={{
                                color: areaTooLarge ? '#ef4444' : '#3b82f6',
                                weight: 2,
                                dashArray: points.length < 3 ? '5, 10' : undefined,
                            }}
                        />
                    )}

                    {/* Render vertex markers */}
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

                    {/* Render H3 Hexagonal Grid Cells & Hotspots */}
                    {showGridLayer && gridFeatures.map((feat, idx) => {
                        if (!feat.geometry || !feat.geometry.coordinates) return null;
                        
                        // GeoJSON Polygon coordinates are [lng, lat], Leaflet expects [lat, lng]
                        const coords = feat.geometry.coordinates[0].map(([lng, lat]: [number, number]) => [lat, lng]);
                        const score = feat.properties.damage_score || 0;
                        const damageInfo = getDamageColor(score);
                        
                        const h3Idx = feat.properties.h3_index;
                        const hs = hotspotMap[h3Idx];
                        const isHotspot = hs && hs.classification && hs.classification.includes('Hotspot');

                        return (
                            <Polygon
                                key={idx}
                                positions={coords}
                                pathOptions={{
                                    color: isHotspot ? '#dc2626' : damageInfo.color,
                                    fillColor: damageInfo.color,
                                    fillOpacity: isHotspot ? 0.75 : 0.45,
                                    weight: isHotspot ? 3 : 1.2,
                                }}
                            >
                                <Tooltip sticky>
                                    <div className="text-xs space-y-1 p-1">
                                        <p className="font-mono font-bold text-zinc-900">{h3Idx}</p>
                                        <p className="text-zinc-700">Hasar Skoru: <span className="font-bold">%{Math.round(score * 100)}</span> ({damageInfo.label})</p>
                                        {hs && (
                                            <p className={`font-semibold ${isHotspot ? 'text-red-600' : 'text-zinc-600'}`}>
                                                {isHotspot ? '🔥 ' : ''}{hs.classification}
                                            </p>
                                        )}
                                    </div>
                                </Tooltip>
                            </Polygon>
                        );
                    })}
                </MapContainer>
            </div>
        </div>
    );
}
