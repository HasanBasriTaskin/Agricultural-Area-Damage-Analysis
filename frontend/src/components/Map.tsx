"use client"
import React, { useState } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const vertexIcon = L.divIcon({
    className: 'bg-white border-[3px] border-red-500 rounded-full shadow-md cursor-grab active:cursor-grabbing',
    iconSize: [14, 14],
    iconAnchor: [7, 7]
});

// GeoJSON to WKT Polygon converter
function coordsToWkt(coordinates: [number, number][]): string | null {
    if (coordinates.length < 3) return null;
    const ring = [...coordinates];
    // Close the ring (Leaflet uses [lat, lng], WKT uses lng lat)
    if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
        ring.push([...ring[0]] as [number, number]);
    }
    // WKT format: POLYGON((lng lat, lng lat, ...))
    const points = ring.map((p) => `${p[1]} ${p[0]}`).join(', ');
    return `POLYGON((${points}))`;
}

// Approximate area in hectares using Shoelace formula + lat/lng degree correction
function calcAreaHa(coordinates: [number, number][]): number {
    if (coordinates.length < 3) return 0;
    const R = 6371000; // Earth radius in meters
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
    return Math.abs(area / 2) / 10000; // m² → ha
}

// GEE 10m scale download limit ≈ 32768 px per side
// At 10m/px → 32768 × 10m = ~327 km per side → ~25,000 ha safe limit
const MAX_AREA_HA = 25000;

interface MapComponentProps {
    onPolygonChange: (wkt: string | null, areaHa?: number) => void;
}

// Sub-component that handles map click events
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

export default function MapComponent({ onPolygonChange }: MapComponentProps) {
    const [isDrawing, setIsDrawing] = useState(false);
    const [points, setPoints] = useState<[number, number][]>([]);

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
    };

    const areaHa = points.length >= 3 ? calcAreaHa(points) : 0;
    const areaTooLarge = areaHa > MAX_AREA_HA;

    return (
        <div className="w-full h-full rounded-xl overflow-hidden border border-zinc-700/50 shadow-2xl relative bg-zinc-900">
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
            </div>

            <MapContainer
                center={[39.0, 35.0]}
                zoom={6}
                style={{ height: '100%', width: '100%' }}
                attributionControl={false}
            >
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
                            fillOpacity: 0.25,
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
                                // Live update during drag
                                const latlng = e.target.getLatLng();
                                setPoints(prev => {
                                    const newPts = [...prev];
                                    newPts[idx] = [latlng.lat, latlng.lng];
                                    return newPts;
                                });
                            },
                            dragend: (e) => {
                                // Finalize on drop
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
            </MapContainer>
        </div>
    );
}
