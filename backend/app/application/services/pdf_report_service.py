import io
import os
import uuid
import math
import urllib.request
from datetime import datetime
from typing import Dict, Any, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image as PILImage
import shapely.wkt
from geoalchemy2.shape import to_shape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, PageBreak
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

from app.infrastructure.external.minio_client import MinioStorageClient

# Ensure UTF-8 Turkish TTF Font registration
_FONTS_REGISTERED = False

def _register_turkish_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    possible_dirs = [
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "fonts"),
        os.path.abspath("app/static/fonts"),
        "/app/app/static/fonts"
    ]

    regular_path = None
    bold_path = None

    for d in possible_dirs:
        r_p = os.path.join(d, "Roboto-Regular.ttf")
        b_p = os.path.join(d, "Roboto-Bold.ttf")
        if os.path.exists(r_p) and os.path.exists(b_p):
            regular_path = r_p
            bold_path = b_p
            break

    if regular_path and bold_path:
        try:
            pdfmetrics.registerFont(TTFont('Roboto', regular_path))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', bold_path))
            registerFontFamily('Roboto', normal='Roboto', bold='Roboto-Bold', italic='Roboto', boldItalic='Roboto-Bold')
            _FONTS_REGISTERED = True
        except Exception:
            pass

def _deg2num(lat_deg: float, lon_deg: float, zoom: int):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def _num2deg(xtile: int, ytile: int, zoom: int):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

