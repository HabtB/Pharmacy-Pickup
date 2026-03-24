# Comprehensive Improvement Plan — Pharmacy Pickup App

> **Scope**: Full evaluation of GUI, architecture, code quality, efficiency, security, testing, error handling, DevOps, and developer experience.

---

## 🔴 Priority 1 — Critical (Security & Data Safety)

### 1.1 API Key Leaked in `.env`
The `.env` file contains a **live Grok API key in plain text** and is present in the working tree. Even though `.gitignore` lists `.env`, if it was ever committed, the key is in git history.

| File | Issue |
|------|-------|
| [.env](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/.env) | Live `GROK_API_KEY` = `xai-acqFZw...` exposed |
| [api_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/config/api_config.dart) | Logs key presence/length to debug console |

**Fix:**
- Rotate the API key immediately.
- Scrub git history with `git filter-repo` or BFG Repo Cleaner.
- Remove API key debug logging from `api_config.dart`.
- Use platform-specific secret injection (env vars at build time or `--dart-define`).

---

### 1.2 Hardcoded Credentials on Server
[docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py) creates default users at module load:
```python
database_manager.create_user('admin', 'admin123', 'admin')
database_manager.create_user('user', 'user123', 'picker')
```

**Fix:** Move to environment-variable-based seeding or a secure admin CLI. Never hardcode passwords.

---

### 1.3 No Authentication Tokens
[auth_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/auth_service.dart) stores `user_id`, `username`, and `role` in plain-text `SharedPreferences`. There is **no session token, no JWT, no expiry**.

**Fix:**
- Implement JWT-based auth on the server; return a signed token on login.
- Store the token in `flutter_secure_storage` (encrypted at rest).
- Attach the token as an `Authorization` header on every API call.
- Add token expiry and refresh logic.

---

### 1.4 All Traffic Over HTTP
`ServerDiscoveryService` and `AppServerConfig` exclusively use `http://`. Medication data (**PHI**) is transmitted unencrypted.

**Fix:** Enforce HTTPS with a valid TLS certificate on the server. Reject `http://` connections in production builds.

---

### 1.5 Database Deleted on Every Launch

