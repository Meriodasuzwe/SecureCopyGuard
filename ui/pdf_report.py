# ui/pdf_report.py
"""
Генерация PDF-отчёта об инцидентах через reportlab.
Зависимость: reportlab==4.1.0
"""

import time
import socket
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрируем кириллические шрифты
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    FONT_REGULAR = 'Arial'
    FONT_BOLD = 'Arial-Bold'
except Exception:
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

from db.database import Database

# ── Цвета фирменного стиля ─────────────────────────────────────────────
C_BLUE    = colors.HexColor("#1D40AF")
C_DARK    = colors.HexColor("#0F172A")
C_MUTED   = colors.HexColor("#64748B")
C_RED     = colors.HexColor("#B91C1C")
C_ORANGE  = colors.HexColor("#B45309")
C_GREEN   = colors.HexColor("#065F46")
C_BG      = colors.HexColor("#F1F5F9")
C_ROW_ALT = colors.HexColor("#F8FAFC")


def generate_report(output_dir: str = "reports") -> str | None:
    try:
        Path(output_dir).mkdir(exist_ok=True)
        filename  = Path(output_dir) / f"DLP_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        hostname  = socket.gethostname()
        timestamp = time.strftime("%d.%m.%Y %H:%M:%S")

        db    = Database()
        logs  = db.get_recent_logs(100)
        stats = db.get_stats_by_module()

        doc   = SimpleDocTemplate(
            str(filename), pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=20*mm,  bottomMargin=20*mm,
        )

        story = []
        
        # ── Заголовок (Исправлен баг с наложением через leading) ───────────
        title_style = ParagraphStyle(
            "DLPTitle",
            fontSize=20, textColor=C_BLUE,
            alignment=TA_CENTER, fontName=FONT_BOLD,
            spaceAfter=10, leading=26 # Жёстко задаем высоту строки
        )
        sub_style = ParagraphStyle(
            "DLPSub",
            fontSize=10, textColor=C_MUTED,
            alignment=TA_CENTER, fontName=FONT_REGULAR,
            spaceAfter=16, leading=14
        )

        story.append(Paragraph("SecureCopyGuard — Отчёт об инцидентах", title_style))
        story.append(Paragraph(
            f"Хост: <b>{hostname}</b> &nbsp;|&nbsp; Сформирован: <b>{timestamp}</b>",
            sub_style
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=14))

        # ── Сводка по модулям ──────────────────────────────────────────
        section_style = ParagraphStyle(
            "Section",
            fontSize=13, textColor=C_DARK,
            fontName=FONT_BOLD, spaceAfter=8
        )
        story.append(Paragraph("Сводка по модулям защиты", section_style))

        stats_data = [["Модуль", "Уровень угрозы", "Инцидентов"]]
        for row in stats:
            module, level, count = row[0], row[1], row[2]
            stats_data.append([module, level, str(count)])

        if len(stats_data) == 1:
            stats_data.append(["Нет данных", "—", "0"])

        # Ширина 170mm (ровно под А4 с отступами)
        stats_table = Table(stats_data, colWidths=[90*mm, 50*mm, 30*mm])
        stats_table.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  C_BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  FONT_BOLD),
            ("FONTSIZE",     (0, 0), (-1, 0),  10),
            ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
            ("BOTTOMPADDING",(0, 0), (-1, 0),  8),
            ("TOPPADDING",   (0, 0), (-1, 0),  8),
            ("FONTNAME",     (0, 1), (-1, -1), FONT_REGULAR),
            ("FONTSIZE",     (0, 1), (-1, -1), 9),
            ("ALIGN",        (2, 1), (2, -1),  "CENTER"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING",   (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ]))

        for i, row in enumerate(stats_data[1:], start=1):
            level = row[1]
            color = C_RED if level == "High" else C_ORANGE if level == "Medium" else C_MUTED
            stats_table.setStyle(TableStyle([
                ("TEXTCOLOR", (1, i), (1, i), color),
                ("FONTNAME",  (1, i), (1, i), FONT_BOLD),
            ]))

        story.append(stats_table)
        story.append(Spacer(1, 16))

        # ── Журнал инцидентов ──────────────────────────────────────────
        story.append(Paragraph("Журнал инцидентов (последние 100)", section_style))

        # 🔥 Специальный стиль для ячеек, чтобы текст АВТОМАТИЧЕСКИ ПЕРЕНОСИЛСЯ
        cell_style = ParagraphStyle(
            "TableCell",
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=11 # Межстрочный интервал внутри ячейки
        )

        log_data = [["Время", "Уровень", "Модуль", "Описание"]]
        for row in logs:
            ts, module, level, details = row
            # Оборачиваем длинные тексты в Paragraph()
            log_data.append([
                str(ts)[:19], 
                str(level), 
                Paragraph(str(module), cell_style), 
                Paragraph(str(details), cell_style)
            ])

        if len(log_data) == 1:
            log_data.append(["—", "—", "—", "Инцидентов не зафиксировано"])

        # Ширина 170mm: 35 + 18 + 35 + 82
        log_table = Table(log_data, colWidths=[35*mm, 18*mm, 35*mm, 82*mm])
        log_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  C_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  FONT_BOLD),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"), # Центрируем всё по вертикали
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            ("FONTNAME",      (0, 1), (-1, -1), FONT_REGULAR),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING",    (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ]))

        for i, row in enumerate(log_data[1:], start=1):
            level = row[1]
            if level == "High":
                log_table.setStyle(TableStyle([
                    ("TEXTCOLOR", (1, i), (1, i), C_RED),
                    ("FONTNAME",  (1, i), (1, i), FONT_BOLD),
                ]))
            elif level == "Medium":
                log_table.setStyle(TableStyle([
                    ("TEXTCOLOR", (1, i), (1, i), C_ORANGE),
                ]))

        story.append(log_table)
        story.append(Spacer(1, 20))

        # ── Подпись ────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1, color=C_BG))
        footer_style = ParagraphStyle(
            "Footer",
            fontSize=8, textColor=C_MUTED,
            alignment=TA_CENTER, fontName=FONT_REGULAR,
            spaceBefore=6
        )
        story.append(Paragraph(
            "Отчёт сформирован автоматически системой SecureCopyGuard DLP Enterprise",
            footer_style
        ))

        doc.build(story)
        return str(filename)

    except Exception as exc:
        print(f"[PDF] Ошибка генерации отчёта: {exc}")
        return None