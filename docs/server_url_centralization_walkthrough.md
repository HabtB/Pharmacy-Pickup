# Server URL Centralization — Walkthrough

## What Changed

| File | Action | Summary |
|------|--------|---------|
| [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart) | **NEW** | Centralized singleton wrapping `ServerDiscoveryService` |
| [auth_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/auth_service.dart) | **MODIFIED** | Removed hardcoded IP, uses `AppServerConfig`; fixed `logout()` |
| [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart) | **MODIFIED** | Removed private discovery logic, uses `AppServerConfig` |
| [main.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/main.dart) | **MODIFIED** | Calls `AppServerConfig.instance.ensureDiscovered()` at startup |

## Key Fixes

**Before**: `AuthService` used hardcoded `http://172.20.10.9:5003/api` while `OCRService` scanned subnets to find the server — they often pointed at different addresses.

**After**: Both services get the URL from `AppServerConfig.instance`, which discovers once at app launch.

```diff
- static const String baseUrl = 'http://172.20.10.9:5003/api';
+ static String get _apiUrl => AppServerConfig.instance.apiUrl;
```

**Bonus fix** — `logout()` was calling `prefs.clear()` which wiped saved medication sessions:

```diff
-  await prefs.clear();
+  await prefs.remove(keyUserId);
+  await prefs.remove(keyUsername);
+  await prefs.remove(keyRole);
```

## Verification

- `flutter analyze lib/` — **0 new errors**. All 17 pre-existing errors are in `image_enhancement_service.dart` and `test_ocr_service.dart` (unrelated missing packages).
