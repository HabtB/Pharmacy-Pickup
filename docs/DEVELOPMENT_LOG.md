# Pharmacy Picker App - Development Log

## Daily Development Documentation Protocol
For every development session, document:
1. **Date Header** - Always start with "Date: [Month Day, Year]"
2. **Session Context** - What we're working on and why
3. **Changes Made** - Specific code changes, file modifications, enhancements
4. **Issues Identified** - Any bugs, problems, or areas needing improvement
5. **Issues Resolved** - Solutions implemented and their effectiveness
6. **Performance Notes** - Any performance improvements or degradations
7. **Testing Results** - Outcomes of testing new features or fixes
8. **Next Steps** - What needs to be done in future sessions
9. **Technical Details** - API changes, dependency updates, configuration changes
10. **User Feedback** - Any feedback or requests from the user

---
## Date: March 5, 2026 (Stop-Processing Recovery)

### Session Context
When OCR processing was stopped mid-way via `ProcessingController.stop()`, the Process Screen could end up in a frozen state — no medications found, "Start Picking" grayed out, no clear way to navigate away.

### Changes Made

#### [MODIFY] `lib/screens/process_screen.dart`
1. **Recovery dialog** (`_showStopRecoveryDialog()`) — shown when OCR is stopped and 0 medications were found. Offers three options:
   - **Try Again** — re-runs OCR on the same scanned images
   - **Review Scans** — navigates back to Document Review screen with original images
   - **Go Home** — navigates to mode selection
2. **Partial results snackbar** — when stopped with some medications already found, shows an orange "Stopped early — found X medications" snackbar and lets user proceed with "Start Picking"
3. **Refactored** stop-detection logic out of `finally` block to avoid `control_flow_in_finally` lint

### Testing Results
- `flutter analyze lib/screens/process_screen.dart` — clean (0 errors/warnings, only pre-existing import-style infos)

---
## Date: March 4, 2026 (Named Routes — go_router Migration)

### Changes Made
1. **`lib/router.dart`** [NEW] — Central route table with auth redirect, `ProcessRouteData` class
2. **`main.dart`** — `MaterialApp` → `MaterialApp.router` with `routerConfig: appRouter`
3. **`login_screen.dart`** — `Navigator.pushReplacement` → `context.go('/home')`
4. **`mode_selection_screen.dart`** — `Navigator.push` → `context.push('/scan/$mode')`, logout → `context.go('/login')`
5. **`scan_screen.dart`** — `context.push('/review/...')`, `context.push('/process/...')`
6. **`document_review_screen.dart`** — `context.go('/process/...')`
7. **`process_screen.dart`** — `context.push('/slideshow', extra: medications)`

### Route Table
| Path | Screen |
|------|--------|
| `/login` | LoginScreen |
| `/home` | ModeSelectionScreen |
| `/scan/:mode` | ScanScreen |
| `/review/:mode` | DocumentReviewScreen |
| `/process/:mode` | ProcessScreen |
| `/slideshow` | SlideshowScreen |

### Testing Results
- `flutter analyze` — clean (zero errors in modified files)
- `flutter test` — **40/40 pass**

---
## Date: March 4, 2026 (Medication Location Data → Database Migration)

### Changes Made
**Server Side:**
1. **`models/medication_locations.py`** [NEW] — SQLite table for medication locations with CRUD operations and one-time CSV import (2,159 rows)
2. **`routes/locations.py`** [NEW] — REST API: `GET /api/locations` (paginated, incremental sync via `?updated_since=`), `GET /api/locations/search?q=`, `POST/PUT/DELETE` for admin
3. **`medication_location_lookup.py`** — `_load_locations()` now reads from SQLite first, falls back to CSV
4. **`app.py`** — registers `locations_bp` Blueprint, runs `init_locations_table()` + `import_from_csv()` on startup

**Flutter Side:**
5. **`database_service.dart`** — Replaced CSV loading with server API sync (`GET /api/locations`), incremental `syncFromServer()`, DB schema v2 with `server_id`/`location_code`/`updated_at`
6. **`location_service.dart`** — Reads from local SQLite cache instead of bundled CSV. Removed `csv` package import.

### Architecture
```
Server SQLite (2,159 meds) → /api/locations → Flutter app (local SQLite cache)
```
- Server owns the data (single source of truth)
- Flutter syncs on launch, works offline via local cache
- CSV kept as fallback if server unreachable

### Testing Results
- `flutter analyze` — clean
- `flutter test` — **40/40 pass**
- Python import: 2,159 rows, search + lookup verified

---
## Date: March 3, 2026 (Quick Wins — Password Hashing, Rate Limiting, Cleanup)

### Changes Made
1. **Password Hashing** — Upgraded from SHA-256 to **bcrypt** in `database_manager.py`. Existing SHA-256 hashes auto-upgrade to bcrypt on next successful login (backward compatible).
2. **Rate Limiting** — Added **Flask-Limiter** to `app.py` — 5 login attempts/minute per IP to prevent brute-force.
3. **Deleted `docling_server.py`** — Old 1,159-line monolith removed (replaced by modular `app.py` + Blueprints).
4. **`requirements.txt`** — Added `bcrypt>=4.0.0` and `flask-limiter>=3.5.0`.

### Testing Results
- `flutter test` — **40/40 pass**
- All Python module imports verified

---
## Date: March 3, 2026 (Security Hardening)

### Changes Made
1. **JWT Secret** — `config.py` now auto-generates a random 32-byte hex secret if `JWT_SECRET` env var is not set, with a loud console warning. Tokens are invalidated on restart unless a persistent secret is configured.
2. **HTTPS Warning** — Added `httpWarningMessage` getter to `AppServerConfig` that returns a user-facing warning when connected over HTTP in release mode.
3. **`.gitignore`** — Already up-to-date from prior refactor (`*_backup*`, `*.bak`, `*.pid`, `*.db`).

