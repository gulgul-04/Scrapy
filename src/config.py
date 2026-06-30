from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = BASE_DIR / "district_pdf_index.json"
MANIFEST_FILE = BASE_DIR / "pdf_manifest.json"
LOG_FILE = BASE_DIR / "download_failures.log"

PDF_MAGIC_BYTES = b"%PDF-"

CRIDA_TARGET_URL = "https://www.icar-crida.res.in/Crop_Contingency_Plan.html"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

INTERIM_DIR = DATA_DIR / "interim"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)

RAW_SOWING_DATA = INTERIM_DIR / "raw_pdf_sowing_data.csv"