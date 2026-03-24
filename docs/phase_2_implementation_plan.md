# Phase 2 — Architecture Refactor

## Goal

Phase 1 (security hardening) is complete. Phase 2 addresses two plan items from `improvement_plan_2.md`:

- **2.1 — State Management**: All three main screens embed their business logic inside `StatefulWidget` state classes. This couples logic to widgets and makes isolated unit testing impossible. The fix is to extract logic into `ChangeNotifier`-based controllers (no new packages needed — `ChangeNotifier` is in Flutter's SDK).
- **2.2 — Monolithic Screens**: `process_screen.dart` (597 lines), `scan_screen.dart` (466 lines), and `slideshow_screen.dart` (442 lines) mix logic, UI, and dialogs in a single file each.
- **2.3 — Mock/Debug Code Not Guarded**: "Test OCR" and "Add More" debug buttons are always visible regardless of build mode.

---

## Proposed Changes

### Controllers

#### [NEW] [scan_controller.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/controllers/scan_controller.dart)
Extracts all non-UI logic from `_ScanScreenState`:
- Camera initialization (`_initializeCamera`)
- Image capture (`_captureImage`)
- Gallery picking (`_pickFromGallery`)
- Exposes `scannedImages`, `isInitialized`, `isDesktop`, `error`
- `CameraController` lifecycle (dispose)

#### [NEW] [process_controller.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/controllers/process_controller.dart)
Extracts all non-UI logic from `_ProcessScreenState`:
- OCR image processing (`processScannedImages`) — wraps existing `ProcessingController` + `OCRService`
- Mock text processing (`processMockText`)
- Medication processing/navigation (`processMedications`)
- Exposes `scannedMedications`, `processedMedications`, `isProcessing`, `processingController`

#### [NEW] [slideshow_controller.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/controllers/slideshow_controller.dart)
Extracts all non-UI logic from `_SlideshowScreenState`:
- Medication sorting (`getPriority`, `_getLocationPriority`)
- Location grouping (`_buildLocationGroups`)
- Toggle complete, adjust qty, warning edit, save progress  
- Exit handling (`_handleExit` — save + navigate)
- Exposes current location, stats, carousel controller

---

### Extracted Widgets

#### [NEW] [lib/widgets/process/process_header.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/process/process_header.dart)
The mode title card with icon, title, and subtitle (~30 lines).

#### [NEW] [lib/widgets/process/ocr_progress_dialog.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/process/ocr_progress_dialog.dart)
The `AlertDialog` with `ListenableBuilder` that shows progress, pause/resume, and stop controls (~100 lines).

#### [NEW] [lib/widgets/process/process_action_buttons.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/process/process_action_buttons.dart)
The Add More / Start Picking / Clear All button row (~80 lines). Debug "Add More" button guarded with `kDebugMode`.

#### [NEW] [lib/widgets/scan/camera_preview_area.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/scan/camera_preview_area.dart)
The camera preview, error display, and desktop fallback widget (~90 lines).

#### [NEW] [lib/widgets/scan/scan_action_buttons.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/scan/scan_action_buttons.dart)
The Scan Page / Gallery / Test OCR / Process page buttons (~80 lines). Test OCR button guarded with `kDebugMode`.

---

### Utility

#### [NEW] [lib/utils/location_priority_helper.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/utils/location_priority_helper.dart)
Extracts the duplicated `getPriority` / `_getLocationPriority` logic from `slideshow_screen.dart` into a single static class.

---

### Modified Screens

#### [MODIFY] [process_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/process_screen.dart)
- Replace `_ProcessScreenState` logic with `ProcessController` via `ListenableBuilder`
- Replace inline dialog/header/buttons with the 3 new widgets above
- Target: ~120 lines (down from 597)

#### [MODIFY] [scan_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/scan_screen.dart)
- Replace `_ScanScreenState` logic with `ScanController`
- Replace inline camera preview + buttons with the 2 new widgets above
- Target: ~80 lines (down from 466)

#### [MODIFY] [slideshow_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart)
- Replace inline logic with `SlideshowController` + `LocationPriorityHelper`
- Target: ~200 lines (down from 442)

---

## Verification Plan

### Automated Tests

**Step 1 — Static Analysis**
```bash
cd /Users/habtamu/Documents/pharmacy_pickup_app_dev
flutter analyze lib/
```
Expected: 0 new errors. Pre-existing warnings (deprecations, `opencv_4`) will still be present but the count must not increase.

**Step 2 — Existing Unit Tests**
```bash
cd /Users/habtamu/Documents/pharmacy_pickup_app_dev
flutter test
```

> [!NOTE]
> `app_test.dart` references `TextParser` and `DatabaseService.getAllMedications()` which may or may not exist at test time (some tests are smoke tests against the real DB). Tests that pass before the refactor must still pass after.

**Step 3 — New Controller Unit Tests** (written during execution)

`test/controllers/process_controller_test.dart`:
- `processMockText` with known input → expected `MedItem` list
- `processScannedImages` with empty list → `scannedMedications` remains empty

`test/controllers/slideshow_controller_test.dart`:
- Sorting: medications with different `pickLocationDesc` values are ordered by priority
- `toggleComplete` flips `isPicked` on the correct index
- `_updateActualQuantity` clamps to 0 minimum

```bash
flutter test test/controllers/
```

### Manual Verification (after running the app)

**Step 1** — Run the app on a device/simulator:
```bash
cd /Users/habtamu/Documents/pharmacy_pickup_app_dev
flutter run
```

**Step 2 — Scan Screen**
1. Navigate to any mode → Scan screen appears
2. Camera initialises (or fallback message shows on desktop) ✅
3. Tap **Gallery** → image picker opens ✅
4. In **debug mode only**: "Test OCR (Mock Data)" button is visible ✅
5. In **release mode** (`flutter run --release`): "Test OCR" button is **not visible** ✅

**Step 3 — Process Screen**
1. After scanning an image, arrive at Process screen
2. Header card shows correct mode title ✅
3. Progress dialog shows with Pause/Resume/Stop controls during OCR ✅
4. In **debug mode only**: "Add More" button is visible ✅
5. "Start Picking" is disabled while processing ✅
6. After processing, tap "Start Picking" → navigates to Slideshow ✅

**Step 4 — Slideshow Screen**
1. Medications are sorted by location priority ✅
2. Toggle complete on a card → card shows as completed ✅
3. Adjust quantity → updates immediately ✅
4. Tap back/exit → save dialog appears ✅