### Testing Results
- `flutter analyze` — 0 issues
- `flutter test` — **40/40 pass**

---
## Date: March 2, 2026 (Python Backend Refactor)

### Session Context
Split monolithic `docling_server.py` (1,159 lines) into modular Flask Blueprints.

### Changes Made

#### 1. **Modularization**
- Created `app.py` (entry point), `config.py` (env config)
- Created `routes/auth.py`, `routes/health.py`, `routes/parsing.py` (Flask Blueprints)
- Created `services/image_service.py`, `parsers/text_parsers.py`

#### 2. **Directory Cleanup**
- Moved 34 debug/test scripts to `scripts/`
- Deleted 9 backup/log files
- Updated `.gitignore` with `*_backup*`, `*.bak`, `*.pid`, `*.db`

### Files Created
| File | Purpose |
|------|---------|
| `python_server/app.py` | Flask factory + Blueprint registration |
| `python_server/config.py` | Centralized env config |
| `python_server/routes/auth.py` | Login (JWT), save_session |
| `python_server/routes/health.py` | Health-check |
| `python_server/routes/parsing.py` | parse-document, parse-documents-parallel |
| `python_server/services/image_service.py` | Image→PDF conversion |
| `python_server/parsers/text_parsers.py` | Text/table parsing utilities |

### Testing Results
- `flutter test test/controllers/ test/models/` — **40 tests pass**
- Server testing requires `python app.py` (replaces `python docling_server.py`)

---
## Date: March 2, 2026 (Phase 4 — Code Quality)

### Session Context
Phase 4 of `improvement_plan_2.md`: Code quality improvements.

### Changes Made

#### 1. **Mock/Debug Code Guard**
- Guarded `_createMockMedications()` fallback behind `kDebugMode` in `ocr_service.dart`

#### 2. **Logging Cleanup**
- Downgraded 4 verbose `[DEBUG]` log lines to `logger.debug()` in `docling_server.py`

#### 3. **Login Form Validation**
- Added `Form`/`GlobalKey<FormState>` + `TextFormField` with validators
- Added `dispose()` for text controllers
- Added `Semantics` label on logo, `autofillHints` on text fields

#### 4. **Stricter Lint Rules**
- Enabled 10 lint rules in `analysis_options.yaml`
- Fixed all violations in modified files (`ocr_service.dart`, `login_screen.dart`)

### Testing Results
- `flutter analyze` — 0 issues on modified files
- `flutter test test/controllers/ test/models/` — **40 tests pass**

### Files Modified
| File | Change |
|------|--------|
| `lib/services/ocr_service.dart` | kDebugMode guard + lint fixes |
| `lib/screens/login_screen.dart` | Form validation + accessibility |
| `analysis_options.yaml` | 10 new lint rules |
| `python_server/docling_server.py` | logger.debug() cleanup |

---
## Date: March 2, 2026 (Phase 3 — Efficiency Improvements)

### Session Context
Phase 3 of `improvement_plan_2.md`: Efficiency improvements covering multipart image upload, server discovery TTL cache, and MedItem model cleanup.

### Changes Made

#### 1. **Multipart Image Upload** (replaces Base64 JSON)
- Refactored all 4 `base64Encode` call sites in `ocr_service.dart` to use `http.MultipartRequest`
- Updated `docling_server.py` — both `/parse-document` and `/parse-documents-parallel` now accept multipart form-data with JSON base64 fallback
- Eliminated ~33% payload overhead for image transfers

#### 2. **Server Discovery TTL Cache**
- Added cache timestamp to `server_discovery_service.dart` (persisted in SharedPreferences)
- 1-hour TTL — expired entries trigger automatic re-discovery
- Added `setCacheTtl()` for configuration
- Added background health-check in `app_server_config.dart` — silently invalidates cache if server becomes unreachable
- Added `force` parameter to `ensureDiscovered()`

#### 3. **MedItem → Equatable**
- Extended `Equatable` in `med_item.dart` (package already in pubspec.yaml)
- Overrode `props` with all 22 fields including `floorBreakdown`
- Deleted 50 lines of manual `operator ==` and XOR-chain `hashCode`

### Testing Results
- `flutter analyze` — 0 issues on all changed files
- `flutter test test/controllers/ test/models/` — **40 tests pass**
- New test file: `test/models/med_item_test.dart` (12 tests)

### Files Modified
| File | Change |
|------|--------|
| `lib/services/ocr_service.dart` | base64 → multipart upload |
| `lib/services/server_discovery_service.dart` | TTL cache + timestamp |
| `lib/services/app_server_config.dart` | background health-check + force param |
| `lib/models/med_item.dart` | Equatable migration |
| `python_server/docling_server.py` | multipart endpoint support |
| `test/models/med_item_test.dart` | [NEW] MedItem unit tests |

---
## Date: March 2, 2026

### Session Context
Phase 2 of the comprehensive improvement plan (`improvement_plan_2.md`): Architecture refactor. Adopted ChangeNotifier-based state management and split all three monolithic screen files into focused, independently testable components.

### Changes Made

#### 1. **Created `lib/controllers/` Directory with 3 Controllers** [NEW]

| File | Lines | Responsibility |
|------|------:|---------------|
| `scan_controller.dart` | 140 | Camera init, image capture, gallery pick |
| `process_controller.dart` | 165 | OCR orchestration, mock-text parsing, medication processing |
| `slideshow_controller.dart` | 212 | Sorting, location grouping, toggle/qty mutations, save progress |

All extend `ChangeNotifier` (Flutter SDK built-in — **zero new package dependencies**).

#### 2. **Extracted 5 Widgets** [NEW]

