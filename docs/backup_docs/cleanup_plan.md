# Cleanup Updates — Replace print(), Move Test, Delete Backup

Continuing with the planned next steps from the Feb 24 dev log.  
All changes are safe refactors — no business logic is modified.

## Proposed Changes

### Logger Utility

#### [NEW] [app_logger.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/utils/app_logger.dart)

Create a thin wrapper around `dart:developer` `log()`.  
Provides `AppLogger.info()`, `AppLogger.warn()`, and `AppLogger.error()` that:

- Use `dart:developer log()` (shows in DevTools, not captured in release)
- Accept an optional `name` tag so logs read like `ServerDiscovery: ✓ Found at 192.168...`
- No new dependencies needed — `dart:developer` is part of the SDK

---

### Replace print() → AppLogger (18 files)

Every `print()` in `lib/` will be replaced with the appropriate `AppLogger` method:

| File | print() count | Notes |
|------|:---:|-------|
| [server_discovery_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/server_discovery_service.dart) | ~15 | Info + error calls |
| [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart) | many | Debug logging |
| [process_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen.dart) | many | Debug logging |
| [slideshow_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart) | several | Debug + error |
| [medication_slide_card.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/slideshow/medication_slide_card.dart) | 1 | Error catch |
| [storage_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/storage_service.dart) | 5 | Info + error |
| [auth_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/auth_service.dart) | 1 | Error catch |
| [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart) | 1 | Info |
| [image_enhancement_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/image_enhancement_service.dart) | ~10 | Debug steps |
| [main.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/main.dart) | several | Startup logging |
| [database_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/database_service.dart) | several | Debug logging |
| [medication_processor.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/medication_processor.dart) | several | Debug logging |
| [debug_processor.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/debug_processor.dart) | several | Debug logging |
| [parsing_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/parsing_service.dart) | several | Debug logging |
| [location_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/location_service.dart) | several | Debug logging |
| [scan_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/scan_screen.dart) | several | Debug logging |
| [config/api_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/config/api_config.dart) | several | Debug logging |

---

### Enable Lint Rule

#### [MODIFY] [analysis_options.yaml](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/analysis_options.yaml)

Uncomment `avoid_print: true` to catch any future `print()` calls at analysis time.

---

### Move Test File

#### [DELETE] [test_ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/test_ocr_service.dart) (from lib/services)
#### [NEW] [test_ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/test/test_ocr_service.dart) (moved to test/)

Move the file and update its imports. Since this file uses `print()` for test output, those will be kept (test files are typically excluded from `avoid_print`).

---

### Delete Backup File

#### [DELETE] [process_screen_backup_before_ui_changes_20250930_0537.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen_backup_before_ui_changes_20250930_0537.dart)

This backup from Sep 30, 2025 is no longer needed — the changes are long committed.

---

## Verification Plan

### Automated Tests
1. **`flutter analyze lib/`** — should return **0 issues** (or only pre-existing deprecation warnings)
2. **`flutter analyze test/`** — verify the moved test file has no import issues
3. **Check for remaining print()** — `grep -rn "print(" lib/` should return **0 results**

### Manual Verification
- Confirm `lib/screens/process_screen_backup_before_ui_changes_20250930_0537.dart` no longer exists
- Confirm `lib/services/test_ocr_service.dart` no longer exists
- Confirm `test/test_ocr_service.dart` exists
