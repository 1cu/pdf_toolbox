import fitz  # PyMuPDF
from PIL import Image
import sys
import os

def pdf_to_multipage_tiff(pdf_path):
    # Verzeichnis und Standarddateinamen festlegen
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.dirname(pdf_path)
    tiff_path = os.path.join(output_dir, f"{base_name}.tiff")

    # PDF öffnen
    doc = fitz.open(pdf_path)

    # Seiten in Bilder konvertieren
    images = []
    for page in doc:
        pix = page.get_pixmap(alpha=False)  # Pixmap ohne Transparenz
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    # Prüfen, ob Bilder vorhanden sind
    if not images:
        print("Fehler: Keine Seiten gefunden.")
        return

    # Multipage-TIFF speichern
    images[0].save(tiff_path, save_all=True, append_images=images[1:], compression="tiff_deflate")
    print(f"Multipage TIFF gespeichert: {tiff_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Verwendung: python {os.path.basename(sys.argv[0])} <eingabe.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]

    # Prüfen, ob die Eingabedatei existiert
    if not os.path.isfile(input_pdf):
        print(f"Fehler: Datei nicht gefunden: {input_pdf}")
        sys.exit(1)

    pdf_to_multipage_tiff(input_pdf)
