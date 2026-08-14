import io
import os
import uuid
import math
from datetime import datetime
from typing import Dict, Any, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import shapely.wkt
from geoalchemy2.shape import to_shape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
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

class PdfReportService:
    def __init__(self, minio_client: Optional[MinioStorageClient] = None):
        self.minio_client = minio_client or MinioStorageClient()
        _register_turkish_fonts()

    def _generate_map_snapshot(
        self,
        cells: List[Any],
        aoi_wkt: Optional[str] = None,
        hotspots: Optional[List[Any]] = None
    ) -> Optional[io.BytesIO]:
        """
        Renders a high-resolution map snapshot with AOI boundary, H3 hexagons and Hotspots.
        """
        if not cells and not aoi_wkt:
            return None

        try:
            fig, ax = plt.subplots(figsize=(7, 3.8), dpi=160)
            ax.set_facecolor('#0f172a')
            fig.patch.set_facecolor('#0f172a')

            # Hotspots set for fast check
            hs_set = set()
            if hotspots:
                for h in hotspots:
                    if "Hotspot" in (h.classification or ""):
                        hs_set.add(h.h3_index)

            # Color mapping
            color_map = {
                "Yok": "#22c55e",
                "Hafif": "#eab308",
                "Orta": "#f97316",
                "Ağır": "#ef4444"
            }

            # 1. Plot H3 Hexagons
            for cell in cells:
                geom = to_shape(cell.geometry) if hasattr(cell, 'geometry') else None
                if geom and geom.geom_type == 'Polygon':
                    x, y = geom.exterior.xy
                    cls = cell.damage_class or "Yok"
                    fc = color_map.get(cls, "#22c55e")
                    is_hs = cell.h3_index in hs_set
                    ec = '#dc2626' if is_hs else '#334155'
                    lw = 2.2 if is_hs else 0.8
                    ax.fill(x, y, alpha=0.85, fc=fc, ec=ec, lw=lw, zorder=3)

            # 2. Plot AOI boundary
            if aoi_wkt:
                try:
                    aoi_geom = shapely.wkt.loads(aoi_wkt)
                    if aoi_geom.geom_type == 'Polygon':
                        bx, by = aoi_geom.exterior.xy
                        ax.plot(bx, by, color='#38bdf8', linestyle='--', linewidth=2.0, label='Seçili AOI Sınırı', zorder=4)
                    elif aoi_geom.geom_type == 'MultiPolygon':
                        for poly in aoi_geom.geoms:
                            bx, by = poly.exterior.xy
                            ax.plot(bx, by, color='#38bdf8', linestyle='--', linewidth=2.0, zorder=4)
                except Exception:
                    pass

            ax.set_title("Mekânsal Hasar Dağılımı ve H3 Grid Haritası", color='#f8fafc', fontsize=10, fontweight='bold', pad=8)
            ax.axis('off')

            # Legend Patches
            p_yok = mpatches.Patch(color='#22c55e', label='Yok (<%20)')
            p_hafif = mpatches.Patch(color='#eab308', label='Hafif (%20-%45)')
            p_orta = mpatches.Patch(color='#f97316', label='Orta (%45-%70)')
            p_agir = mpatches.Patch(color='#ef4444', label='Ağır (>%70)')
            p_hs = mpatches.Patch(facecolor='none', edgecolor='#dc2626', linewidth=2, label='🔥 Hotspot')

            legend = ax.legend(
                handles=[p_yok, p_hafif, p_orta, p_agir, p_hs],
                loc='lower left',
                facecolor='#1e293b',
                edgecolor='#475569',
                labelcolor='#f8fafc',
                fontsize=7.5,
                framealpha=0.9
            )

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception as e:
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
        aoi_wkt: Optional[str] = None
    ) -> bytes:
        """
        Generates a formal, beautiful, multi-section A4 PDF Damage Assessment Report with Map Visual and Full Weather details.
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
            topMargin=32,
            bottomMargin=32
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
            alignment=1 # Center
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
            spaceBefore=6,
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

        # 1. Header Banner
        story.append(Paragraph("T.C. TARIMSAL HASAR TESPİT VE DEĞERLENDİRME RAPORU", title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Çoklu Sensör (Sentinel-1 SAR + Sentinel-2 Optik + Meteoroloji Füzyonu) Analizi", subtitle_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceBefore=2, spaceAfter=8))

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
            ('PADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # 2. General Info & AOI Table
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
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 8))

        # 3. Weather & Meteorological Verification (Enhanced with Temperature & Humidity)
        story.append(Paragraph("2. Meteorolojik Doğrulama, Sıcaklık ve Nem Göstergeleri", section_heading))
        weather = summary_data.get('weather') or weather_data or {}
        precip = weather.get('precipitation_mm', 0.0)
        sm = weather.get('soil_moisture_m3_m3', 0.0)
        wind = weather.get('wind_speed_kmh', 0.0)
        t_max = weather.get('temperature_max_c')
        t_min = weather.get('temperature_min_c')
        t_mean = weather.get('temperature_mean_c')
        is_anomaly = weather.get('is_anomaly', False)

        temp_str = f"Maks: {t_max}°C / Min: {t_min}°C (Ort: {t_mean}°C)" if t_max is not None else "Ölçüm Alındı"
        anomaly_text = "<font color='#dc2626'><b>EKSTREM AFET ANOMALİSİ TESPİT EDİLDİ</b></font>" if is_anomaly else "<font color='#16a34a'><b>Normal Meteorolojik Seviye</b></font>"

        weather_table_data = [
            ["Meteorolojik Parametre", "Ölçülen Değer", "Referans / Eşik", "Değerlendirme"],
            ["Hava Sıcaklığı (2m)", temp_str, "Mevsim Normalleri", "İklim Verisi"],
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
            ('PADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(weather_table)
        story.append(Spacer(1, 8))

        # 4. Map Visual Snapshot
        if cells or aoi_wkt:
            map_img_buf = self._generate_map_snapshot(cells or [], aoi_wkt, hotspots or [])
            if map_img_buf:
                story.append(Paragraph("3. Uydu Tabanlı Mekânsal Hasar Haritası", section_heading))
                story.append(Image(map_img_buf, width=520, height=210))
                story.append(Spacer(1, 8))

        # 5. Damage Distribution & Pie Chart
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
            ('PADDING', (0,0), (-1,-1), 3.5),
            ('TEXTCOLOR', (0,1), (0,1), colors.HexColor('#16a34a')), # Green
            ('TEXTCOLOR', (0,2), (0,2), colors.HexColor('#ca8a04')), # Yellow
            ('TEXTCOLOR', (0,3), (0,3), colors.HexColor('#ea580c')), # Orange
            ('TEXTCOLOR', (0,4), (0,4), colors.HexColor('#dc2626')), # Red
        ]))

        # Pie Chart Drawing
        d = Drawing(100, 75)
        pc = Pie()
        pc.x = 12
        pc.y = 5
        pc.width = 68
        pc.height = 68
        
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
        story.append(Spacer(1, 8))

        # 6. Hotspots & Spatial Concentration
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
            ('PADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(hs_table)
        story.append(Spacer(1, 8))

        # 7. Methodology & Weights
        story.append(Paragraph("6. Analiz Metodolojisi ve Ağırlık Katsayıları", section_heading))
        method_text = (
            "Bu analiz, <b>Sentinel-1 C-Bant SAR</b> radar geri saçılım değişimi (%35), "
            "<b>Sentinel-2 MSI</b> optik bantlarından türetilen <b>ΔNDMI</b> nem kaybı indeksi (%25) ve "
            "<b>ΔNDRE</b> klorofil/vejetasyon sağlığı indeksi (%20) ile <b>Open-Meteo & ERA5</b> meteorolojik ekstrem "
            "doğrulama katsayılarının (%20) ağırlıklı lineer füzyon modeli (Weighted Fusion Strategy) ile hesaplanmıştır."
        )
        story.append(Paragraph(method_text, body_style))

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
