# Production Readiness Audit — Pharmacy Pickup App

**Date:** March 15–16, 2026
**Commits:** `4f1fa92` through `a83fa2e` on `main`

---

## Summary

Full production hardening pass before App Store submission. Addressed debug-only code leaking into release builds, missing error handling, UI stability issues, iOS networking restrictions, a critical server-side bug, and screen timeout killing OCR processing.

---

## Critical Fixes

### 1. `debugMode` Always True in Release

**File:** `lib/services/database_service.dart`
**Problem:** `const bool debugMode = true` was hardcoded, meaning debug SQL logging and verbose output ran in production.
**Fix:** Changed to `final bool debugMode = kDebugMode` using `package:flutter/foundation.dart`. This is automatically `false` in release builds — no manual toggle needed.

### 2. `print()` Statements Across Codebase

**Files:** 13 files across services and screens
**Problem:** `print()` writes to stdout, which is a no-op on iOS release but still evaluates string interpolation (performance cost) and could leak sensitive data on Android logcat.
**Fix:** Replaced all `print()` calls with `AppLogger` (`lib/utils/app_logger.dart`), which uses `dart:developer log()` — stripped entirely from release builds by the Dart compiler.

**Files converted:**
- `database_service.dart`, `auth_service.dart`, `ocr_service.dart`, `parsing_service.dart`
- `server_discovery_service.dart`, `medication_processor.dart`, `location_service.dart`
- `image_enhancement_service.dart`, `debug_processor.dart`

### 3. SERVER_URL Production Override

**File:** `lib/services/server_discovery_service.dart`
**Problem:** The app always performed LAN network scanning (762 IPs across 3 subnets) to find the backend server. This is fine for development but wastes time and battery in production.
**Fix:** Added check at top of `discoverServer()`:
```dart
final envUrl = dotenv.env['SERVER_URL'];
if (envUrl != null && envUrl.isNotEmpty && !envUrl.contains('localhost')) {
  _cachedServerUrl = envUrl;
  return envUrl;
}
```
If `SERVER_URL` is set in `.env`, network scanning is skipped entirely. Falls back to LAN discovery if not set (dev workflow unchanged).

### 4. Token Expiration Handling

**File:** `lib/services/auth_service.dart`
**Problem:** No handling for expired/invalid JWT tokens. If the server restarted (invalidating tokens), API calls would silently fail.
**Fix:** Added `_isTokenExpired()` method that checks for HTTP 401 responses and triggers `logout()`, forcing re-authentication.

### 5. HTTP Timeouts

**Files:** `auth_service.dart`, `parsing_service.dart`, `ocr_service.dart`
**Problem:** HTTP calls had no timeout — a hung server would freeze the app indefinitely.
**Fix:**
- Auth calls (login, register, save session): **30 second** timeout
- OCR/parsing calls: **60 second** timeout
- Parallel image processing: **5 minute** timeout

### 6. Mock Data Fallback Removed

**File:** `lib/services/ocr_service.dart`
**Problem:** When OCR failed, the app returned fake medication data (`_createMockMedications()`). In production, this would show fabricated medications to pharmacy staff.
**Fix:** Returns empty list on failure. The UI shows "no medications found" instead of fake data.

---

## UI Stability Fixes

### 7. `mounted` Checks After Async Operations

**Files:** `process_screen.dart`, `register_screen.dart`, `document_review_screen.dart`
**Problem:** `setState()` called after `await` without checking if the widget is still in the tree. Causes "setState() called after dispose()" exceptions if user navigates away during processing.
**Fix:** Added `if (!mounted) return;` before every `setState()` that follows an async gap. 8 locations in process_screen alone.

### 8. Missing `dispose()` Methods

**Files:** `slideshow_screen.dart`, `process_screen.dart`
**Problem:** `CarouselController.autoPlay` and wakelock not cleaned up on screen exit.
**Fix:**
- Slideshow: `carouselController.stopAutoPlay()` in dispose
- Process screen: `WakelockPlus.disable()` in dispose

### 9. Test OCR Button Hidden in Release

**File:** `lib/screens/scan_screen.dart`
**Problem:** "Test OCR" debug button visible to production users.
**Fix:** Wrapped in `if (kDebugMode)` — only shows in debug builds.

### 10. Screen Wakelock During OCR Processing