[database_service.dart:24](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/database_service.dart#L24):
```dart
const bool debugMode = true; // Set to false for production
```
This deletes and recreates the SQLite database on **every app start**.

**Fix:** Set `debugMode = false` or (better) use `kDebugMode` from `package:flutter/foundation.dart` to auto-detect.

---

## 🟠 Priority 2 — High (Architecture & Efficiency)

### 2.1 No State Management
All screens use raw `setState()`. Business logic (OCR batching, medication processing, session management) is tightly coupled to UI widgets.

**Fix:**
- Adopt **Riverpod** or **flutter_bloc**.
- Extract business logic into dedicated controllers/notifiers that can be unit tested independently.

---

### 2.2 Monolithic Screen Files
| File | Lines | Problem |
|------|-------|---------|
| [process_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen.dart) | 598 | OCR dialog, processing logic, and full UI in one file |
| [scan_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/scan_screen.dart) | 466 | Camera init, capture logic, mock data, and UI |
| [slideshow_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart) | 442 | Sorting, grouping, saving, and carousel UI |

**Fix:** Split each into: a **screen** (UI only), a **controller/notifier** (business logic), and extracted **widgets** for reusable sub-components.

---

### 2.3 Monolithic Python Backend
| File | Size | Problem |
|------|------|---------|
| [floor_stock_parser.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/floor_stock_parser.py) | 116 KB | Single file doing everything |
| [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py) | 1,103 lines | Endpoints + parsing + image conversion in one file |

**Fix:** Refactor into a proper Python package with separate modules: `routes/`, `parsers/`, `services/`, `models/`.

---

### 2.4 Inefficient Server Discovery
[server_discovery_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/server_discovery_service.dart) fires 762+ HTTP requests (scanning 3 subnets × 254 IPs) on every launch because caching is disabled.

**Fix:**
- Re-enable caching after successful discovery.
- Store the last-known server IP in `SharedPreferences` and try it first.
- Add a manual "Change Server" UI option.

---

### 2.5 Base64 Image Payloads
`OCRService` encodes images to Base64 (+33% overhead), wraps them in JSON, and sends them. For 5 high-res images this can exceed 30 MB.

**Fix:** Use `http.MultipartRequest` to send raw image bytes directly. This reduces memory pressure and payload size.

---

### 2.6 `MedItem` God Object
[med_item.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/models/med_item.dart) has **22 fields**, a `copyWith` with 22 parameters, and a collision-prone `hashCode` using XOR chaining. It also has a duplicate method `withLocationAndNotes` that does the same thing as `copyWith`.

**Fix:**
- Consider using `freezed` or `equatable` packages for immutable models with auto-generated `==`, `hashCode`, and `copyWith`.
- Remove `withLocationAndNotes` in favor of `copyWith`.
- Consider splitting into sub-models (e.g., `LocationInfo`, `PickingState`).

---

## 🟡 Priority 3 — Medium (Code Quality & GUI)

### 3.1 Mock / Debug Code in Production
| Location | Issue |
|----------|-------|
| [scan_screen.dart:198](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/scan_screen.dart#L198) | "Test OCR (Mock Data)" button visible to users |
| [process_screen.dart:532](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen.dart#L532) | "Add More" button adds hardcoded fake medications |
| [ocr_service.dart:237](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart#L237) | Falls back to mock data silently on failure |

**Fix:** Guard all debug/test features behind `kDebugMode` checks. In production, show clear error messages instead of fake data.

---

### 3.2 Excessive Debug Logging
Many files contain verbose `=== DEBUG ===` style logging (e.g., `scan_screen.dart`, `api_config.dart`). The server has an **8.9 MB** log file committed to the repo.

**Fix:**
- Clean up verbose debug prefixes.
- Add `server.log` and `*.log` to `.gitignore`.
- Consider a structured logging solution (e.g., Python's `logging` with configurable levels).

---

### 3.3 No Named Routes
Navigation is done via direct `MaterialPageRoute` construction with no route names. This makes deep linking, analytics, and testing difficult.

**Fix:** Adopt `go_router` for declarative, type-safe routing with named routes and deep linking support.

---

### 3.4 Duplicated Priority/Sorting Logic
Location priority logic is duplicated between:
- [slideshow_screen.dart:38-68](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart#L38) (`initState` sort)
- [slideshow_screen.dart:166-188](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart#L166) (`_getLocationPriority`)

**Fix:** Extract into a single `LocationPriorityHelper` utility class.

---

### 3.5 Missing Form Validation
[login_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/login_screen.dart) does basic empty-check validation but does not use `Form`/`GlobalKey<FormState>` or `TextFormField.validator`. No `TextEditingController.dispose()` calls either.

**Fix:** Use proper `Form` widget with `TextFormField` validators and dispose controllers in `dispose()`.

---

### 3.6 No Accessibility Support
No `Semantics` widgets, no `Tooltip` on icon-only buttons, no large-text/dynamic-type support, no high-contrast mode.

**Fix:** Add `Semantics` labels to interactive elements. Test with TalkBack/VoiceOver. Support dynamic text scaling.

---

### 3.7 Linting Too Lenient
[analysis_options.yaml](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/analysis_options.yaml) only enables `avoid_print`. Many best-practice rules are not enforced.

**Fix:** Upgrade to `very_good_analysis` or at minimum enable: `prefer_const_constructors`, `prefer_const_declarations`, `always_use_package_imports`, `sort_child_properties_last`.

---

## 🔵 Priority 4 — Low (Testing, DevOps, Documentation)

### 4.1 Minimal Test Coverage
Only **6 test files** exist in `test/`, covering basic widget and OCR smoke tests. No integration tests, no service tests, no model tests.

**Fix:**
- Write unit tests for all services (`DatabaseService`, `AuthService`, `StorageService`).
- Write widget tests for all screens.
- Add integration tests for the scan → process → slideshow flow.
- Target ≥70% code coverage.

---

### 4.2 Backup Files in Repo
The `python_server/` directory contains backup files that bloat the repository:
- `floor_stock_parser_backup_20251020_0545.py` (54 KB)
- `floor_stock_parser_backup_before_hybrid_20251107_1537.py` (77 KB)
- Multiple `*.log` files totaling 9+ MB

**Fix:** Delete backup files (git history preserves them). Add `*.log`, `*.bak`, `*_backup*` to `.gitignore`.

---

### 4.3 No CI/CD Pipeline
The `codemagic.yaml` exists but there's no evidence of automated testing, linting, or deployment gating.

**Fix:** Configure CI to run `flutter analyze`, `flutter test`, and build checks on every PR.

---

### 4.4 Flask Debug Mode in Production
[docling_server.py:1103](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py#L1103):
```python
app.run(host='0.0.0.0', port=5003, debug=True)
```
Flask `debug=True` enables the interactive debugger (arbitrary code execution) and auto-reloading.

**Fix:** Use `debug=False` in production. Use a proper WSGI server like `gunicorn` for deployment.

---

## Summary of Proposed Implementation Order

| Phase | Focus | Effort |
|-------|-------|--------|
| **Phase 1** | Security hardening (API key, auth tokens, HTTPS, debug mode) | 2-3 days |
| **Phase 2** | Architecture refactor (state management, file splitting) | 4-5 days |
| **Phase 3** | Efficiency (multipart uploads, server discovery, DB queries) | 2-3 days |
| **Phase 4** | Code quality (linting, routing, form validation, accessibility) | 2-3 days |
| **Phase 5** | Testing & DevOps (unit tests, CI/CD, cleanup) | 3-4 days |
| **Phase 6** | Python backend refactor (modularize, remove debug mode) | 2-3 days |
