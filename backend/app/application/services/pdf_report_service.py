import io
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, String, Rect
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

    # Check font directories
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

    def generate_damage_report(
        self,
        job_id: uuid.UUID,
        aoi_name: str,
        aoi_area_ha: float,
        event_date: str,
        summary_data: Dict[str, Any],
        weather_data: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> bytes:
        """
        Generates a formal, beautiful, multi-section A4 PDF Damage Assessment Report with full UTF-8 Turkish font support.
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
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Styles with Turkish Font
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName=font_bold,
            fontSize=15,
            leading=19,
            textColor=colors.HexColor('#0f172a'),
            alignment=1 # Center
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName=font_norm,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName=font_bold,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#0f766e'),
            spaceBefore=8,
            spaceAfter=4
        )

        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName=font_norm,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#1e293b')
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("T.C. TARIMSAL HASAR TESPİT VE DEĞERLENDİRME RAPORU", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Çoklu Sensör (Sentinel-1 SAR + Sentinel-2 Optik + Meteoroloji Füzyonu) Analizi", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceBefore=2, spaceAfter=10))

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
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

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
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))

        # 3. Weather & Meteorological Verification
        story.append(Paragraph("2. Meteorolojik Doğrulama ve Ekstrem Hava Durumu", section_heading))
        weather = summary_data.get('weather') or weather_data or {}
        precip = weather.get('precipitation_mm', 0.0)
        sm = weather.get('soil_moisture_m3_m3', 0.0)
        is_anomaly = weather.get('is_anomaly', False)

        anomaly_text = "<font color='#dc2626'><b>EKSTREM AFET ANOMALİSİ TESPİT EDİLDİ</b></font>" if is_anomaly else "<font color='#16a34a'><b>Normal Meteorolojik Seviye</b></font>"

        weather_table_data = [
            ["Meteorolojik Parametre", "Ölçülen Değer", "Referans / Eşik", "Değerlendirme"],
            ["Toplam Yağış (mm)", f"{round(float(precip), 1)} mm", "> 30 mm (Aşırı Yağış)", "Afet Tetikleyici" if precip > 30 else "Normal"],
            ["Toprak Yüzey Nemi (0-7cm)", f"{round(float(sm), 3)} m³/m³", "> 0.35 (Doygun)", "Aşırı Doygun" if sm > 0.35 else "Normal"],
            ["Genel Anomali Durumu", "-", "-", Paragraph(anomaly_text, body_style)]
        ]
        weather_table = Table(weather_table_data, colWidths=[150, 110, 130, 130])
        weather_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_bold),
            ('FONTNAME', (0,1), (-1,-1), font_norm),
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(weather_table)
        story.append(Spacer(1, 10))

        # 4. Damage Distribution & Pie Chart
        story.append(Paragraph("3. Hasar Dağılımı ve Şiddet Sınıflandırması", section_heading))

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
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 4),
            ('TEXTCOLOR', (0,1), (0,1), colors.HexColor('#16a34a')), # Green
            ('TEXTCOLOR', (0,2), (0,2), colors.HexColor('#ca8a04')), # Yellow
            ('TEXTCOLOR', (0,3), (0,3), colors.HexColor('#ea580c')), # Orange
            ('TEXTCOLOR', (0,4), (0,4), colors.HexColor('#dc2626')), # Red
        ]))

        # Pie Chart Drawing
        d = Drawing(100, 80)
        pc = Pie()
        pc.x = 10
        pc.y = 5
        pc.width = 75
        pc.height = 75
        
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
        story.append(Spacer(1, 10))

        # 5. Hotspots & Spatial Concentration
        story.append(Paragraph("4. Mekânsal Kümelenme ve Odak Noktaları (Getis-Ord G*)", section_heading))
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
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(hs_table)
        story.append(Spacer(1, 10))

        # 6. Methodology & Weights
        story.append(Paragraph("5. Analiz Metodolojisi ve Ağırlık Katsayıları", section_heading))
        method_text = (
            "Bu analiz, <b>Sentinel-1 C-Bant SAR</b> radar geri saçılım değişimi (%35), "
            "<b>Sentinel-2 MSI</b> optik bantlarından türetilen <b>ΔNDMI</b> nem kaybı indeksi (%25) ve "
            "<b>ΔNDRE</b> klorofil/vejetasyon sağlığı indeksi (%20) ile <b>Open-Meteo & ERA5</b> meteorolojik ekstrem "
            "doğrulama katsayılarının (%20) ağırlıklı lineer füzyon modeli (Weighted Fusion Strategy) ile hesaplanmıştır."
        )
        story.append(Paragraph(method_text, body_style))
        story.append(Spacer(1, 14))

        # 7. Official Sign-off & Verification Footer
        story.append(Paragraph("6. Resmi Tasdik ve Islak İmza Onayı", section_heading))
        
        sign_data = [
            [
                Paragraph("<b>Raporu Düzenleyen / Ziraat Müh.</b><br/><br/><br/>İsim: .......................................<br/>İmza: ......................................", body_style),
                Paragraph("<b>Tarımsal Hasar Eksperi</b><br/><br/><br/>İsim: .......................................<br/>İmza: ......................................", body_style),
                Paragraph("<b>Arazi Sahibi / Çiftçi</b><br/><br/><br/>İsim: .......................................<br/>İmza: ......................................", body_style)
            ]
        ]
        sign_table = Table(sign_data, colWidths=[170, 175, 175])
        sign_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(sign_table)

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