**File:** `lib/screens/process_screen.dart`
**Package:** `wakelock_plus: ^1.2.8`
**Problem:** iPhone screen timeout would lock the device during 30+ second OCR processing, killing the active network request. When user unlocked, the app restarted and re-sent images (doubling processing time).
**Fix:**
- `WakelockPlus.enable()` at start of `_processScannedImages()`
- `WakelockPlus.disable()` in `finally` block and in `dispose()`
- Screen stays on only during active processing, not permanently

---

## iOS-Specific Fixes

### 11. App Transport Security (ATS)

**File:** `ios/Runner/Info.plist`
**Problem:** iOS release builds block all HTTP (non-HTTPS) connections by default. The app communicates with the Python server over HTTP on the local network, so login and OCR calls silently failed in release mode.
**Fix:**
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```
`NSAllowsLocalNetworking` covers LAN server discovery. `NSAllowsArbitraryLoads` is a broader override needed until the production backend has HTTPS. Should be tightened to domain-specific exceptions once SSL is configured.

### 12. Session Resume Navigation

**File:** `lib/main.dart`
**Problem:** `_resumeSession()` had a TODO comment instead of actual navigation — saved sessions couldn't be resumed.
**Fix:** Navigates to `ProcessScreen` with the loaded medications.

---

## Dependency Cleanup

### 13. Removed `google_mlkit_text_recognition`

**File:** `pubspec.yaml`
**Impact:** App size dropped from **67.6 MB → 23.1 MB** (reduced by ~44 MB).
**Reason:** The app uses server-side Google Vision + Gemini for OCR, making the on-device ML Kit bundle unnecessary.

---

## Server-Side Fixes

### 14. `parsing.py` Indentation Bug

**File:** `python_server/routes/parsing.py` (lines 157–267)
**Problem:** The legacy JSON base64 handler was indented inside the `if 'multipart/form-data' in content_type` block. When the Flutter app sent JSON requests (which it always does), the code fell through and the function returned `None`, causing a 500 Internal Server Error.

**Before (broken):**
```python
if 'multipart/form-data' in content_type:
    # ... multipart handling ...
    return jsonify({...})

    # Legacy JSON handler (WRONG — indented inside the if block)
    data = request.get_json()
    ...
```

**After (fixed):**
```python
if 'multipart/form-data' in content_type:
    # ... multipart handling ...
    return jsonify({...})

else:
    # Legacy JSON handler (correct — runs for JSON requests)
    data = request.get_json()
    ...
```

### 15. Missing `GEMINI_API_KEY` Environment Variable

**File:** `python_server/.env`
**Problem:** The `.env` file had the Gemini API key stored as `GOOGLE_API_KEY`, but `floor_stock_parser.py` (line 2262) reads `os.getenv('GEMINI_API_KEY')`. For floor_stock mode, Gemini Vision is the primary (and only) parser — without this key, all floor stock parsing returned a 500 error: `"Gemini Vision failed and OCR fallback is disabled."`
**Fix:** Added `GEMINI_API_KEY=<key>` to `.env` alongside the existing `GOOGLE_API_KEY`.

---

## Files Deleted

| File | Reason |
|------|--------|
| `lib/screens/process_screen_backup_before_ui_changes_20250930_0537.dart` | Stale backup from September 2025 |
| `lib/services/test_ocr_service.dart` | Unused test service |

---

## Remaining Work

### Should-Fix (Before App Store)
- Wrap API key debug logging in `kDebugMode`
- Clean up commented-out code blocks
- Add `JWT_SECRET` to `.env` for persistent sessions across server restarts
- Set `ADMIN_PASSWORD` / `PICKER_PASSWORD` env vars (currently using insecure defaults)

### Before Production Deployment
- Configure HTTPS on production backend and tighten ATS to domain-specific exceptions
- SSL certificate pinning
- Build with obfuscation: `flutter build ios --release --obfuscate --split-debug-info=build/debug-info`

---

## Commit Log

| Hash | Description |
|------|-------------|
| `4f1fa92` | Services hardening (kDebugMode, AppLogger, timeouts, token expiry, SERVER_URL) |
| `73c3349` | UI stability + wakelock (mounted checks, dispose, screen-on during OCR) |
| `54f0156` | iOS ATS config + dependency cleanup (removed mlkit, added wakelock_plus) |
| `8897601` | Removed stale backup and test files |
| `a83fa2e` | Server parsing.py indentation fix + GEMINI_API_KEY env config |
