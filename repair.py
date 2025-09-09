import fitz
import sys
import os
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

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

def repair_pdf(input_pdf):
    """ Repariert eine beschädigte PDF und speichert sie neu """
    try:
        logger.info(f"Repariere PDF: {input_pdf}")
        input_folder, input_filename = os.path.split(input_pdf)
        filename_no_ext, file_extension = os.path.splitext(input_filename)
        output_filename = f"{filename_no_ext}_repaired{file_extension}"
        output_pdf = os.path.join(input_folder, output_filename)
        doc = fitz.open(input_pdf)

        update_metadata(doc)

        doc.save(output_pdf, garbage=4, clean=True, incremental=False)
        doc.close()
        logger.info(f"Reparierte Datei gespeichert: {output_pdf}")
    except Exception as e:
        logger.error(f"Fehler beim Reparieren der PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repariert eine beschädigte PDF-Datei")
    parser.add_argument("input_pdf", help="Pfad zur Eingabe-PDF")
    parser.add_argument("-d", "--debug", action="store_true", help="Aktiviert den Debug-Modus")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    repair_pdf(args.input_pdf)
