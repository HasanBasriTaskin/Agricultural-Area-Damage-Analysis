"use client";
import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  CartesianGrid
} from 'recharts';

interface TimeSeriesPoint {
  date: string;
  precipitation_mm: number;
  soil_moisture: number;
  temp_max?: number | null;
  temp_min?: number | null;
  temp_mean?: number | null;
  wind_speed_kmh?: number;
  is_event_date?: boolean;
}

interface TimeSeriesChartProps {
  jobId: string;
}

export default function TimeSeriesChart({ jobId }: TimeSeriesChartProps) {
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [eventDate, setEventDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/results/timeseries`);
        if (!res.ok) {
          throw new Error("Meteorolojik zaman serisi alınamadı.");
        }
        const json = await res.json();
        if (isMounted) {
          setData(json.timeseries || []);
          setEventDate(json.event_date || null);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Veri yüklenirken hata oluştu.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
  }, [jobId]);

  if (loading) {
    return (
      <div className="p-6 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-center min-h-[220px]">
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          30 Günlük Meteorolojik Zaman Serisi Yükleniyor...
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 text-xs text-zinc-400 text-center">
        Meteorolojik zaman serisi verisi bulunamadı.
      </div>
    );
  }

  // Calculate metrics
  const totalPrecip = data.reduce((sum, d) => sum + (d.precipitation_mm || 0), 0);
  const maxPrecip = Math.max(...data.map(d => d.precipitation_mm || 0), 0);
  const avgMoisture = data.length > 0 ? (data.reduce((sum, d) => sum + (d.soil_moisture || 0), 0) / data.length) : 0;
  const maxTemp = Math.max(...data.map(d => d.temp_max || 0), 0);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload as TimeSeriesPoint;
      return (
        <div className="p-3 bg-zinc-900/95 border border-zinc-700 rounded-lg shadow-xl text-xs space-y-1 backdrop-blur-sm z-[2000]">
          <div className="flex items-center justify-between gap-4 font-semibold text-zinc-200 border-b border-zinc-800 pb-1">
            <span>📅 {label}</span>
            {point.is_event_date && (
              <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30 rounded text-[10px]">
                🚨 Afet Tarihi
              </span>
            )}
          </div>
          <div className="flex items-center justify-between gap-4 text-blue-400">
            <span>🌧️ Günlük Yağış:</span>
            <span className="font-bold font-mono">{point.precipitation_mm} mm</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-emerald-400">
            <span>🌱 Toprak Nemi (0-7cm):</span>
            <span className="font-bold font-mono">{point.soil_moisture} m³/m³</span>
          </div>
          {point.temp_max !== null && point.temp_min !== null && (
            <div className="flex items-center justify-between gap-4 text-amber-400">
              <span>🌡️ Sıcaklık:</span>
              <span className="font-bold font-mono">{point.temp_min}°C - {point.temp_max}°C</span>
            </div>
          )}
          {point.wind_speed_kmh && (
            <div className="flex items-center justify-between gap-4 text-cyan-400">
              <span>💨 Rüzgar Hızı:</span>
              <span className="font-bold font-mono">{point.wind_speed_kmh} km/h</span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="p-5 rounded-2xl bg-zinc-950 border border-zinc-800/80 shadow-2xl space-y-4">
      {/* Header & Quick KPI Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-zinc-800/60 pb-3">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-zinc-100">📈 30 Günlük Meteorolojik Yağış & Nem Değişimi</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800 font-mono">
              ERA5 Reanalysis
            </span>
          </div>
          <p className="text-xs text-zinc-400">
            Afet öncesi birikimli yağış, nem doygunluğu ve sıcaklık grafiği
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800">
            <span className="text-zinc-400 text-[11px]">Toplam Yağış: </span>
            <span className="font-bold text-blue-400 font-mono">{roundToOne(totalPrecip)} mm</span>
          </div>
          <div className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800">
            <span className="text-zinc-400 text-[11px]">Pik Yağış: </span>
            <span className="font-bold text-cyan-400 font-mono">{maxPrecip} mm</span>
          </div>
          <div className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800">
            <span className="text-zinc-400 text-[11px]">Ort. Nem: </span>
            <span className="font-bold text-emerald-400 font-mono">{avgMoisture.toFixed(3)} m³/m³</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 15, left: -15, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => d.slice(5)} // MM-DD
              stroke="#71717a"
              fontSize={10}
              tickLine={false}
            />
            {/* Left Y Axis: Precipitation (mm) */}
            <YAxis
              yAxisId="left"
              stroke="#60a5fa"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              unit=" mm"
            />
            {/* Right Y Axis: Soil Moisture (m3/m3) */}
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#34d399"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              domain={[0, 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
              iconType="circle"
              iconSize={8}
            />

            {/* Event Date Vertical Reference Marker */}
            {eventDate && (
              <ReferenceLine
                x={eventDate}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: '🚨 Afet Günü',
                  position: 'top',
                  fill: '#ef4444',
                  fontSize: 10,
                  fontWeight: 'bold'
                }}
              />
            )}

            {/* Precipitation Bars */}
            <Bar
              yAxisId="left"
              dataKey="precipitation_mm"
              name="Günlük Yağış (mm)"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              maxBarSize={18}
            />

            {/* Soil Moisture Line */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="soil_moisture"
              name="Toprak Nemi (m³/m³)"
              stroke="#10b981"
              strokeWidth={2.2}
              dot={{ r: 2, fill: '#10b981' }}
              activeDot={{ r: 5 }}
            />

            {/* Temperature Line */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="temp_mean"
              name="Ort. Sıcaklık (°C)"
              stroke="#f59e0b"
              strokeWidth={1.8}
              strokeDasharray="3 3"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function roundToOne(num: number): number {
  return Math.round(num * 10) / 10;
}
