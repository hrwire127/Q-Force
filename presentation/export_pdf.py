"""Make a presentation-sized PDF from the deck's rendered slide PNGs."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
PNGS = sorted((ROOT.parent / ".presentation-build").glob("slide-*.png"))
OUT = ROOT / "Q-Force_Quantum_Railways_Final.pdf"

if len(PNGS) != 19:
    raise SystemExit(f"Expected 19 slide previews, found {len(PNGS)}")

pdf = canvas.Canvas(str(OUT), pagesize=(960, 540), pageCompression=1)
pdf.setTitle("Q-Force — Quantum Railways")
pdf.setAuthor("Q-Force")
for png in PNGS:
    pdf.drawImage(ImageReader(str(png)), 0, 0, 960, 540, preserveAspectRatio=False)
    pdf.showPage()
pdf.save()
print(OUT)
