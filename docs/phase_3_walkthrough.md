# Phase 3 — Efficiency Improvements Walkthrough

## What Changed

### 3.1 Multipart Image Upload (replaces Base64 JSON)

**Problem:** `ocr_service.dart` encoded images to Base64 (+33% overhead), wrapped them in JSON, and sent them. For 5 high-res images this exceeded 30 MB.

**Fix:** Replaced all 4 `base64Encode` call sites with `http.MultipartRequest`:

| Method | Before | After |
|--------|--------|-------|
| `extractTextFromImages` | base64 → JSON body | `MultipartFile.fromBytes('image', ...)` |
| `_parseWithRetry` | accepts base64 string | accepts file path, builds multipart |
| `_parseImagesParallel` | encodes all to base64 array | uses `image_0`, `image_1`, ... file fields |
| sequential fallback | encodes individually | passes file path to `_parseWithRetry` |

Server-side, both `/parse-document` and `/parse-documents-parallel` now accept multipart form-data **and** fall back to JSON base64 for backward compatibility.

**Files changed:**
- [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart)
- [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py)

---

### 3.2 Server Discovery — TTL Cache

**Problem:** Once discovered, the server URL was cached forever, even if the server IP changed.

**Fix:**
- Cache timestamp stored alongside URL in SharedPreferences
- 1-hour TTL (configurable via `setCacheTtl()`)
- Background health-check: after returning a cached URL, `AppServerConfig` fires a non-blocking GET `/health` — if unreachable, silently invalidates cache
- `ensureDiscovered(force: true)` bypasses cache entirely

**Files changed:**
- [server_discovery_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/server_discovery_service.dart)
- [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart)

---

### 3.3 MedItem → Equatable

**Problem:** Hand-written `operator ==` (missed `floorBreakdown`) and XOR-chain `hashCode` (collision-prone).

**Fix:**
- Extended `Equatable` (already in `pubspec.yaml`)
- Overrode `props` with all 22 fields including `floorBreakdown`
- Deleted 50 lines of boilerplate `==`/`hashCode`

**File changed:**
- [med_item.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/models/med_item.dart)

---

## Test Results

```
$ flutter analyze — 0 issues
$ flutter test test/controllers/ test/models/ — 40 tests passed
```

| Test file | Tests | Status |
|-----------|-------|--------|
| `slideshow_controller_test.dart` | 13 | ✅ |
| `process_controller_test.dart` | 15 | ✅ |
| `med_item_test.dart` | 12 | ✅ |
