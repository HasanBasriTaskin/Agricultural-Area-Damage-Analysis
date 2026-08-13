"use client"
import React, { useRef, useEffect, useState } from 'react';
import Map, { NavigationControl, useControl, MapRef } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';

// Simple GeoJSON to WKT Polygon converter
function geoJsonPolygonToWkt(geometry: any) {
    if (geometry.type !== 'Polygon') return null;
    const rings = geometry.coordinates.map((ring: any[]) => {
        const points = ring.map((p) => `${p[0]} ${p[1]}`).join(', ');
        return `(${points})`;
    });
    return `POLYGON(${rings.join(', ')})`;
}

// Wrapper for MapboxDraw control
function DrawControl(props: any) {
    useControl(
        () => new MapboxDraw(props) as any,
        ({ map }: { map: any }) => {
            map.on('draw.create', props.onCreate);
            map.on('draw.update', props.onUpdate);
            map.on('draw.delete', props.onDelete);
        },
        ({ map }: { map: any }) => {
            map.off('draw.create', props.onCreate);
            map.off('draw.update', props.onUpdate);
            map.off('draw.delete', props.onDelete);
        },
        {
            position: props.position
        }
    );
    return null;
}

interface MapComponentProps {
    onPolygonChange: (wkt: string | null) => void;
}

export default function MapComponent({ onPolygonChange }: MapComponentProps) {
    const [viewState, setViewState] = useState({
        longitude: 35.0, // Default to Turkey region approx
        latitude: 39.0,
        zoom: 5
    });

    const handleUpdate = (e: any) => {
        if (e.features && e.features.length > 0) {
            const feature = e.features[0];
            const wkt = geoJsonPolygonToWkt(feature.geometry);
            onPolygonChange(wkt);
        } else {
            onPolygonChange(null);
        }
    };

    const handleDelete = () => {
        onPolygonChange(null);
    };

    return (
        <div className="w-full h-full rounded-xl overflow-hidden border border-gray-700/50 shadow-2xl relative">
            <Map
                {...viewState}
                onMove={evt => setViewState(evt.viewState)}
                mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json" // Premium dark map style
                attributionControl={false}
            >
                <NavigationControl position="top-right" />
                <DrawControl
                    position="top-left"
                    displayControlsDefault={false}
                    controls={{
                        polygon: true,
                        trash: true
                    }}
                    onCreate={handleUpdate}
                    onUpdate={handleUpdate}
                    onDelete={handleDelete}
                />
            </Map>
        </div>
    );
}
