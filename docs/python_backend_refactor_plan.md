# Python Backend Refactor — Modularize `docling_server.py`

`docling_server.py` is **1,159 lines** doing routing, parsing, image conversion, and app setup in one file. The `python_server/` directory has **65 flat files** including backups, debug scripts, and an 8.9MB log.

## Current Structure (flat)

```
python_server/
├── docling_server.py          # 1,159 lines — EVERYTHING
├── database_manager.py        # ✅ Already separate
├── google_vision_ocr.py       # ✅ Already separate  
├── enhanced_medication_parser.py  # ✅ Already separate
├── medication_location_lookup.py  # ✅ Already separate
├── medspacy_parser.py         # ✅ Already separate
├── floor_stock_parser.py      # ✅ Already separate (116KB)
├── llm_medication_parser.py   # ✅ Already separate
├── 20+ debug/test scripts     # ❌ Cluttering directory
├── 5+ log files (8.9MB+)      # ❌ Should be gitignored
└── 2 backup parser files      # ❌ Should be deleted
```

## Proposed Structure

```
python_server/
├── app.py                     # Flask app factory + startup (slim entry point)
├── config.py                  # [NEW] Environment config (JWT secret, debug mode, credentials)
├── routes/
│   ├── __init__.py
│   ├── auth.py                # /api/login, /api/save_session
│   ├── health.py              # /health
│   └── parsing.py             # /parse-document, /parse-documents-parallel
├── services/
│   ├── __init__.py
│   └── image_service.py       # convert_image_to_pdf
├── parsers/
│   ├── __init__.py
│   └── text_parsers.py        # extract_medication_data, parse_*_data, fix_common_ocr_errors
├── database_manager.py        # (unchanged)
├── google_vision_ocr.py       # (unchanged)
├── enhanced_medication_parser.py  # (unchanged)
├── medication_location_lookup.py  # (unchanged)
├── medspacy_parser.py         # (unchanged)
├── floor_stock_parser.py      # (unchanged)
├── llm_medication_parser.py   # (unchanged)
├── requirements.txt           # (unchanged)
└── scripts/                   # [MOVE] debug/test scripts (out of root)
```

---

## Proposed Changes

### [NEW] `config.py` — Centralized Configuration
- `FLASK_DEBUG`, `JWT_SECRET`, `ADMIN_USERNAME/PASSWORD`, `PICKER_USERNAME/PASSWORD`
- All read from env vars with sensible dev defaults

### [NEW] `app.py` — Flask App Factory
- Creates Flask app, registers Blueprints
- Initializes Google Vision, Docling converter, database seeding
- `if __name__ == '__main__'` entry point
- **Replaces** `docling_server.py` as the entry point

### [NEW] `routes/auth.py` — Auth Blueprint
- `login()` endpoint (JWT generation)
- `save_session()` endpoint

### [NEW] `routes/health.py` — Health Blueprint
- `health_check()` endpoint

### [NEW] `routes/parsing.py` — Parsing Blueprint
- `parse_document()` — single image (multipart + base64 fallback)
- `parse_documents_parallel()` — batch images (multipart + base64 fallback)

### [NEW] `services/image_service.py` — Image Utilities
- `convert_image_to_pdf()` function

### [NEW] `parsers/text_parsers.py` — Text Parsing Utilities
- `extract_medication_data()`, `parse_floor_stock_data()`, `parse_cart_fill_data()`
- `parse_table_for_medications()`, `find_column_index()`
- `parse_text_for_floor_stock()`, `parse_text_for_medications()`
- `fix_common_ocr_errors()`, `parse_medication_text()`

### [DELETE] `docling_server.py`
- Replaced by `app.py` + modules

### [MOVE] Debug/Test Scripts → `scripts/`
- Move `debug_*.py`, `test_*.py`, `analyze_*.py`, `diagnose_*.py`, `dump_log.py`, `fix_csv*.py`, `organize_images.py`, `generate_report.py`, `update_csv_manual.py` into `scripts/`

### [DELETE] Backup Files
- `floor_stock_parser_backup_20251020_0545.py`
- `floor_stock_parser_backup_before_hybrid_20251107_1537.py`
- `medication_locations_backup.csv`, `medication_locations_backup_v2.csv`
- `fixed_server.py`, `medication_parser_fix.py`, `floor_stock_parser_hybrid_methods.py`

### `.gitignore` Updates
- Add `*.log`, `*.pid`, `recent_log.txt` patterns

---

## Verification

```bash
# Start the new server
cd python_server && python app.py

# Verify health endpoint
curl http://localhost:5003/health

# Verify login
curl -X POST http://localhost:5003/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Flutter tests still pass
cd .. && flutter test test/controllers/ test/models/
```
