import fitz  # PyMuPDF
import os
import sys
import getpass  # Sicheres Passwort-Eingabefeld
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)

def update_metadata(new_doc, original_doc=None):
    """Aktualisiert die Metadaten des neuen Dokuments.
    Wenn ein Originaldokument übergeben wird, werden dessen Metadaten übernommen und ergänzt."""
    metadata = original_doc.metadata.copy() if original_doc else new_doc.metadata.copy()
    
    logging.debug("Metadata update_metadata (vorher): %s", metadata)
    
    script_name = os.path.basename(sys.argv[0])
    custom_info = f"Bearbeitet mit {script_name} | Kontakt: Jens Bergmann (jens.bergmann@ewe.de)"
    
    metadata.setdefault("producer", script_name)
    metadata.setdefault("author", "Jens Bergmann")
    
    metadata["subject"] = metadata.get("subject", "") + " | " + custom_info if "subject" in metadata else custom_info
    
    logging.debug("Metadata update_metadata (nachher): %s", metadata)
    new_doc.set_metadata(metadata)
def unlock_pdf(input_pdf):
    folder, filename = os.path.split(input_pdf)
    name, ext = os.path.splitext(filename)
    output_pdf = os.path.join(folder, f"{name}_unlocked{ext}")

    doc = fitz.open(input_pdf)

    # Prüfen, ob das PDF verschlüsselt ist (komplett gesperrt)
    if doc.needs_pass:
        print("Das PDF ist verschlüsselt und benötigt ein Passwort zum Entsperren.")
        password = getpass.getpass("Passwort eingeben (leer lassen zum Abbrechen): ").strip()

        if not password:
            print("Abbruch: Kein Passwort eingegeben.")
            return

        if not doc.authenticate(password):
            print("Fehler: Falsches Passwort.")
            return
    
    # Prüfen, ob das PDF Einschränkungen hat
    if doc.permissions < fitz.PDF_PERM_PRINT:
        print("Das PDF hat Einschränkungen (z. B. Kopierschutz oder Bearbeitungsschutz) - diese werden entfernt.")
    
    update_metadata(doc)
    
    # PDF speichern (entfernt automatisch alle Einschränkungen)
    doc.save(output_pdf)
    print(f"PDF erfolgreich entsperrt: {output_pdf}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung: python script.py <pfad_zur_pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    
    if not os.path.isfile(input_pdf):
        print(f"Fehler: Datei '{input_pdf}' nicht gefunden.")
        sys.exit(1)

    unlock_pdf(input_pdf)
