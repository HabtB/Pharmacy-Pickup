# Phase 3 — Efficiency Improvements

Covers improvement_plan_2.md items §2.4 (server discovery), §2.5 (base64 → multipart), and §2.6 (MedItem cleanup).

---

## Proposed Changes

### 3.1 Multipart Image Upload (replaces Base64 JSON)

Current state: `ocr_service.dart` encodes images to base64 (+33% overhead), wraps them in JSON, and sends them. For 5 high-res images this can exceed 30 MB.

#### [MODIFY] [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart)

- Replace all 4 `base64Encode` call sites with `http.MultipartRequest`
- `_parseWithRetry()`: send single image as multipart file field
- `_parseImagesParallel()`: send multiple images as multipart file fields
- `extractTextFromImages()`: convert to multipart
- Remove `dart:convert` base64 imports if no longer needed

#### [MODIFY] [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py)

- `/parse-document`: accept **both** multipart form-data (preferred) and JSON base64 (backward compat)
- `/parse-documents-parallel`: accept multipart form-data with multiple file fields
- Use `request.files` for multipart; fall back to `request.get_json()` for legacy base64

---

### 3.2 Server Discovery — TTL-Based Cache Invalidation

Current state: `ServerDiscoveryService` already has a 3-step strategy (cached → common IPs → full scan) and persists to SharedPreferences. This is solid. The only gap is there's no TTL — once discovered, the cache is used forever even if the server IP changes.

#### [MODIFY] [server_discovery_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/server_discovery_service.dart)

- Store cache timestamp alongside the URL in SharedPreferences
- Add a configurable TTL (default: 1 hour)
- In `_loadCachedServer()`, check if the cached entry is expired; if so, return null so discovery re-runs
- Add `setCacheTimeout()` for testing/configuration

#### [MODIFY] [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart)

- `ensureDiscovered()`: add a `force` parameter to bypass TTL check on user request
- Background health-check: after returning cached URL, schedule a non-blocking `_testServer` call to verify the cached server is still alive; if it's not, invalidate cache

---

### 3.3 MedItem Cleanup with Equatable

Current state: 22-field model with hand-written `==`, `hashCode` (XOR-chain, collision-prone), `copyWith`, `fromMap`, `toMap`. `equatable` package already in `pubspec.yaml`.

#### [MODIFY] [med_item.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/models/med_item.dart)

- Extend `Equatable` — removes the need for manual `==` and `hashCode`
- Override `props` with all 22 fields (including `floorBreakdown`)
- Delete the hand-written `operator ==` and `hashCode` getter
- Keep `copyWith`, `fromMap`, `toMap`, and `_calculateFromSig` as-is
- Keep `toString()` as-is

---

## Verification Plan

### Automated Tests
```bash
# Static analysis
flutter analyze lib/services/ocr_service.dart lib/services/server_discovery_service.dart \
  lib/services/app_server_config.dart lib/models/med_item.dart

# Existing + new unit tests
flutter test test/
```

### Manual Verification
- Start the Python server, scan a prescription, verify multipart upload works end-to-end
- Kill and restart server on a different IP, verify TTL-based re-discovery kicks in
- Verify `MedItem` equality and hashCode correctness in tests