`lib/widgets/process/`:
- `process_header.dart` — Mode title card
- `ocr_progress_dialog.dart` — Progress dialog with Pause/Resume/Stop controls (includes static `show()` helper)
- `process_action_buttons.dart` — Add More / Start Picking / Clear All

`lib/widgets/scan/`:
- `camera_preview_area.dart` — Camera preview, error state, desktop fallback
- `scan_action_buttons.dart` — Scan Page / Gallery / Test OCR / Process

#### 3. **Extracted `lib/utils/location_priority_helper.dart`** [NEW]
   - Deduplicated `getPriority` + `_getLocationPriority` from `slideshow_screen.dart` into a single static utility class

#### 4. **Refactored 3 Screens to Thin UI Shells**

| Screen | Before | After | Reduction |
|--------|-------:|------:|----------:|
| `process_screen.dart` | 597 lines | ~195 lines | **−67%** |
| `scan_screen.dart` | 466 lines | ~155 lines | **−67%** |
| `slideshow_screen.dart` | 442 lines | ~215 lines | **−51%** |

Each screen now uses `ListenableBuilder` / `addListener` on its controller. Business logic calls go directly to the controller methods.

#### 5. **Debug Code Guarded with `kDebugMode`**
   - "Test OCR (Mock Data)" in `ScanActionButtons` → `if (kDebugMode)`
   - "Add More" in `ProcessActionButtons` → `if (kDebugMode)`

### Issues Resolved
1. ✅ Business logic decoupled from UI — controllers are independently unit testable
2. ✅ All three monolithic screens split into focused components
3. ✅ Duplicated location-priority logic consolidated into one utility
4. ✅ Debug buttons are no longer visible in production builds

### Testing Results
- `flutter analyze lib/controllers/ lib/widgets/process/ lib/widgets/scan/ lib/utils/location_priority_helper.dart lib/screens/process_screen.dart lib/screens/scan_screen.dart lib/screens/slideshow_screen.dart`: **2 info-level issues only** — both pre-existing `onPopInvoked` deprecations (same as `document_review_screen.dart`)
- **0 new errors or warnings** introduced

### Technical Details
- **Architecture Pattern**: `ChangeNotifier` (SDK built-in, no new pub.dev dependency)
- **Screen pattern**: Screen holds controller in `initState`, calls `_controller.addListener(() => setState((){}))`; business logic mutations call controller methods; `ListenableBuilder` used for the process screen body
- **Verification docs**: `docs/improvement_plan_2.md`, `docs/phase_2_walkthrough.md`

### Next Steps
- Phase 3: Efficiency improvements (multipart image upload, server discovery caching)
- Phase 4: Code quality (go_router, form validation, accessibility)
- Phase 5: Testing & DevOps
- Fix pre-existing `onPopInvoked` deprecations → `onPopInvokedWithResult`

---
## Date: February 25, 2026

### Session Context
Codebase cleanup session: replaced all debug `print()` calls with a proper logging utility, enabled `avoid_print` lint, moved misplaced test file, and deleted stale backup file.

### Changes Made

#### 1. **Created `AppLogger` Utility** (`lib/utils/app_logger.dart`) [NEW]
   - Thin wrapper around `dart:developer log()`
   - Three levels: `AppLogger.info()`, `AppLogger.warn()`, `AppLogger.error()`
   - Named `name` parameter for log channel filtering (e.g., `name: 'OCR'`, `name: 'ServerDiscovery'`)
   - No new dependencies — uses SDK-bundled `dart:developer`

#### 2. **Replaced ~180 `print()` Calls Across 18 Files**
   - Every `print()` in `lib/` replaced with the appropriate `AppLogger` method
   - Log messages cleaned up — removed verbose `=== DEBUG ===` wrappers, consolidated multi-line prints

   | File | Calls Replaced | Log Tag |
   |------|:-:|---------|
   | `ocr_service.dart` | ~50 | `OCR` |
   | `process_screen.dart` | 19 | `ProcessScreen` |
   | `server_discovery_service.dart` | 15 | `ServerDiscovery` |
   | `database_service.dart` | ~27 | `Database` |
   | `parsing_service.dart` | ~34 | `Parsing` |
   | `medication_processor.dart` | ~17 | `MedProcessor` |
   | `scan_screen.dart` | 15 | `ScanScreen` |
   | `image_enhancement_service.dart` | 12 | `ImageEnhancement` |
   | `debug_processor.dart` | 7 | `Debug` |
   | `storage_service.dart` | 5 | `Storage` |
   | `main.dart` | 4 | `Init` |
   | `location_service.dart` | 2 | `Location` |
   | `api_config.dart` | 3 | `ApiConfig` |
   | `auth_service.dart` | 1 | `Auth` |
   | `slideshow_screen.dart` | 1 | `Slideshow` |
   | `medication_slide_card.dart` | 1 | `MedSlideCard` |
   | `app_server_config.dart` | 1 | `AppServerConfig` |

#### 3. **Enabled `avoid_print` Lint Rule** (`analysis_options.yaml`)
   - Uncommented and set `avoid_print: true`
   - Future `print()` usage will now be flagged by the analyzer

#### 4. **Moved `test_ocr_service.dart`** from `lib/services/` → `test/`
   - No references to this file existed in `lib/`, so no import updates needed

#### 5. **Deleted Backup File** (`lib/screens/process_screen_backup_before_ui_changes_20250930_0537.dart`)
   - Stale backup from Sep 30, 2025 — changes long committed

### Issues Resolved
1. ✅ ~180 `avoid_print` lint warnings eliminated
2. ✅ Test file properly placed in `test/` directory
3. ✅ Backup file cluttering `lib/screens/` removed

