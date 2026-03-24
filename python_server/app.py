#!/usr/bin/env python3
"""
Pharmacy Picker OCR Server — Flask application entry point.

Modular architecture:
  routes/auth.py        — login, save_session
  routes/health.py      — /health
  routes/parsing.py     — /parse-document, /parse-documents-parallel
  services/image_service.py — convert_image_to_pdf
  parsers/text_parsers.py   — text/table extraction helpers
  config.py             — centralized environment configuration
"""

import os
import logging

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import config
import database_manager
from google_vision_ocr import GoogleVisionOCR
from medication_location_lookup import get_location_lookup

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# Rate limiter — 5 login attempts per minute per IP
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],  # no global limit — only on specific routes
    storage_uri='memory://',
)

# ── Initialize Services ─────────────────────────────────────────────────────
google_vision = GoogleVisionOCR()
logger.info("Google Vision OCR initialized")

# Check Grok API key
if not os.getenv('GROK_API_KEY'):
    logger.warning("⚠️ GROK_API_KEY is missing — LLM extraction fallback will fail.")
else:
    logger.info("✓ GROK_API_KEY found. LLM extraction enabled.")

# ── Docling Converter ────────────────────────────────────────────────────────
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    logger.info("Using Google Cloud Vision OCR engine")
    try:
        from docling.models.gcs_ocr_model import GcsOcrOptions
        ocr_options = GcsOcrOptions()
        pipeline_options.ocr_options = ocr_options
        logger.info("✓ Google Cloud Vision OCR configured successfully")
    except ImportError:
        logger.warning("Google Cloud Vision OCR not available, using default")
    except Exception as e:
        logger.warning(f"Could not configure Google Cloud Vision OCR: {e}")

if not hasattr(pipeline_options, 'ocr_options') or pipeline_options.ocr_options is None:
    logger.info("Using default OCR engine (Tesseract/EasyOCR)")

format_options = {
    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
}
converter = DocumentConverter(format_options=format_options)

# ── Seed Default Users ───────────────────────────────────────────────────────
database_manager.init_db()

admin_pass = config.ADMIN_PASSWORD
picker_pass = config.PICKER_PASSWORD

if not admin_pass or not picker_pass:
    logger.warning("ADMIN_PASSWORD / PICKER_PASSWORD env vars not set — using insecure defaults. Set them in production!")
    admin_pass = admin_pass or 'admin123'
    picker_pass = picker_pass or 'user123'

database_manager.create_user(config.ADMIN_USERNAME, admin_pass, 'admin')
database_manager.create_user(config.PICKER_USERNAME, picker_pass, 'picker')

# ── Medication Locations DB ──────────────────────────────────────────────────
from models.medication_locations import init_locations_table, import_from_csv

init_locations_table()
imported = import_from_csv()  # One-time import from CSV (skips if data exists)
logger.info(f"Medication locations: {imported} rows in database")

# ── Register Blueprints ──────────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.health import health_bp
from routes.parsing import parsing_bp, init_google_vision
from routes.locations import locations_bp

# Share the google_vision singleton with the parsing blueprint
init_google_vision(google_vision)

app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)
app.register_blueprint(parsing_bp)
app.register_blueprint(locations_bp)

# Apply rate limit to login endpoint (5 attempts/minute per IP)
limiter.limit('5/minute')(app.view_functions['auth.login'])

logger.info("All blueprints registered: auth, health, parsing")
logger.info("Rate limiting: 5 login attempts/minute per IP")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Starting Enhanced OCR Server with Google Vision...")

    # Preload the location database at startup
    print("Preloading medication location database...")
    try:
        location_lookup_preload = get_location_lookup()
        print(f"✓ Preloaded {len(location_lookup_preload.location_db)} medication locations")
    except Exception as e:
        print(f"Warning: Could not preload location database: {e}")

    print(f"Server will be available at: http://localhost:{config.SERVER_PORT}")
    print(f"Health check: http://localhost:{config.SERVER_PORT}/health")
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.FLASK_DEBUG
    )
