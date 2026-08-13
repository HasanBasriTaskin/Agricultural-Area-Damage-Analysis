"use client";

import * as React from "react";
import Map, { NavigationControl, ScaleControl } from "react-map-gl/maplibre";
import 'maplibre-gl/dist/maplibre-gl.css';

interface AoiMapProps {
  onPolygonDrawn?: (geojson: any) => void;
}

export function AoiMap({ onPolygonDrawn }: AoiMapProps) {
  return (
    <div className="w-full h-[600px] rounded-xl overflow-hidden border border-border/50 relative shadow-2xl">
      <Map
        initialViewState={{
          longitude: 35.2433,
          latitude: 38.9637,
          zoom: 5
        }}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
      >
        <NavigationControl position="top-right" />
        <ScaleControl position="bottom-right" />
        
        {/* İleride @mapbox/mapbox-gl-draw veya terra-draw eklenecek AOI çizimi için */}
      </Map>
    </div>
  );
}
