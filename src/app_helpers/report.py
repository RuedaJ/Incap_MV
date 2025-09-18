from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def build_pdf_report(
    out_dir: Path,
    title: str,
    author: str,
    notes: str,
    counts: Dict[str, int],
    rulepack_file: str,
) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"screening_summary_{ts}.pdf"

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, height - 2.5 * cm, title)

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 3.2 * cm, f"Author: {author}")
    c.drawString(2 * cm, height - 3.8 * cm, f"Generated (UTC): {datetime.utcnow().isoformat(timespec='seconds')}")

    # Counts
    y = height - 5.0 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Overall risk counts")
    y -= 0.8 * cm
    c.setFont("Helvetica", 11)
    for k in ["High", "Medium", "Low", None]:
        label = "Unassigned" if k is None else k
        v = counts.get(k, 0)
        c.drawString(2.5 * cm, y, f"{label}: {v}")
        y -= 0.6 * cm

    # Notes & rulepack
    y -= 0.4 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Notes")
    y -= 0.7 * cm
    c.setFont("Helvetica", 10)
    textobj = c.beginText(2 * cm, y)
    for line in notes.splitlines() or ["(none)"]:
        textobj.textLine(line)
    c.drawText(textobj)

    y = 3.0 * cm
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y, f"Rulepack: {rulepack_file}")
    y -= 0.6 * cm
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2 * cm, y, "Prototype output – not for external distribution.")

    c.showPage()
    c.save()
    return str(out_path)