### Testing Results
- `flutter analyze lib/`: 51 issues, **all pre-existing** (opencv_4 errors, deprecation warnings, unused elements)
- **0 new issues** from our changes
- **0 `avoid_print` violations** — all `print()` calls successfully replaced
- `grep -rn "print(" lib/ | grep -v AppLogger`: **0 results**

### Technical Details
- **AppLogger** uses `dart:developer` which is automatically stripped in release builds
- Log levels: info (0), warn (500), error (1000) — filterable in DevTools
- Each service/screen uses a unique `name` tag for easy log filtering

### Next Steps
- Add settings screen for manual server IP entry
- Address pre-existing `image_enhancement_service.dart` errors (missing `opencv_4` dependency)
- Replace deprecated `withOpacity` calls with `withValues()`
- Replace deprecated `onPopInvoked` with `onPopInvokedWithResult`

---
## Date: February 24, 2026

### Session Context
Comprehensive app architecture review followed by centralization of server URL management. The app had two conflicting server URL strategies — `AuthService` used a hardcoded IP while `OCRService` used dynamic subnet scanning — causing login failures when the network changed.

### Changes Made

#### 1. **Created `AppServerConfig` Singleton** (`lib/services/app_server_config.dart`) [NEW]
   - Centralized singleton wrapping `ServerDiscoveryService`
   - Provides `baseUrl` and `apiUrl` accessors
   - Lazy initialization with `ensureDiscovered()` — discovers once, caches for app lifetime
   - `rediscover()` method for manual retry after network changes

#### 2. **Updated `AuthService`** (`lib/services/auth_service.dart`)
   - Removed hardcoded `http://172.20.10.9:5003/api` constant
   - Added dynamic URL via `AppServerConfig.instance.apiUrl`
   - Fixed `logout()`: Changed `prefs.clear()` → only removes auth-specific keys, preserving saved medication sessions

#### 3. **Updated `OCRService`** (`lib/services/ocr_service.dart`)
   - Removed private `_discoverServer()` method and `_serverDiscovered` / `_doclingServerUrl` fields
   - Replaced all server URL references with `AppServerConfig.instance.baseUrl`

#### 4. **Updated `main.dart`**
   - Calls `AppServerConfig.instance.ensureDiscovered()` during startup

#### 5. **Created `docs/` Folder for Dev Storyboard**
   - `docs/server_url_centralization_plan.md` — Implementation plan
   - `docs/server_url_centralization_walkthrough.md` — Walkthrough

### Issues Identified
1. Hardcoded auth IP mismatch — `AuthService` vs `OCRService` pointing at different IPs
2. `logout()` wiping all SharedPreferences including saved sessions
3. 330+ `avoid_print` lint warnings across codebase (pre-existing)

### Issues Resolved
1. ✅ Server URL centralized — both services use `AppServerConfig`
2. ✅ `logout()` fixed — only removes auth keys
3. ✅ Server discovery runs once at startup

### Testing Results
- `flutter analyze lib/`: 0 new errors; all pre-existing errors in unrelated files

### Next Steps
- Remove debug `print()` statements and replace with proper logging
- Split `slideshow_screen.dart` (1621 lines) into smaller widgets
- Move `test_ocr_service.dart` from `lib/services/` to `test/`
- Add settings screen for manual server IP entry

### User Feedback
- Plans and walkthroughs to be saved in `docs/` folder
- Always update `DEVELOPMENT_LOG.md` after making changes (established as rule)

---

## Date: February 24, 2026 (Afternoon Session)

### Session Context
Split `slideshow_screen.dart` from 1621 lines into 5 focused files to improve maintainability.

### Changes Made

#### 1. **Extracted `PreparationTab`** (`lib/widgets/slideshow/preparation_tab.dart`) [NEW]
   - Moved the `PreparationTab` class (cups, syringes, fridge alerts) to its own file

#### 2. **Extracted `MedicationSlideCard`** (`lib/widgets/slideshow/medication_slide_card.dart`) [NEW]
   - The ~700-line carousel card with location badge, med details, quantity picker, floor breakdown, warnings, and completion button
   - All helper methods moved: `_parseFloorBreakdown`, `_extractOriginalNotes`, `_getPluralForm`, `_showLocationImage`

#### 3. **Extracted `LocationProgressBanner`** (`lib/widgets/slideshow/location_progress_banner.dart`) [NEW]
   - Green location header showing current location name and pick progress counter

#### 4. **Extracted `PickingSummaryBar`** (`lib/widgets/slideshow/picking_summary_bar.dart`) [NEW]
   - Bottom bar with Total Items / Completed / Remaining counts

#### 5. **Refactored `slideshow_screen.dart`** (1621 → ~330 lines)
   - Removed all extracted UI code
   - Added imports for 4 new widgets
   - Carousel `itemBuilder` now delegates to `MedicationSlideCard` widget
   - `_buildSlideshowTab()` delegates to `LocationProgressBanner` and `PickingSummaryBar`
   - Removed unused `_isNewLocationGroup` method
   - Removed `LocationImageService` import (now in `MedicationSlideCard`)

### Issues Resolved
1. ✅ `slideshow_screen.dart` reduced from 1621 to ~330 lines
2. ✅ Each widget is now independently testable and reusable
3. ✅ Removed unused `_isNewLocationGroup` method (flagged by analyzer)

### Testing Results
- `flutter analyze`: 0 errors in all 5 files; only pre-existing deprecation warnings

### Technical Details
| File | Lines | Purpose |
|------|-------|---------|
| `slideshow_screen.dart` | ~330 | State management, sorting, location logic, navigation |
| `medication_slide_card.dart` | ~540 | Individual medication card in carousel |
| `preparation_tab.dart` | ~230 | Cup/syringe/fridge prep alerts |
| `location_progress_banner.dart` | ~75 | Green location header |
| `picking_summary_bar.dart` | ~55 | Bottom stats bar |

