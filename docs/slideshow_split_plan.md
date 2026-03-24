# Split `slideshow_screen.dart` (1621 → ~450 lines)

The file contains the entire picking workflow UI in one 1621-line file. This plan extracts 5 focused widgets into a new `lib/widgets/slideshow/` directory.

## Current Structure

| Section | Lines | What it does |
|---------|-------|-------------|
| State + sorting + location logic | 19–269 | 16 methods for state management, grouping, sorting |
| Navigation + dialogs | 271–326 | Search, jump-to-location, exit dialog |
| `build()` scaffold | 328–431 | AppBar, bottom nav, tab switching |
| `_buildSlideshowTab()` | 433–1266 | Location banner + carousel + summary bar |
| Carousel `itemBuilder` | 529–1226 | **~700 lines** — the individual med card |
| Helper methods | 1288–1389 | Floor breakdown parsing, plural form, image dialog |
| `PreparationTab` | 1392–1620 | Separate StatelessWidget (cups, syringes, fridge alerts) |

## Proposed Changes

### Widgets Layer (`lib/widgets/slideshow/`)

#### [NEW] [preparation_tab.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/slideshow/preparation_tab.dart)
Move `PreparationTab` class (lines 1392–1620) + `_buildAlertCard` to its own file. No logic changes — just a file move.

---

#### [NEW] [medication_slide_card.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/slideshow/medication_slide_card.dart)
Extract the carousel `itemBuilder` content (lines 529–1226) into a `MedicationSlideCard` StatelessWidget. It receives:
- `MedItem med`, `int index`, `bool isCompleted`
- Callbacks: `onToggleComplete`, `onUpdateQuantity`, `onSetQuantity`, `onWarningEdit`
- Helper methods moved here: `_getPluralForm`, `_parseFloorBreakdown`, `_extractOriginalNotes`, `_showLocationImage`

---

#### [NEW] [location_progress_banner.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/slideshow/location_progress_banner.dart)
Extract the green location banner (lines 438–501) into a `LocationProgressBanner` widget receiving `locationStats` map.

---

#### [NEW] [picking_summary_bar.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/slideshow/picking_summary_bar.dart)
Extract the bottom summary row (lines 1230–1266) + `_buildSummaryItem` (lines 1268–1286) into a `PickingSummaryBar` widget receiving total/completed/remaining counts.

---

### Screens Layer

#### [MODIFY] [slideshow_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/slideshow_screen.dart)
After extraction, the file keeps:
- State fields + `initState` with sorting logic (~70 lines)
- Location grouping + priority methods (~130 lines)
- Toggle/quantity/save callbacks (~60 lines)
- Navigation + exit dialog (~60 lines)
- `build()` scaffold (~100 lines)
- `_buildSlideshowTab()` — now slim, delegates to extracted widgets (~30 lines)

**Estimated: ~450 lines** (down from 1621)

---

## Verification Plan

### Build Check
```bash
cd /Users/habtamu/Documents/pharmacy_pickup_app_dev && flutter analyze lib/
```

### Manual Verification
- Confirm carousel navigation, card rendering, and completion toggling work
- Confirm PreparationTab still shows cup/syringe/fridge alerts
- Confirm floor breakdown and location image popups render correctly
