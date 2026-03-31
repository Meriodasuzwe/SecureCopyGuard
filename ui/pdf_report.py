# ui/pdf_report.py
"""
Генерация PDF-отчёта об инцидентах через reportlab.
Зависимость: reportlab==4.1.0 (уже в requirements.txt)
"""

import time
import socket
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

from db.database import Database


# ── Цвета фирменного стиля ─────────────────────────────────────────────
C_BLUE    = colors.HexColor("#1D40AF")   # заголовок
C_DARK    = colors.HexColor("#0F172A")   # основной текст
C_MUTED   = colors.HexColor("#64748B")   # второстепенный
C_RED     = colors.HexColor("#B91C1C")   # High угрозы
C_ORANGE  = colors.HexColor("#B45309")   # Medium
C_GREEN   = colors.HexColor("#065F46")   # Low / OK
C_BG      = colors.HexColor("#F1F5F9")   # фон шапки таблицы
C_ROW_ALT = colors.HexColor("#F8FAFC")   # чередование строк


def generate_report(output_dir: str = "reports") -> str | None:
    """
    Формирует PDF-отчёт и возвращает путь к файлу.
    Возвращает None при ошибке.
    """
    try:
        Path(output_dir).mkdir(exist_ok=True)
        filename  = Path(output_dir) / f"DLP_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        hostname  = socket.gethostname()
        timestamp = time.strftime("%d.%m.%Y %H:%M:%S")

        db    = Database()
        logs  = db.get_recent_logs(100)
        stats = db.get_stats_by_module()

        doc   = SimpleDocTemplate(
            str(filename),
            pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=20*mm,  bottomMargin=20*mm,
        )

        story = []
        styles = getSampleStyleSheet()

        # ── Заголовок ──────────────────────────────────────────────────
        title_style = ParagraphStyle(
            "DLPTitle",
            fontSize=22, textColor=C_BLUE,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
            spaceAfter=4
        )
        sub_style = ParagraphStyle(
            "DLPSub",
            fontSize=10, textColor=C_MUTED,
            alignment=TA_CENTER, fontName="Helvetica",
            spaceAfter=12
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
            fontName="Helvetica-Bold", spaceAfter=8
        )
        story.append(Paragraph("Сводка по модулям защиты", section_style))

        stats_data = [["Модуль", "Уровень угрозы", "Инцидентов"]]
        for row in stats:
            module, level, count = row[0], row[1], row[2]
            stats_data.append([module, level, str(count)])

        if len(stats_data) == 1:
            stats_data.append(["Нет данных", "—", "0"])

        stats_table = Table(
            stats_data,
            colWidths=[95*mm, 50*mm, 30*mm]
        )
        stats_table.setStyle(TableStyle([
            # Шапка
            ("BACKGROUND",   (0, 0), (-1, 0),  C_BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  10),
            ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
            ("BOTTOMPADDING",(0, 0), (-1, 0),  8),
            ("TOPPADDING",   (0, 0), (-1, 0),  8),
            # Данные
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 9),
            ("ALIGN",        (2, 1), (2, -1),  "CENTER"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING",   (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ]))

        # Раскрашиваем уровни угроз
        for i, row in enumerate(stats_data[1:], start=1):
            level = row[1]
            color = C_RED if level == "High" else C_ORANGE if level == "Medium" else C_MUTED
            stats_table.setStyle(TableStyle([
                ("TEXTCOLOR", (1, i), (1, i), color),
                ("FONTNAME",  (1, i), (1, i), "Helvetica-Bold"),
            ]))

        story.append(stats_table)
        story.append(Spacer(1, 16))

        # ── Журнал инцидентов ──────────────────────────────────────────
        story.append(Paragraph("Журнал инцидентов (последние 100)", section_style))

        log_data = [["Время", "Уровень", "Модуль", "Описание"]]
        for row in logs:
            ts, module, level, details = row
            log_data.append([
                str(ts)[:19],
                str(level),
                str(module)[:20],
                str(details)[:80],
            ])

        if len(log_data) == 1:
            log_data.append(["—", "—", "—", "Инцидентов не зафиксировано"])

        log_table = Table(
            log_data,
            colWidths=[38*mm, 20*mm, 35*mm, 82*mm]
        )
        log_table.setStyle(TableStyle([
            # Шапка
            ("BACKGROUND",    (0, 0), (-1, 0),  C_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            # Данные
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("WORDWRAP",      (3, 1), (3, -1),  True),
        ]))

        # Раскрашиваем уровни в журнале
        for i, row in enumerate(log_data[1:], start=1):
            level = row[1]
            if level == "High":
                log_table.setStyle(TableStyle([
                    ("TEXTCOLOR", (1, i), (1, i), C_RED),
                    ("FONTNAME",  (1, i), (1, i), "Helvetica-Bold"),
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
            alignment=TA_CENTER, fontName="Helvetica-Oblique",
            spaceBefore=6
        )
        story.append(Paragraph(
            "Отчёт сформирован автоматически системой SecureCopyGuard DLP v2.0",
            footer_style
        ))

        doc.build(story)
        print(f"[PDF] Отчёт сохранён: {filename}")
        return str(filename)

    except Exception as exc:
        print(f"[PDF] Ошибка генерации отчёта: {exc}")
        return None