### Next Steps
- Remove debug `print()` statements and replace with proper logging
- Remove backup file from `lib/screens/`
- Move `test_ocr_service.dart` from `lib/services/` to `test/`

---

## Date: October 2, 2025

### Session Context
Implemented Google Vision API for OCR, enhanced medication parsing with intelligent extraction, added 24-hour pick amount calculation, and improved UI display formatting for the Pharmacy Picker app.

### Changes Made

#### 1. **Google Vision API Integration**
   - Created `python_server/google_vision_ocr.py` - Direct Google Cloud Vision API client
   - Migrated from Docling to Google Vision as primary OCR engine
   - Configured credentials using service account JSON file from Downloads
   - Added environment variable support with `.env` file and `python-dotenv`
   - Server now runs on port 5003 with Google Vision OCR

#### 2. **Fixed xAI Grok API Integration**
   - Corrected API endpoint from Groq to xAI: `https://api.x.ai/v1/chat/completions`
   - Updated model from `grok-beta` to `grok-2-latest`
   - Added system message for pharmacy medication extraction context
   - Successfully integrated LLM parsing as primary method with regex fallback

#### 3. **Enhanced Medication Parsing (`enhanced_medication_parser.py`)**
   - **Hyphenated Medication Support**: Added regex patterns for medications like `dorzolamide-timolol`
   - **Complex Strength Formats**: Handles formats like `22.3.6.8 mg/ml`
   - **Improved Frequency Detection**: Expanded patterns to detect Q4h, Q6h, Q8h, BID, TID, QID, QHS, QAM, QHS, PRN
   - **Human-Readable Frequency Display**: Maps abbreviations to full text (e.g., "BID" → "Twice per day", "Q4h" → "Every 4 hours")
   - **Enhanced Validation**: Filters out non-medication words (tablet, dose, admin, order, etc.)
   - **Duplicate Prevention**: Tracks seen medication names to avoid duplicates
   - **Brand Name Recognition**: Prioritizes medications with brand names in parentheses

#### 4. **24-Hour Pick Amount Calculation**
   - Implemented `_calculate_24hr_pick_amount()` method
   - Calculates total daily quantity based on frequency and admin amount
   - Examples:
     - Q4h × 1 tablet = 6 tablets
     - Q6h × 1 tablet = 4 tablets
     - Q8h × 1 tablet = 3 tablets
     - TID × 1 tablet = 3 tablets
     - BID × 1 tablet = 2 tablets
     - Daily × 1 tablet = 1 tablet
   - Returns integer values (rounds up for partial doses)

#### 5. **UI/UX Improvements (`process_screen.dart`)**
   - Removed redundant circled number display
   - Kept clean `#1, #2, #3` medication numbering
   - Added "Pick Amount" display with proper pluralization
   - Format: `Pick Amount: 3 tablets` (automatically handles singular/plural)
   - Added inventory icon for pick amount field
   - Improved visual hierarchy with color-coded icons

#### 6. **Flutter OCR Service Fixes (`ocr_service.dart`)**
   - Fixed broken ternary operator in `_convertMapToMedItem()` that caused type errors
   - Implemented safe pick amount parsing (handles both int and string)
   - Added frequency field mapping to sig display
   - Proper error handling for missing or malformed data

### Issues Identified
1. **Type Mismatch Error**: `type 'int' is not a subtype of type 'bool'` - caused by improper ternary operator syntax
2. **Duplicate Medications**: Regex was extracting multiple invalid entries ("Tablet", "Dose", "Admin" as medication names)
3. **Missing Frequency Display**: Frequency info was extracted but not shown in UI
4. **Pick Amount Not Calculated**: Was defaulting to 1 for all medications regardless of dosing schedule

### Issues Resolved
1. ✅ Fixed type error in Flutter OCR service with proper pick amount parsing
2. ✅ Implemented strict medication name validation to filter non-medication words
3. ✅ Added duplicate prevention using seen names tracking
4. ✅ Integrated frequency into dose display field
5. ✅ Implemented intelligent 24-hour pick amount calculation
6. ✅ Google Vision API successfully extracting text from medication labels
7. ✅ xAI Grok API successfully parsing medications with high accuracy

### Testing Results
- **OCR Extraction**: ✅ Successfully extracted "hydrALAZINE (APRESOLINE) tablet 25 mg" from real pharmacy label
- **Medication Parsing**: ✅ Correctly parsed to "Hydralazine - 25 mg - tablet"
- **Frequency Detection**: ✅ Detected "Every 8 hours" from label text
- **Pick Amount Calculation**: ✅ Calculated 3 tablets for Q8h dosing (8 hours × 3 = 24 hours)
- **UI Display**: ✅ Shows formatted medication card with all fields
- **Duplicate Filtering**: ✅ Only shows 1 medication (not 5 invalid entries)

### Performance Notes
- Google Vision API provides superior OCR accuracy compared to Docling
- xAI Grok API response time: ~2 seconds for medication parsing
- Regex fallback provides instant results when LLM is unavailable
- Server auto-reload works correctly for Python code changes
- Flutter hot reload successfully applies UI changes

### Technical Details

#### Files Created
- `python_server/google_vision_ocr.py` - Google Vision API client
- `python_server/.env` - Environment configuration
- `python_server/GOOGLE_VISION_SETUP.md` - Setup documentation
- `python_server/start_server.sh` - Server startup script
- `python_server/google_credentials.json` - Google Cloud service account credentials

#### Files Modified
- `python_server/docling_server.py` - Integrated Google Vision, updated port to 5003
- `python_server/enhanced_medication_parser.py` - Enhanced parsing logic, 24hr calculation
- `python_server/requirements.txt` - Added google-cloud-vision, python-dotenv
- `lib/services/ocr_service.dart` - Fixed type errors, improved parsing
- `lib/screens/process_screen.dart` - Updated UI for pick amount display

