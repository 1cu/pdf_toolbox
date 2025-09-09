import fitz
import sys
import os
import logging
import argparse
from PIL import Image
import io

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# Qualitätsprofile für PDF- und Bildkomprimierung
QUALITY_SETTINGS = {
    "screen": {"pdf_quality": 50, "image_quality": 40, "min_reduction": 0.3},
    "ebook": {"pdf_quality": 75, "image_quality": 60, "min_reduction": 0.2},
    "printer": {"pdf_quality": 90, "image_quality": 85, "min_reduction": 0.1},
    "prepress": {"pdf_quality": 100, "image_quality": 95, "min_reduction": 0.05},
    "default": {"pdf_quality": 80, "image_quality": 75, "min_reduction": 0.15}
}

def update_metadata(new_doc, original_doc=None):
    """Aktualisiert die Metadaten des neuen Dokuments.
    Wenn ein Originaldokument übergeben wird, werden dessen Metadaten übernommen und ergänzt."""
    metadata = original_doc.metadata.copy() if original_doc else new_doc.metadata.copy()
    
    logging.debug("Metadata update_metadata (vorher): %s", metadata)
    
    script_name = os.path.basename(sys.argv[0])
    custom_info = f"Bearbeitet mit {script_name} | Kontakt: Jens B. (1742418+1cu@users.noreply.github.com)"
    
    metadata.setdefault("producer", script_name)
    metadata.setdefault("author", "Jens B.")
    
    metadata["subject"] = metadata.get("subject", "") + " | " + custom_info if "subject" in metadata else custom_info
    
    logging.debug("Metadata update_metadata (nachher): %s", metadata)
    new_doc.set_metadata(metadata)

def compress_images(doc, image_quality):
    """ Reduziert die Bildqualität in der PDF mit Fehlerbehandlung für nicht definierte Farbräume """
    for page in doc:
        images = page.get_images(full=True)
        for img in images:
            xref = img[0]  # XREF der Bildreferenz
            try:
                logger.debug(f"Verarbeite Bild auf Seite {page.number + 1}, XREF {xref}")
                pix = fitz.Pixmap(doc, xref)  # Bild laden
                logger.debug(f"Pixmap geladen: {pix.width}x{pix.height}, Kanäle: {pix.n}")
                
                if pix.colorspace is None:
                    logger.warning(f"Bild auf Seite {page.number + 1} hat keinen definierten Farbraum, Originalbild bleibt erhalten.")
                    continue
                
                if pix.n < 1 or pix.width == 0 or pix.height == 0 or pix.samples is None:
                    logger.warning(f"Ungültiges Bild auf Seite {page.number + 1}, Originalbild bleibt erhalten.")
                    continue
                
                # Falls das Bild ein 1-Kanal-Bild ist (Graustufen), konvertiere es in RGB
                if pix.n == 1:
                    logger.debug("Konvertiere Graustufenbild in RGB")
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                # Falls das Bild Transparenz enthält, konvertiere es ebenfalls in RGB
                if pix.n > 3:
                    logger.debug("Konvertiere Bild mit Transparenz in RGB")
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                # Bild in ein PIL-Image umwandeln
                logger.debug("Konvertiere Bild in PIL Image")
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_io = io.BytesIO()
                logger.debug("Speichere Bild als JPEG")
                img_pil.save(img_io, format="JPEG", quality=image_quality)
                img_data = img_io.getvalue()
                
                # Bild stream in die PDF aktualisieren
                logger.debug("Aktualisiere Bild in PDF")
                doc.update_stream(xref, img_data)
            except Exception as e:
                logger.error(f"Fehler bei Bildkomprimierung auf Seite {page.number + 1}: {e}, Originalbild bleibt erhalten.")

def optimize_pdf(input_pdf, quality="default", keep=False, debug=False, compress_images_flag=False):
    """ Optimiert eine PDF und speichert sie im selben Ordner """
    if quality not in QUALITY_SETTINGS:
        logger.error(f"Ungültige Qualitätsstufe: {quality}")
        sys.exit(1)

    # Debug-Modus aktivieren
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # Pfad und Dateiname aufteilen
    input_folder, input_filename = os.path.split(input_pdf)
    filename_no_ext, file_extension = os.path.splitext(input_filename)

    # Neues PDF im selben Ordner speichern
    output_filename = f"{filename_no_ext}_optimized_{quality}{file_extension}"
    output_pdf = os.path.join(input_folder, output_filename)

    # Qualitätsstufen abrufen
    pdf_quality = QUALITY_SETTINGS[quality]["pdf_quality"]
    image_quality = QUALITY_SETTINGS[quality]["image_quality"]
    min_reduction = QUALITY_SETTINGS[quality]["min_reduction"]

    logger.info(f"Starte Optimierung: {input_filename} (Qualität: {quality})")

    # Originalgröße abrufen
    original_size = os.path.getsize(input_pdf)

    # PDF öffnen
    doc = fitz.open(input_pdf)

    update_metadata(doc)

    # Bilder komprimieren nur wenn aktiviert
    if compress_images_flag:
        logger.warning("Bildkomprimierung ist aktiviert. Fehlerhafte oder fehlende Bilder werden explizit gewarnt!")
        compress_images(doc, image_quality)

    # PDF speichern mit Optimierungen
    doc.save(output_pdf, garbage=3, deflate=True, clean=True, incremental=False)
    doc.close()

    # Neue Größe abrufen
    optimized_size = os.path.getsize(output_pdf)
    reduction_ratio = 1 - (optimized_size / original_size)

    if reduction_ratio < min_reduction and not keep:
        os.remove(output_pdf)
        logger.warning(f"Keine signifikante Reduzierung (nur {reduction_ratio:.2%}). Datei wurde nicht gespeichert.")
    else:
        logger.info(f"PDF optimiert und gespeichert als: {output_filename} ({optimized_size / 1024:.2f} KB, Reduzierung: {reduction_ratio:.2%})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimiert eine PDF-Datei")
    parser.add_argument("input_pdf", help="Pfad zur Eingabe-PDF")
    parser.add_argument("quality", nargs="?", default="default", choices=QUALITY_SETTINGS.keys(), help="Qualitätsstufe der Optimierung")
    parser.add_argument("--keep", action="store_true", help="Erhält die optimierte Datei, auch wenn die Reduzierung gering ist")
    parser.add_argument("-d", "--debug", action="store_true", help="Aktiviert den Debug-Modus")
    parser.add_argument("--compress-images", action="store_true", help="Aktiviert die Bildkomprimierung")
    
    args = parser.parse_args()
    optimize_pdf(args.input_pdf, args.quality, args.keep, args.debug, args.compress_images)
