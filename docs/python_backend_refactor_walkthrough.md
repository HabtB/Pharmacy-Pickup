# Python Backend Refactor — Walkthrough

## What Changed

Split the monolithic `docling_server.py` (1,159 lines) into a modular Flask Blueprint architecture:

### New Structure

```
python_server/
├── app.py              ← Entry point (115 lines)
├── config.py           ← Environment config
├── routes/
│   ├── auth.py         ← /api/login, /api/save_session
│   ├── health.py       ← /health
│   └── parsing.py      ← /parse-document, /parse-documents-parallel
├── services/
│   └── image_service.py ← convert_image_to_pdf()
├── parsers/
│   └── text_parsers.py  ← text/table parsing helpers
├── scripts/             ← 34 debug/test scripts (moved from root)
└── (existing modules unchanged)
```

### Files Created (8)

| File | Lines | Responsibility |
|------|-------|---------------|
| `app.py` | ~115 | Flask factory, Blueprint registration, startup |
| `config.py` | ~25 | Env vars: `FLASK_DEBUG`, `JWT_SECRET`, credentials |
| `routes/auth.py` | ~70 | Login endpoint (JWT), save_session |
| `routes/health.py` | ~14 | Health-check |
| `routes/parsing.py` | ~350 | Both parse endpoints + deduplication + location enrichment |
| `services/image_service.py` | ~100 | Image→PDF conversion with enhancement |
| `parsers/text_parsers.py` | ~225 | 9 regex/table parsing functions |

### Directory Cleanup

| Action | Count |
|--------|-------|
| Debug/test scripts → `scripts/` | 34 files |
| Backup files deleted | 5 files |
| Log/PID files deleted | 4 files |
| `.gitignore` patterns added | `*_backup*`, `*.bak`, `*.pid`, `*.db` |
| Before | 65 flat files |
| After | 18 files + 4 subdirs |

### Key Design Decisions

- **Flask Blueprints** for route separation (no import-time side effects)
- **`google_vision` singleton** initialized in `app.py`, injected into parsing blueprint via `init_google_vision()`
- **`docling_server.py` kept** temporarily as reference — delete once server is tested live
- **Config centralized** in `config.py` — all env vars read in one place

## Test Results

- `flutter test test/controllers/ test/models/` — **40/40 pass** (Flutter client unchanged)
- Server testing requires `python app.py` in the `python_server/` directory