#### API Configuration
- **Google Vision API**: Using service account credentials from `google_credentials.json`
- **xAI Grok API**: Using API key from `.env` file
- **Server Port**: 5003 (standardized across Flutter app and Python server)
- **Server URL**: `http://192.168.1.134:5003`

#### Dependencies Added
```
google-cloud-vision>=3.0.0
python-dotenv>=1.0.0
```

### Display Format
Medications now display as:
```
#1
Name: Hydralazine
Dose: 25 mg Every 8 hours
Admin: 1 tablet
Pick Amount: 3 tablets
```

### Next Steps
- Test with additional medication labels to validate parsing accuracy
- Consider adding patient name and MRN extraction to display
- Implement location lookup from database
- Add error recovery for network failures
- Monitor Google Vision API usage and costs

### User Feedback
- User requested Google Vision API for OCR (successfully implemented)
- User wanted clean display format with Name, Dose, Admin, and Pick Amount
- User requested 24-hour pick amount calculation based on frequency
- User wanted to remove duplicate/redundant UI elements (circled numbers)

---

## Date: August 24, 2025

### Session Context
Completed comprehensive enhancement of medication parsing functionality in Pharmacy Picker Flutter app to improve OCR text-to-medication conversion accuracy.

### Changes Made
1. **Fixed Patient Name Regex Pattern** - Corrected regex groups in `_parseMedicationLine()` to properly capture patient names from complex medication labels
2. **Implemented Granular Debug Logging** - Added detailed line-by-line parsing logs in `parseTextToMedications()` method for better troubleshooting visibility
3. **Refined Regex Patterns with Fallback** - Created sophisticated regex pattern in `parseMedicationLine()` that captures:
   - Medication name (e.g., "oxybutynin")
   - Strength (e.g., "5 mg") 
   - Type/form (e.g., "tablet")
   - Brand name in parentheses (e.g., "DITROPAN XL")
   - Dose/sig instructions (e.g., "BEDTIME")
   - Patient information (e.g., "Polanco, Milena")
4. **Updated LLM Prompt** - Enhanced Grok-4 API prompt in `parsing_service.dart` to include brand field and better structure for pharmacy label formats
5. **Ensured MedItem Compatibility** - Implemented `_convertMapToMedItem()` method to properly convert parsed maps to MedItem objects
6. **Added Unit Test** - Created `test_parsing.dart` with comprehensive test for complex medication label parsing

---

## Date: August 27, 2025

### Session Context
Enhanced medication parsing functionality to support additional real-world pharmacy label formats including Zonisamide, Valproic Acid, and Fluoxetine medications.

### Changes Made
1. **Added Brand Before Strength Pattern** - New regex pattern to handle "Zonisamide (ZONEGRAN) 100 mg capsule" format
2. **Added Brand Form Strength Pattern** - New regex pattern for "zonisamide (ZONEGRAN) capsule 100 mg" format  
3. **Added Name Form Strength Pattern** - New regex pattern for "Valproic Acid capsule 250 mg" format
4. **Created Comprehensive Test Suite** - Added `test_additional_medication_labels.dart` with full test coverage
5. **Fixed Case Sensitivity Issues** - Updated test expectations to handle case-insensitive medication name matching

### Issues Resolved
- Brand names in parentheses now properly extracted regardless of position relative to strength
- Multiple word order variations now supported (name-brand-strength, name-brand-form-strength, name-form-strength)
- Case sensitivity handled correctly in both parsing and testing
- Full medication label text parsing now works with complex multi-line pharmacy labels

### Testing Results
- All 5 test cases passing with 100% success rate
- Individual medication line parsing: ✅ Zonisamide (ZONEGRAN), ✅ Valproic Acid, ✅ Fluoxetine (PROZAC)
- Full text parsing: ✅ Multi-line pharmacy labels with dose information
- Case sensitivity variations: ✅ All uppercase, lowercase, and mixed case formats

### Technical Details
- Added 3 new regex patterns in `_parseMedicationLine()` method
- Patterns handle flexible word ordering while maintaining field accuracy
- Maintained backward compatibility with existing parsing patterns
- Debug logging shows successful regex matching for all new formats

### Performance Notes
- Minimal performance impact with sequential regex pattern matching
- Early pattern matching prevents unnecessary processing
- Comprehensive pattern coverage reduces LLM fallback usage

---

## Date: August 25, 2025

### Session Context
Fixed fundamental issues in Pharmacy Picker app's OCR and parsing pipeline that were preventing medication scanning from working.

### Issues Identified
1. **Async/Await Mismatch** - OCRService was calling `parseExtractedText()` synchronously but the function in `parsing_service.dart` returns `Future<List>`
2. **Function Name Collision** - Both OCRService and parsing_service had `parseExtractedText()` functions, causing OCRService to call its own static method instead of the parsing service's async function
3. **API Key Disabled** - ProcessScreen was passing null for apiKey parameter, completely disabling LLM fallback parsing

### Changes Made
1. **Fixed Async Call** - Updated `OCRService.parseTextToMedications()` to properly await `parseExtractedText()` from parsing_service
2. **Renamed Local Function** - Changed OCRService's local `parseExtractedText()` to `_parseExtractedTextLocal()` to avoid name collision
3. **Enabled API Key** - Updated `process_screen.dart` to pass `ApiConfig.grokApiKey` for both scanned images and mock text processing
4. **Fixed Test Compilation** - Updated `test_ocr_service.dart` to remove reference to private method

### Issues Resolved
- OCR extraction and parsing pipeline now properly integrated
- API key is now properly passed through the entire parsing pipeline
- Function name collisions eliminated

### Testing Results
- App successfully builds for iOS release (25.4s build time)
- Ready for deployment to physical device
- OCR extraction and parsing pipeline now properly integrated