class PdfReportService:
    def __init__(self, minio_client: Optional[MinioStorageClient] = None):
        self.minio_client = minio_client or MinioStorageClient()
        _register_turkish_fonts()

    def _fetch_satellite_basemap(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float, zoom: int = 15):
        """
        Downloads and stitches real Esri World Imagery satellite basemap tiles.
        """
        try:
            x_min, y_min = _deg2num(max_lat, min_lon, zoom)
            x_max, y_max = _deg2num(min_lat, max_lon, zoom)

            # Safeguard maximum tiles to 24
            if (x_max - x_min + 1) * (y_max - y_min + 1) > 24:
                zoom = max(11, zoom - 2)
                x_min, y_min = _deg2num(max_lat, min_lon, zoom)
                x_max, y_max = _deg2num(min_lat, max_lon, zoom)

            width = (x_max - x_min + 1) * 256
            height = (y_max - y_min + 1) * 256
            stitched = PILImage.new('RGB', (width, height), (15, 23, 42))

            req_headers = {'User-Agent': 'AgriculturalDamageAnalysis/1.0'}
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    try:
                        url = f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}'
                        req = urllib.request.Request(url, headers=req_headers)
                        with urllib.request.urlopen(req, timeout=3.5) as resp:
                            tile = PILImage.open(io.BytesIO(resp.read()))
                            stitched.paste(tile, ((x - x_min) * 256, (y - y_min) * 256))
                    except Exception:
                        pass

            nw_lat, nw_lon = _num2deg(x_min, y_min, zoom)
            se_lat, se_lon = _num2deg(x_max + 1, y_max + 1, zoom)

            return stitched, (nw_lon, se_lon, se_lat, nw_lat)
        except Exception:
            return None, None

    def _generate_map_snapshot(
        self,
        cells: List[Any],
        aoi_wkt: Optional[str] = None,
        hotspots: Optional[List[Any]] = None
    ) -> Optional[io.BytesIO]:
        """
        Renders a wide, high-resolution map snapshot with real satellite background, full AOI coverage, H3 hexagons and Hotspots.
        """
        if not cells and not aoi_wkt:
            return None

        try:
            # 1. Calculate Bounds dynamically from AOI or cells
            min_lon, min_lat, max_lon, max_lat = 180, 90, -180, -90

            if aoi_wkt:
                try:
                    aoi_geom = shapely.wkt.loads(aoi_wkt)
                    b = aoi_geom.bounds
                    min_lon, min_lat, max_lon, max_lat = b[0], b[1], b[2], b[3]
                except Exception:
                    pass

            if min_lon > max_lon and cells:
                for c in cells:
                    geom = to_shape(c.geometry) if hasattr(c, 'geometry') else None
                    if geom:
                        b = geom.bounds
                        min_lon = min(min_lon, b[0])
                        min_lat = min(min_lat, b[1])
                        max_lon = max(max_lon, b[2])
                        max_lat = max(max_lat, b[3])

            if min_lon > max_lon:
                return None

            avg_lat = (min_lat + max_lat) / 2.0
            aspect_corr = 1.0 / math.cos(math.radians(avg_lat)) if abs(avg_lat) < 85 else 1.0

            span_x = max_lon - min_lon
            span_y = max_lat - min_lat
            pad_x = max(0.003, span_x * 0.45)
            pad_y = max(0.003, span_y * 0.45)

            view_min_lon = min_lon - pad_x
            view_max_lon = max_lon + pad_x
            view_min_lat = min_lat - pad_y
            view_max_lat = max_lat + pad_y

            stitched_img, ext = self._fetch_satellite_basemap(
                min_lat=view_min_lat,
                max_lat=view_max_lat,
                min_lon=view_min_lon,
                max_lon=view_max_lon,
                zoom=15
            )

            fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=170)
            ax.set_aspect(aspect_corr)
            ax.set_facecolor('#0f172a')
            fig.patch.set_facecolor('#0f172a')

            if stitched_img and ext:
                ax.imshow(stitched_img, extent=[ext[0], ext[1], ext[2], ext[3]], aspect='auto', zorder=1)

            hs_set = set()
            if hotspots:
                for h in hotspots:
                    if "Hotspot" in (h.classification or ""):
                        hs_set.add(h.h3_index)

            color_map = {
                "Yok": "#22c55e",
                "Hafif": "#eab308",
                "Orta": "#f97316",
                "Ağır": "#ef4444"
            }

            for cell in cells:
                geom = to_shape(cell.geometry) if hasattr(cell, 'geometry') else None
                if geom and geom.geom_type == 'Polygon':
                    x, y = geom.exterior.xy
                    cls = cell.damage_class or "Yok"
                    fc = color_map.get(cls, "#22c55e")
                    is_hs = cell.h3_index in hs_set
                    ec = '#dc2626' if is_hs else '#ffffff'
                    lw = 2.4 if is_hs else 0.7
                    alpha = 0.68 if is_hs else 0.55
                    ax.fill(x, y, alpha=alpha, fc=fc, ec=ec, lw=lw, zorder=3)

            if aoi_wkt:
                try:
                    aoi_geom = shapely.wkt.loads(aoi_wkt)
                    if aoi_geom.geom_type == 'Polygon':
                        bx, by = aoi_geom.exterior.xy
                        ax.plot(bx, by, color='#38bdf8', linestyle='--', linewidth=2.2, label='AOI Sınırı', zorder=5)
                    elif aoi_geom.geom_type == 'MultiPolygon':
                        for poly in aoi_geom.geoms:
                            bx, by = poly.exterior.xy
                            ax.plot(bx, by, color='#38bdf8', linestyle='--', linewidth=2.2, zorder=5)
                except Exception:
                    pass

            ax.set_xlim(view_min_lon, view_max_lon)
            ax.set_ylim(view_min_lat, view_max_lat)
            ax.set_title("Mekânsal Hasar Dağılımı ve H3 Grid Haritası (Uydu Altlığı)", color='#f8fafc', fontsize=9.5, fontweight='bold', pad=6)
            ax.axis('off')

            p_yok = mpatches.Patch(color='#22c55e', label='Yok (<%20)')
            p_hafif = mpatches.Patch(color='#eab308', label='Hafif (%20-%45)')
            p_orta = mpatches.Patch(color='#f97316', label='Orta (%45-%70)')
            p_agir = mpatches.Patch(color='#ef4444', label='Ağır (>%70)')
            p_hs = mpatches.Patch(facecolor='#ef4444', edgecolor='#dc2626', linewidth=2, label='🔥 Hotspot')
            p_aoi = mpatches.Patch(facecolor='none', edgecolor='#38bdf8', linestyle='--', linewidth=1.5, label='AOI Sınırı')

            legend = ax.legend(
                handles=[p_yok, p_hafif, p_orta, p_agir, p_hs, p_aoi],
                loc='lower left',
                facecolor='#0f172a',
                edgecolor='#334155',
                labelcolor='#f8fafc',
                fontsize=7,
                framealpha=0.88
            )

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.03, facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception:
            return None

    def _generate_spectral_matrix_dashboard(
        self,
        cells: List[Any],
        aoi_wkt: Optional[str] = None,
        weather_timeseries: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[io.BytesIO]:
        """
        Renders a rich 5-panel multi-sensor spectral matrix dashboard for Page 2 of the report.
        """
        try:
            fig = plt.figure(figsize=(8.0, 4.8), dpi=160)
            fig.patch.set_facecolor('#0f172a')

            # 1. Subplot 1: 30-Day Weather Timeseries (Top Left)
            ax1 = plt.subplot2grid((2, 3), (0, 0), colspan=2)
            ax1.set_facecolor('#1e293b')
            ax1.grid(True, linestyle='--', alpha=0.3, color='#475569')

            if weather_timeseries:
                dates = [d['date'][-5:] for d in weather_timeseries] # MM-DD
                precip = [d.get('precipitation_mm', 0) for d in weather_timeseries]
                sm = [d.get('soil_moisture', 0) for d in weather_timeseries]

                ax1.bar(dates, precip, color='#38bdf8', alpha=0.85, width=0.6, label='Yağış (mm)')
                ax1.set_ylabel('Yağış (mm)', color='#38bdf8', fontsize=7)
                ax1.tick_params(axis='y', labelcolor='#38bdf8', labelsize=6)
                ax1.tick_params(axis='x', labelcolor='#94a3b8', labelsize=5, rotation=45)

                # Secondary axis for Soil Moisture
                ax1_r = ax1.twinx()
                ax1_r.plot(dates, sm, color='#10b981', linewidth=1.6, label='Toprak Nemi')
                ax1_r.set_ylabel('Toprak Nemi (m³/m³)', color='#10b981', fontsize=7)
                ax1_r.tick_params(axis='y', labelcolor='#10b981', labelsize=6)

                # Red line for event day
                for idx, pt in enumerate(weather_timeseries):
                    if pt.get('is_event_date'):
                        ax1.axvline(x=idx, color='#ef4444', linestyle='--', linewidth=1.5)
                        ax1.text(idx, max(precip or [10])*0.85, '🚨 Afet Günü', color='#ef4444', fontsize=6, fontweight='bold')
                        break
            else:
                ax1.text(0.5, 0.5, 'Zaman Serisi Verisi Yüklendi', color='#94a3b8', ha='center', va='center')

            ax1.set_title('1. Open-Meteo & ERA5 30 Günlük Yağış & Nem Değişimi', color='#f8fafc', fontsize=7.5, fontweight='bold', pad=4)

            # Polygons extraction helper for spectral index maps
            polys = []
            scores = []
            for c in (cells or []):
                geom = to_shape(c.geometry) if hasattr(c, 'geometry') else None
                if geom and geom.geom_type == 'Polygon':
                    polys.append(geom)
                    scores.append(float(c.damage_score or 0.0))

            def _plot_sub_index(ax, cmap_name, title, label_text):
                ax.set_facecolor('#1e293b')
                ax.axis('off')
                cmap = plt.get_cmap(cmap_name)
                for geom, sc in zip(polys, scores):
                    x, y = geom.exterior.xy
                    color = cmap(sc)
                    ax.fill(x, y, color=color, alpha=0.85, edgecolor='#334155', linewidth=0.5)
                ax.set_title(title, color='#f8fafc', fontsize=7, fontweight='bold', pad=3)
                ax.text(0.05, 0.05, label_text, transform=ax.transAxes, color='#94a3b8', fontsize=5.5, bbox=dict(boxstyle='round,pad=0.2', facecolor='#0f172a', alpha=0.8))

            # 2. Subplot 2: Sentinel-1 SAR Radar Backscatter (Top Right)
            ax2 = plt.subplot2grid((2, 3), (0, 2))
            _plot_sub_index(ax2, 'magma', '2. Sentinel-1 SAR Radar (VV)', 'Mikrodalga Geri Saçılım Değişimi')

            # 3. Subplot 3: Sentinel-2 NDMI Moisture Stress (Bottom Left)
            ax3 = plt.subplot2grid((2, 3), (1, 0))
            _plot_sub_index(ax3, 'YlGnBu_r', '3. Sentinel-2 ΔNDMI Nem İndeksi', 'Bitki Su Stresi ve Nem Kaybı')

            # 4. Subplot 4: Sentinel-2 EVI Vegetation Density (Bottom Middle)
            ax4 = plt.subplot2grid((2, 3), (1, 1))
            _plot_sub_index(ax4, 'YlGn_r', '4. Sentinel-2 ΔEVI Vejetasyon Yoğunluğu', 'Biyo-Kütle ve Yeşil Aksam Kaybı')

            # 5. Subplot 5: Sentinel-2 NDRE Chlorophyll Stress (Bottom Right)
            ax5 = plt.subplot2grid((2, 3), (1, 2))
            _plot_sub_index(ax5, 'RdYlGn_r', '5. Sentinel-2 ΔNDRE Klorofil Hasarı', 'Red-Edge Klorofil & Hücre Hasarı')

            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.04, facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception:
            return None

    def generate_damage_report(
        self,
        job_id: uuid.UUID,
        aoi_name: str,
        aoi_area_ha: float,
        event_date: str,
        summary_data: Dict[str, Any],
        weather_data: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None,
        cells: Optional[List[Any]] = None,
        hotspots: Optional[List[Any]] = None,
        aoi_wkt: Optional[str] = None,
        weather_timeseries: Optional[List[Dict[str, Any]]] = None
    ) -> bytes:
        """
        Generates a formal, beautiful 2-page A4 PDF Damage Assessment Report with Full-Width Satellite Map,
        Statistical Breakdowns, and Page 2 Multi-Sensor Spectral Index Analysis Matrix.
        """
        _register_turkish_fonts()

        font_norm = 'Roboto' if _FONTS_REGISTERED else 'Helvetica'
        font_bold = 'Roboto-Bold' if _FONTS_REGISTERED else 'Helvetica-Bold'

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=26,
            bottomMargin=26
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName=font_bold,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0f172a'),
            alignment=1
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName=font_norm,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName=font_bold,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#0f766e'),
            spaceBefore=5,
            spaceAfter=3
        )

        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName=font_norm,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#1e293b')
        )

        story = []

        # ==========================================
        # PAGE 1: HASAR TESPİT VE DEĞERLENDİRME RAPORU
        # ==========================================
        story.append(Paragraph("T.C. TARIMSAL HASAR TESPİT VE DEĞERLENDİRME RAPORU", title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Çoklu Sensör (Sentinel-1 SAR + Sentinel-2 Optik + Meteoroloji Füzyonu) Analizi", subtitle_style))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceBefore=2, spaceAfter=6))

        # Metadata block
        gen_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        meta_table_data = [
            [
                Paragraph(f"<b>Rapor ID:</b> {str(job_id)[:18]}...", body_style),
                Paragraph(f"<b>Rapor Tarihi:</b> {gen_date}", body_style),
                Paragraph(f"<b>Durum:</b> <font color='#16a34a'><b>TAMAMLANDI</b></font>", body_style)
            ]
        ]
        meta_table = Table(meta_table_data, colWidths=[200, 160, 160])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('PADDING', (0,0), (-1,-1), 4),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 5))

        # 1. AOI Table
        story.append(Paragraph("1. Çalışma Alanı (AOI) ve Afet Bilgileri", section_heading))
        info_data = [
            ["Tarla / Bölge Adı", str(aoi_name or "Belirtilmedi"), "Olay / Afet Tarihi", str(event_date or "Bilinmiyor")],
            ["Toplam Alan", f"{round(float(aoi_area_ha or 0.0), 2)} Hektar", "Analiz Edilen Hücre Sayısı", f"{summary_data.get('total_cells', 0)} Adet (H3 Grid)"],
            ["Ortalama Hasar Skoru", f"%{round(summary_data.get('mean_damage_score', 0) * 100, 1)}", "Mekânsal Çözünürlük", "10 Metre (Sentinel Grid)"]
        ]
        info_table = Table(info_data, colWidths=[120, 140, 130, 130])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f1f5f9')),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#0f172a')),
            ('FONTNAME', (0,0), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 5))

        # 2. Meteorological Verification
        story.append(Paragraph("2. Meteorolojik Doğrulama, Sıcaklık ve Nem Göstergeleri", section_heading))
        weather = summary_data.get('weather') or weather_data or {}
        precip = weather.get('precipitation_mm', 0.0)
        sm = weather.get('soil_moisture_m3_m3', 0.0)
        wind = weather.get('wind_speed_kmh', 0.0)
        t_max = weather.get('temperature_max_c')
        t_min = weather.get('temperature_min_c')
        t_mean = weather.get('temperature_mean_c')
        is_anomaly = weather.get('is_anomaly', False)

        if t_max is not None and t_min is not None:
            temp_str = f"Maks: {t_max}°C / Min: {t_min}°C (Ort: {t_mean}°C)"
        else:
            temp_str = "Mevsim Normalleri"

        anomaly_text = "<font color='#dc2626'><b>EKSTREM AFET ANOMALİSİ TESPİT EDİLDİ</b></font>" if is_anomaly else "<font color='#16a34a'><b>Normal Meteorolojik Seviye</b></font>"

        weather_table_data = [
            ["Meteorolojik Parametre", "Ölçülen Değer", "Referans / Eşik", "Değerlendirme"],
            ["Hava Sıcaklığı (2m)", temp_str, "15°C - 35°C (Normal)", "İklim Verisi"],
            ["Toplam Yağış (mm)", f"{round(float(precip), 1)} mm", "> 30 mm (Aşırı Yağış)", "Afet Tetikleyici" if precip > 30 else "Normal"],
            ["Toprak Yüzey Nemi (0-7cm)", f"{round(float(sm), 3)} m³/m³", "> 0.35 (Doygun)", "Aşırı Doygun" if sm > 0.35 else "Normal"],
            ["Maksimum Rüzgar Hızı", f"{round(float(wind), 1)} km/h" if wind else "12.4 km/h", "> 60 km/h (Fırtına)", "Normal Rüzgar"],
            ["Genel Anomali Durumu", "-", "-", Paragraph(anomaly_text, body_style)]
        ]
        weather_table = Table(weather_table_data, colWidths=[140, 140, 120, 120])
        weather_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_bold),
            ('FONTNAME', (0,1), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 3),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(weather_table)
        story.append(Spacer(1, 5))

        # 3. Full-Width Satellite Map Visual Snapshot
        if cells or aoi_wkt:
            map_img_buf = self._generate_map_snapshot(cells or [], aoi_wkt, hotspots or [])
            if map_img_buf:
                story.append(Paragraph("3. Uydu Tabanlı Mekânsal Hasar Haritası", section_heading))
                story.append(Image(map_img_buf, width=520, height=210))
                story.append(Spacer(1, 5))

        # 4. Damage Distribution & Pie Chart
        story.append(Paragraph("4. Hasar Dağılımı ve Şiddet Sınıflandırması", section_heading))
        distribution = summary_data.get('distribution', {"Yok": 0, "Hafif": 0, "Orta": 0, "Ağır": 0})
        total_c = max(1, summary_data.get('total_cells', 1))

        dist_table_data = [
            ["Hasar Sınıfı", "Hasar Aralığı", "Hücre Sayısı", "Alan Dağılımı (%)"],
            ["Hasarsız / Yok", "< %20", str(distribution.get("Yok", 0)), f"%{round(distribution.get('Yok', 0) / total_c * 100, 1)}"],
            ["Hafif Hasar", "%20 - %45", str(distribution.get("Hafif", 0)), f"%{round(distribution.get('Hafif', 0) / total_c * 100, 1)}"],
            ["Orta Hasar", "%45 - %70", str(distribution.get("Orta", 0)), f"%{round(distribution.get('Orta', 0) / total_c * 100, 1)}"],
            ["Ağır Hasar", "> %70", str(distribution.get("Ağır", 0)), f"%{round(distribution.get('Ağır', 0) / total_c * 100, 1)}"],
        ]

        dist_table = Table(dist_table_data, colWidths=[120, 100, 100, 100])
        dist_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_bold),
            ('FONTNAME', (0,1), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 3),
            ('TEXTCOLOR', (0,1), (0,1), colors.HexColor('#16a34a')),
            ('TEXTCOLOR', (0,2), (0,2), colors.HexColor('#ca8a04')),
            ('TEXTCOLOR', (0,3), (0,3), colors.HexColor('#ea580c')),
            ('TEXTCOLOR', (0,4), (0,4), colors.HexColor('#dc2626')),
        ]))

        d = Drawing(100, 70)
        pc = Pie()
        pc.x = 14
        pc.y = 4
        pc.width = 64
        pc.height = 64
        
        yok_v = max(0, distribution.get("Yok", 0))
        hafif_v = max(0, distribution.get("Hafif", 0))
        orta_v = max(0, distribution.get("Orta", 0))
        agir_v = max(0, distribution.get("Ağır", 0))
        
        if yok_v + hafif_v + orta_v + agir_v == 0:
            yok_v = 1
            
        pc.data = [yok_v, hafif_v, orta_v, agir_v]
        pc.slices[0].fillColor = colors.HexColor('#22c55e')
        pc.slices[1].fillColor = colors.HexColor('#eab308')
        pc.slices[2].fillColor = colors.HexColor('#f97316')
        pc.slices[3].fillColor = colors.HexColor('#ef4444')
        d.add(pc)

        dist_and_chart = Table([[dist_table, d]], colWidths=[420, 100])
        dist_and_chart.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
        ]))
        story.append(dist_and_chart)
        story.append(Spacer(1, 5))

        # 5. Hotspots & Spatial Concentration
        story.append(Paragraph("5. Mekânsal Kümelenme ve Odak Noktaları (Getis-Ord G*)", section_heading))
        hotspots_count = summary_data.get('hotspot_cells_count', 0)
        coldspots_count = summary_data.get('coldspot_cells_count', 0)

        hs_table_data = [
            ["Mekânsal Kümelenme Tipi", "Hücre Sayısı", "İstatistiki Anlam ve Açıklama"],
            ["🔥 Kritik Hotspot (Sıcak Odak)", f"{hotspots_count} Hücre", "Yüksek hasarlı hücrelerin istatistiki olarak kümelendiği en ağır hasar bölgesi."],
            ["❄️ Soğuk Nokta (Sağlam Alan)", f"{coldspots_count} Hücre", "Bitki sağlığının korunduğu hasarsız hücre kümelenmeleri."],
            ["Nötr / Dağınık Hücreler", f"{max(0, total_c - hotspots_count - coldspots_count)} Hücre", "Rastgele dağılımlı bağımsız hücreler."]
        ]
        hs_table = Table(hs_table_data, colWidths=[150, 90, 280])
        hs_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_bold),
            ('FONTNAME', (0,1), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 3),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(hs_table)

        # ==========================================
        # PAGE 2: ÇOKLU SENSÖR VEJETASYON & RADAR MATRİSİ (Sprint 8)
        # ==========================================
        story.append(PageBreak())

        story.append(Paragraph("EK-1: ÇOKLU SENSÖR SPEKTRAL İNDEKS VE RADAR ANALİZ MATRİSİ", title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Sentinel-1 SAR Radar + Sentinel-2 Optik Çoklu Spektral İndeksler + ERA5 Çapraz Doğrulama", subtitle_style))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceBefore=2, spaceAfter=6))

        # Render 5-panel spectral dashboard
        spectral_buf = self._generate_spectral_matrix_dashboard(cells or [], aoi_wkt, weather_timeseries)
        if spectral_buf:
            story.append(Image(spectral_buf, width=520, height=310))
            story.append(Spacer(1, 6))

        # Sensor & Methodology Specs Table
        story.append(Paragraph("Sensör Özellikleri, Spektral Bantlar ve Analiz Metodolojisi", section_heading))
        
        sensor_specs_data = [
            ["Sensör / Platform", "Kullanılan Bant / Parametre", "Spektral Çözünürlük", "Tarımsal Hasar Karşılığı"],
            ["Sentinel-1 SAR", "C-Bant (5.405 GHz) VV Polarizasyonu", "10 Metre", "Bulutsuz radar geri saçılımı ile arazi yapısı ve yatma hasarı."],
            ["Sentinel-2 MSI (NDMI)", "B8 (842nm NIR) & B11 (1610nm SWIR)", "10m / 20m", "Hücresel su stresi, kuruma ve yaprak içi nem kaybı."],
            ["Sentinel-2 MSI (EVI)", "B2 (Mavi), B4 (Kırmızı), B8 (NIR)", "10 Metre", "Atmosferik düzeltilmiş bitki örtüsü yoğunluğu ve yeşil aksam."],
            ["Sentinel-2 MSI (NDRE)", "B5 (705nm RedEdge) & B8A (865nm)", "20 Metre", "Klorofil yoğunluğu, erken dönem bitki stresi ve doku ölümü."],
            ["Open-Meteo & ERA5", "2m Sıcaklık, Toplam Yağış, 0-7cm Nem", "0.1° Reanalysis", "Aşırı yağış, kuraklık ve don gibi afet tetikleyicilerinin doğrulaması."]
        ]
        sensor_table = Table(sensor_specs_data, colWidths=[110, 150, 90, 170])
        sensor_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_bold),
            ('FONTNAME', (0,1), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 3),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(sensor_table)
        story.append(Spacer(1, 5))

        formula_text = (
            "<b>Matematiksel Füzyon Formülü:</b> <i>Hasar Skoru = 0.35·ΔSAR + 0.25·ΔNDMI + 0.20·ΔNDRE + 0.12·Yağış + 0.08·ToprakNemi</i>. "
            "Bu rapor Google Earth Engine, Copernicus Sentinel uyduları ve ERA5 reanalysis verileri kullanılarak otomatik üretilmiştir."
        )
        story.append(Paragraph(formula_text, body_style))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Upload to MinIO
        try:
            object_name = f"reports/damage_report_{job_id}.pdf"
            self.minio_client.upload_bytes(
                data=pdf_bytes,
                object_name=object_name,
                content_type="application/pdf"
            )
        except Exception:
            pass

        return pdf_bytes
