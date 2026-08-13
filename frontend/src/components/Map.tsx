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

interface MapComponentProps {
    onPolygonChange: (wkt: string | null) => void;
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
            onPolygonChange(coordsToWkt(newPoints));
        } else {
            onPolygonChange(null);
        }
    };

    const handleStartDrawing = () => {
        setIsDrawing(true);
        setPoints([]);
        onPolygonChange(null);
    };

    const handleFinish = () => {
        setIsDrawing(false);
    };

    const handleClear = () => {
        setIsDrawing(false);
        setPoints([]);
        onPolygonChange(null);
    };

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
                            color: '#3b82f6',
                            fillColor: '#3b82f6',
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
                            color: '#3b82f6',
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
                                    onPolygonChange(coordsToWkt(newPts));
                                }
                            }
                        }}
                    />
                ))}
            </MapContainer>
        </div>
    );
}