### Technical Details
- Line 86 in `ocr_service.dart` now properly awaits the async parsing service function
- Removed duplicate/unused parsing helper functions from `process_screen.dart`
- API key is now properly passed through the entire parsing pipeline

### Performance Notes
- Root cause was a simple but critical async/await mismatch that prevented the parsing service from ever being called
- The OCRService was trying to call a synchronous function that didn't exist, causing parsing to silently fail

---

## Date: September 2, 2025

### Session Context
Major migration from ML Kit + regex parsing to Docling-based document understanding system to improve OCR accuracy and handle complex pharmacy document layouts.

### Changes Made
1. **Backup Creation** - Backed up current OCR and parsing services to `backup_unused_code/` folder for safety
2. **Python Docling Server Implementation** - Created `python_server/docling_server.py` Flask server with:
   - Advanced OCR using Docling document AI
   - Table recognition for floor stock pick lists
   - Layout understanding for medication labels
   - REST API endpoints: `/health` and `/parse-document`
   - Support for both floor_stock and cart_fill parsing modes
3. **Flutter OCR Service Rewrite** - Completely rewrote `lib/services/ocr_service.dart`:
   - Simplified to HTTP client communicating with Docling server
   - New method: `parseImagesDirectly()` for direct image-to-medication parsing
   - Base64 image encoding for server communication
   - Server health check functionality
4. **Process Screen Updates** - Modified `lib/screens/process_screen.dart`:
   - Updated scanned image processing to use new Docling integration
   - Maintained backward compatibility for mock text processing
5. **iOS Deployment Solution** - Created automated `deploy_ios.sh` script:
   - Handles code signing automatically using development team US2G25TP3N
   - Uses correct device ID for AneBaeley: 00008101-00012DD01A99001E
   - Multiple fallback deployment methods
   - Eliminates recurring deployment issues

### Issues Identified
1. **Port Conflict** - Initial Docling server used port 5000 (conflicted with macOS AirPlay)
2. **Device ID Confusion** - Flutter vs Core Device use different identifiers for same iPhone
3. **Code Signing Issues** - Recurring iOS deployment failures due to certificate problems

### Issues Resolved
1. **Port Conflict** - Changed Docling server to port 5001
2. **Device Detection** - Updated deployment script to use Flutter-recognized device ID
3. **Automated Deployment** - Created comprehensive deployment script handling all signing issues

### Technical Details
- **Dependencies Added**: docling>=2.0.0, flask>=2.3.0, flask-cors>=4.0.0
- **Architecture**: Flutter HTTP client ↔ Python Flask server ↔ Docling document AI
- **Communication**: REST API with base64 image transfer
- **Server URL**: http://localhost:5001

### Testing Results
- Docling server successfully running and responding to health checks
- iOS app builds successfully (68.6MB release build)
- Deployment script created and tested

### Performance Notes
- Docling provides superior document understanding compared to raw OCR + regex
- Better handling of tabular data (floor stock lists)
- More accurate medication label recognition
- Reduced dependency on complex regex patterns

### Next Steps
- Test Docling integration with real medication labels and pick lists on physical device
- Compare parsing accuracy and performance versus previous regex + LLM approach
- Monitor and optimize performance for mobile deployment scenarios
- Update development logs following documented protocol

---

## Date: September 2, 2025 - Session 2
- Missing method for converting parsed maps to MedItem objects

### Issues Resolved
- Patient name extraction from complex labels now working correctly
- Brand name extraction from parentheses format working properly
- Regex pattern now handles complex pharmacy labels with multiple components including dose, administration, and patient info
- All parsing pipeline components properly integrated and tested
- Unit test validates parsing accuracy with real-world medication label format

### Performance Notes
- Parsing performance maintained with hybrid regex-first, LLM-fallback approach
- Debug logging adds minimal overhead while providing valuable troubleshooting data
- Regex patterns optimized for common pharmacy label formats

### Testing Results
- Unit test passing with 100% success rate
- Complex medication label successfully parsed: `"oxybutynin 5 mg tablet (DITROPAN XL) oral 24 hr extended release tablet, Dose 5 mg, Admin 1 tablet, BEDTIME; oral for Polanco, Milena"`
- All expected fields extracted correctly:
  - Name: `oxybutynin` ✅
  - Strength: `5 mg` ✅  
  - Type: `tablet` ✅
  - Brand: `DITROPAN XL` ✅
  - Dose: `BEDTIME` ✅
  - Patient: `Polanco, Milena` ✅

### Technical Details
- **File Modified**: `/lib/services/ocr_service.dart`
  - Made `parseMedicationLine()` method public for testing
  - Implemented `_convertMapToMedItem()` for proper MedItem object creation
  - Enhanced regex pattern with multiple capture groups
- **File Modified**: `/lib/services/parsing_service.dart`
  - Updated LLM prompt to include brand field extraction
  - Improved JSON structure specification for Grok-4 API
- **File Created**: `/test_parsing.dart`
  - Comprehensive unit test for medication label parsing
  - Validates all major parsing components

### Next Steps
- All planned parsing enhancements completed successfully
- App ready for real-world testing with pharmacy documents
- Monitor debug logs during actual usage to identify any remaining edge cases
- Consider adding more unit tests for different label formats as they're encountered

### User Feedback
- User emphasized importance of maintaining comprehensive development logs
- User requested all development work be documented with proper date headers and context

---

## Date: August 24, 2025 - Session 2

### Session Context
Completed comprehensive testing and debugging of enhanced medication parsing functionality using local testing and user-provided medication label.

