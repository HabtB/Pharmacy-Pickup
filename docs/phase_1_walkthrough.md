# Phase 1: Security Hardening — Walkthrough

## Changes Made

### 1.1 — API Key Exposure Fixed
| File | Change |
|------|--------|
| [api_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/config/api_config.dart) | Removed debug logging that exposed API key presence/length; removed unused `AppLogger` import |
| [main.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/main.dart) | Removed log line that revealed whether `GROK_API_KEY` was loaded |
| [.env.example](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/.env.example) | **[NEW]** Template file showing required env vars without real keys |

> [!IMPORTANT]
> You should **rotate your Grok API key** at https://x.ai/api since the old key was in the `.env` file. If it was ever committed to git, also scrub history with `git filter-repo`.

---

### 1.2 — Hardcoded Credentials Removed
| File | Change |
|------|--------|
| [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py) | Default user passwords now read from `ADMIN_PASSWORD` / `PICKER_PASSWORD` env vars; logs warning if not set |
| [database_manager.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/database_manager.py) | Removed hardcoded `admin123`/`user123` seeding at module load |

---

### 1.3 — JWT Token Authentication
| File | Change |
|------|--------|
| [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py) | Login endpoint now returns a signed JWT (24hr expiry) using `PyJWT`; secret from `JWT_SECRET` env var |
| [auth_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/auth_service.dart) | **Rewritten** — JWT stored in `flutter_secure_storage` (encrypted at rest); added `getAuthHeaders()` for Bearer token on API calls |
| [pubspec.yaml](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/pubspec.yaml) | Added `flutter_secure_storage: ^9.2.4` |
| [requirements.txt](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/requirements.txt) | Added `PyJWT>=2.8.0`; deduplicated entries |

---

### 1.4 — HTTPS Enforcement
| File | Change |
|------|--------|
| [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart) | Added `isSecure` property; logs warning in release builds if not using HTTPS for PHI data |

---

### 1.5 — Database Deletion Bug Fixed
| File | Change |
|------|--------|
| [database_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/database_service.dart) | Replaced `const bool debugMode = true` with `kDebugMode` from `package:flutter/foundation.dart` — database is now only deleted in debug builds |

---

---

## Grok API Removal (User Request)

User confirmed the Grok API is no longer used. All related code was removed:

| File | Change |
|------|--------|
| [api_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/config/api_config.dart) | **[DELETED]** Entire file removed |
| [parsing_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/parsing_service.dart) | **Rewritten** — Removed `parseWithLLM`, `parseNumbersWithLLM`, and `http` import. `parseExtractedText` now regex-only (no API key parameter) |
| [process_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen.dart) | Removed `api_config.dart` import and `ApiConfig.grokApiKey` argument |
| [main.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/main.dart) | Removed `flutter_dotenv` import and `.env` loading block |
| [pubspec.yaml](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/pubspec.yaml) | Removed `flutter_dotenv: ^5.1.0` dependency |
| [.env](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/.env) | Removed Grok API key (only `DOCLING_SERVER_URL` remains) |
| [.env.example](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/.env.example) | Updated to remove `GROK_API_KEY` template |

---

## Verification

- **`flutter pub get`** — ✅ `flutter_dotenv` successfully removed
- **`flutter analyze lib/`** — ✅ 45 pre-existing warnings/infos only, 0 new issues
