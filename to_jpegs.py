import fitz  # PyMuPDF
from PIL import Image
import sys
import os

def pdf_to_jpegs(pdf_path, start_page=None, end_page=None):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.dirname(pdf_path)

    doc = fitz.open(pdf_path)

    if doc.page_count == 0:
        print("Fehler: Keine Seiten gefunden.")
        return

    # Begrenzung festlegen
    start = start_page - 1 if start_page else 0
    end = end_page if end_page else doc.page_count

    if start < 0 or end > doc.page_count or start >= end:
        print(f"Fehler: Ungültiger Seitenbereich (PDF hat {doc.page_count} Seiten).")
        return

    for i in range(start, end):
        page = doc[i]
        pix = page.get_pixmap(alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        jpeg_path = os.path.join(output_dir, f"{base_name}_Seite_{i + 1}.jpg")
        img.save(jpeg_path, "JPEG", quality=95)
        print(f"Seite {i + 1} gespeichert: {jpeg_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print(f"Verwendung:\n  python {os.path.basename(sys.argv[0])} <eingabe.pdf> [start] [ende]")
        print("Beispiel:\n  python script.py datei.pdf         # alle Seiten\n"
              "  python script.py datei.pdf 3        # nur Seite 3\n"
              "  python script.py datei.pdf 3 5      # Seiten 3 bis 5")
        sys.exit(1)

    input_pdf = sys.argv[1]

    if not os.path.isfile(input_pdf):
        print(f"Fehler: Datei nicht gefunden: {input_pdf}")
        sys.exit(1)

    start = int(sys.argv[2]) if len(sys.argv) >= 3 else None
    end = int(sys.argv[3]) if len(sys.argv) == 4 else start

    pdf_to_jpegs(input_pdf, start, end)