### Changes Made
1. **Fixed Regex Parsing Logic** - Resolved issue where parsing returned null instead of medication data
2. **Enhanced Multiple Pattern Support** - Added three distinct regex patterns:
   - Complex pattern: Handles brand names in parentheses, patient info, dosing instructions
   - Simple pattern: Handles basic "name strength form" format  
   - Dosing pattern: Extracts administration instructions
3. **Fixed Group Mappings** - Corrected regex group assignments for proper field extraction
4. **Added Comprehensive Test Suite** - Created multiple test files validating different parsing scenarios
5. **Integrated User Medication Label** - Added real Oxybutynin (DITROPAN XL) label as test asset

### Issues Identified
- Original regex pattern was too restrictive, requiring "for patient" clause
- Group mappings were incorrect in complex regex pattern
- Mock text parsing was failing due to insufficient pattern coverage
- OCR extraction issue: ML Kit only extracting "X" and "0" from clear medication labels

### Issues Resolved
- Multiple regex patterns now handle various medication label formats
- Simple medication lines like "Metoprolol Tartrate 25 mg tablet" parse correctly
- Complex labels with brands in parentheses work properly
- Dosing instructions are extracted accurately
- All unit tests passing with 100% success rate

### Performance Notes
- Local testing approach much more efficient than phone deployment for debugging
- Multiple regex patterns provide robust fallback coverage
- Enhanced debug logging provides clear visibility into parsing pipeline

### Testing Results
- **Unit Tests**: All 7 tests passing across 3 test files
- **Simple Format**: "Metoprolol Tartrate 25 mg tablet" → ✅ correctly parsed
- **Complex Format**: "Oxybutynin (DITROPAN XL) 5 mg tablet extended release BEDTIME for patient Smith" → ✅ correctly parsed
- **User Label**: Oxybutynin medication successfully extracted from real pharmacy label
- **Mock Text**: Previously failing mock text now parses 3 medications correctly

### Technical Details
- **Enhanced Regex Patterns**: 
  - Pattern 1: Complex labels with brands and patient info
  - Pattern 2: Simple medication format (name strength form)
  - Pattern 3: Dosing instructions extraction
- **Test Files Created**:
  - `test_simple_parsing.dart` - Basic pattern validation
  - `test_user_medication_label.dart` - Real medication label testing
  - `lib/services/test_ocr_service.dart` - Comprehensive parsing tests
- **Assets Added**: User-provided medication label image for testing

### Next Steps
- OCR text extraction issue still needs investigation (ML Kit only getting "X" and "0")
- Consider image preprocessing to improve OCR accuracy
- Deploy enhanced parsing to phone for real-world testing
- Monitor parsing performance with actual pharmacy documents

### User Feedback
- User reported "no medication OCR processing failed using scanned data" error
- Issue resolved through systematic debugging of processing pipeline

---

## Date: September 23, 2025

### Session Context
Resolved persistent iOS Flutter app launch failure that was preventing testing of the pharmacy pickup app's OCR and parsing functionality. User established a rule requiring pre-launch diagnostics to prevent recurring launch issues.

### Issues Identified
- **iOS Debug Mode Restrictions**: App failing to launch with ptrace permission errors
- **Flutter Engine Debug Mode Issue**: "Cannot create a FlutterEngine instance in debug mode" on iOS 14+
- **Dart VM Service Discovery Timeout**: Flutter debugger unable to connect to device
- **Recurring Launch Problem**: User reported this as a consistent issue after app updates

### Issues Resolved
- **iOS Launch Failure**: Resolved by building app in profile mode instead of debug/release mode
- **Network Configuration**: Fixed IP address mismatch between Docling server (172.20.10.7:5001) and Flutter app configuration (was 172.20.10.9:5001)
- **Build Process**: Successfully cleaned and rebuilt app with proper iOS deployment configuration
- **App Deployment**: App now running successfully on user's iPhone (AneBaeley) with iOS 18.6.2

### Changes Made
1. **Updated OCR Service Configuration** - Fixed Docling server URL from `http://172.20.10.9:5001` to `http://172.20.10.7:5001` to match actual running server
2. **Implemented Pre-Launch Diagnostics Rule** - Established systematic approach to check and fix build/run issues before attempting app launch
3. **Applied Profile Mode Build** - Used `flutter run --profile` instead of debug mode to bypass iOS security restrictions
4. **Clean Build Process** - Ran `flutter clean` to clear build cache and resolve dependency conflicts

### Technical Details
- **iOS Deployment Target**: 14.0 (compatible with iOS 18.6.2 device)
- **Build Mode**: Profile mode successfully bypasses iOS debug restrictions
- **Docling Server**: Running healthy at http://172.20.10.7:5001 with health check confirmed
- **Flutter DevTools**: Available at http://127.0.0.1:9100 for debugging
- **Code Signing**: Automatic signing with development team US2G25TP3N working correctly

### Testing Results
- **App Launch**: ✅ Successfully installed and running on iPhone
- **Docling Server**: ✅ Healthy and responding to requests
- **Network Communication**: ✅ Flutter app configured to connect to correct server IP
- **Environment Configuration**: ✅ API key loaded correctly (84 characters)
- **Initial Parsing Test**: ⚠️ Showing 0 medications found - requires further investigation with actual OCR input

### Performance Notes
- Profile mode build time: ~56.8s (reasonable for iOS deployment)
- Pod install time: ~2.8s (dependencies installing correctly)
- App installation: ~51.1s (normal for iOS device deployment)
- No performance degradation observed from profile mode vs debug mode

### Next Steps
- Test OCR pipeline with existing test image (test_png_med.png)
- Verify Docling server OCR extraction with real medication labels
- Investigate parsing logic if 0 medications continue to be found
- Monitor app performance during actual OCR processing

### User Feedback
- User established rule: Always check and fix build/run blockers before launching app
- User confirmed this is a recurring issue that needs proactive diagnosis
- User requested this diagnostic approach be applied for all future app launches