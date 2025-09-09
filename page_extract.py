import fitz  # PyMuPDF
import argparse
import os
import sys
import logging

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)

def update_metadata(new_doc, original_doc=None, first_page=None, last_page=None):
    metadata = original_doc.metadata.copy() if original_doc else new_doc.metadata.copy()
    script_name = os.path.basename(sys.argv[0])
    kontakt_info = f"{script_name} | Kontakt: Jens Bergmann (jens.bergmann@ewe.de)"

    # Producer ergänzen
    existing_producer = metadata.get("producer", "")
    if kontakt_info not in existing_producer:
        metadata["producer"] = f"{existing_producer} | {kontakt_info}".strip(" |")

    # Author nur setzen, wenn leer
    metadata.setdefault("author", "Jens Bergmann")

    # Keywords ergänzen
    existing_keywords = metadata.get("keywords", "")
    neue_keywords = ["automatisiert erstellt", "PDF-Auszug", "Script"]
    for keyword in neue_keywords:
        if keyword not in existing_keywords:
            existing_keywords += f", {keyword}" if existing_keywords else keyword
    metadata["keywords"] = existing_keywords

    # Seitenangabe
    if first_page and last_page:
        seiteninfo = (
            f"PDF-Auszug Seite {first_page}"
            if first_page == last_page
            else f"PDF-Auszug Seiten {first_page}–{last_page}"
        )
    else:
        seiteninfo = "PDF-Auszug"

    # Subject setzen
    existing_subject = metadata.get("subject", "").strip()
    if existing_subject:
        metadata["subject"] = f"{seiteninfo} | {existing_subject}"
    else:
        filename = os.path.splitext(os.path.basename(original_doc.name if original_doc else "Datei"))[0]
        metadata["subject"] = f"{seiteninfo} | {filename}"

    new_doc.set_metadata(metadata)
    logging.info(f"Metadaten aktualisiert: subject = '{metadata['subject']}'")

def extract_page_range(input_pdf, first_page, last_page, output_suffix=None):
    try:
        doc = fitz.open(input_pdf)
    except Exception as e:
        logging.error(f"Fehler beim Öffnen der Eingabedatei: {e}")
        sys.exit(1)

    new_doc = fitz.open()
    first_page_index = first_page - 1
    last_page_index = last_page - 1

    if first_page_index < 0 or last_page_index >= len(doc) or first_page_index > last_page_index:
        logging.error(f"Ungültiger Seitenbereich ({first_page}-{last_page}). PDF hat {len(doc)} Seiten.")
        doc.close()
        sys.exit(1)

    try:
        new_doc.insert_pdf(doc, from_page=first_page_index, to_page=last_page_index)
    except Exception as e:
        logging.error(f"Fehler beim Einfügen der Seiten: {e}")
        doc.close()
        new_doc.close()
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(input_pdf))[0]
    output_dir = os.path.dirname(input_pdf)
    if output_suffix is None:
        output_suffix = f"Seite_{first_page}" if first_page == last_page else f"Auszug_{first_page}_{last_page}"
    output_pdf = os.path.join(output_dir, f"{base_name}_{output_suffix}.pdf")

    update_metadata(new_doc, doc, first_page, last_page)

    try:
        new_doc.save(output_pdf)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Ausgabedatei: {e}")
        doc.close()
        new_doc.close()
        sys.exit(1)

    new_doc.close()
    doc.close()
    logging.info(f"Extrahiert: Seite(n) {first_page} bis {last_page} → '{output_pdf}'")
    return output_pdf

def split_pdf(input_pdf, pages_per_file):
    try:
        doc = fitz.open(input_pdf)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        logging.error(f"Fehler beim Öffnen der Eingabedatei für Split: {e}")
        sys.exit(1)

    created_files = []
    for start_page in range(1, total_pages + 1, pages_per_file):
        end_page = min(start_page + pages_per_file - 1, total_pages)
        output_suffix = f"Split_{start_page}_{end_page}"
        output_file = extract_page_range(input_pdf, start_page, end_page, output_suffix)
        if output_file:
            created_files.append(output_file)
        else:
            logging.warning(f"Keine Datei erzeugt für Seiten {start_page}-{end_page}.")

    if not created_files:
        logging.error("Keine Ausgabedateien erzeugt.")
        sys.exit(1)

    logging.info(f"Split abgeschlossen. {len(created_files)} Dateien erzeugt.")
    return created_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrahiere Seiten oder splitte ein PDF.")
    parser.add_argument("input_pdf", help="Pfad zur Eingabedatei")
    parser.add_argument("start", nargs="?", type=int, help="Startseite (ab 1)")
    parser.add_argument("end", nargs="?", type=int, help="Endseite (ab 1)")
    parser.add_argument("--split", type=int, metavar="SEITEN_PRO_DATEI", help="PDF in Blöcke aufteilen (z. B. --split 5)")

    args = parser.parse_args()

    if args.split:
        split_pdf(args.input_pdf, args.split)
    elif args.start and args.end:
        extract_page_range(args.input_pdf, args.start, args.end)
    elif args.start:
        extract_page_range(args.input_pdf, args.start, args.start)
    else:
        parser.print_help()
        sys.exit(1)
