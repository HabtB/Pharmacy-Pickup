# Pharmacy Pickup App — Architecture Review & Improvement Plan

> Full review conducted February 24, 2026
> Last updated: February 25, 2026

## App Flow

```
LoginScreen → ModeSelectionScreen (Floor Stock / Cart-Fill)
  → ScanScreen (Camera / Gallery)
    → DocumentReviewScreen (Review scanned pages)
      → ProcessScreen (OCR + AI parsing)
        → SlideshowScreen (Picking workflow carousel)
```

## Completed Improvements

- [x] **Centralize server URL management** — Created `AppServerConfig` singleton (see `server_url_centralization_plan.md`)
- [x] **Fix logout wiping all data** — `logout()` now only clears auth keys
- [x] **Split `slideshow_screen.dart`** (1621 → ~330 lines) — Extracted 4 widgets to `lib/widgets/slideshow/` (see `slideshow_split_plan.md`)
- [x] **Replace debug print statements** — Created `AppLogger` utility wrapping `dart:developer log()`; ~180 `print()` calls replaced across 18 files (see `cleanup_walkthrough.md`)
- [x] **Enable `avoid_print` lint** — Future `print()` usage caught at analysis time
- [x] **Move test file** — `test_ocr_service.dart` moved from `lib/services/` → `test/`
- [x] **Delete stale backup** — Removed `process_screen_backup_before_ui_changes_20250930_0537.dart`

## Remaining Improvements

### High Priority
1. **Add settings screen for manual server IP entry** — Fallback for when auto-discovery fails
2. **Fix `image_enhancement_service.dart`** — Missing `opencv_4` dependency causes 16 analyzer errors; either add the dep or remove the unused service
3. **Fix "Add More" button** on ProcessScreen — Currently adds hardcoded demo data; should scan more pages
4. **Guard dev-only UI** — Hide "Test OCR (Mock Data)" button using `kDebugMode`

### Medium Priority
5. **Fix deprecated API usage** — Replace `withOpacity` → `withValues()` (~6 warnings), `onPopInvoked` → `onPopInvokedWithResult` (~2 warnings)
6. **Clean up unused code** — Remove dead code and unused elements flagged by analyzer (`_isMedicationNameMatch`, `_inferGeneralLocation`, `_isBackBottomVial`, `_isIVBag`, `_getLocationPriority`, `_parseFloorStockFormat`, `_parseCartFillFormat`)
7. **Remove unused imports** in `main.dart` (4 warnings)
8. **Fix `use_build_context_synchronously`** in `document_review_screen.dart` (4 warnings)
9. **Add state management** — Consider `Riverpod` or `BLoC` as the app grows
10. **Python server hardening** — Move default user creation to a seed script; use `gunicorn` for production
11. **Add document auto-crop** before sending to OCR

### Low Priority
12. Dark mode support
13. Offline mode (queue OCR when server unreachable)
14. Pick history with timestamps for audit
15. Barcode verification during picking
16. Multi-language support
17. Accessibility improvements (semantic labels)

## Documentation
All plans and walkthroughs are saved in `docs/`:
- `server_url_centralization_plan.md` — Server URL centralization implementation plan
- `server_url_centralization_walkthrough.md` — Server URL centralization walkthrough
- `slideshow_split_plan.md` — Slideshow screen split implementation plan
- `cleanup_plan.md` — Print replacement & file cleanup implementation plan
- `cleanup_walkthrough.md` — Print replacement & file cleanup walkthrough
- `DEVELOPMENT_LOG.md` — Daily development session documentation
