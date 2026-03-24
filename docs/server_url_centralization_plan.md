# Centralize Server URL Management

The app currently has two separate server URL strategies that conflict:
- `AuthService` hardcodes `http://172.20.10.9:5003/api` — breaks when the network changes
- `OCRService` uses `ServerDiscoveryService` to scan subnets — works but only for OCR
  
This change creates a **single source of truth** for the server URL that all services share.

## Proposed Changes

### Services Layer

#### [NEW] [app_server_config.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/app_server_config.dart)

A centralized singleton that wraps `ServerDiscoveryService` and provides the server base URL + API URL to all services. Key design decisions:

- **Lazy initialization**: Discovers on first use, caches for app lifetime
- **Re-discovery**: `rediscover()` method for manual retry after network change
- **Two accessors**: `baseUrl` (e.g., `http://192.168.1.134:5003`) and `apiUrl` (e.g., `http://192.168.1.134:5003/api`)
- Delegates actual subnet scanning to the existing `ServerDiscoveryService`

---

#### [MODIFY] [auth_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/auth_service.dart)

- **Remove** the hardcoded `baseUrl` constant (`http://172.20.10.9:5003/api`)
- **Add** dynamic URL resolution via `AppServerConfig.instance.apiUrl`
- **Fix `logout()`**: Change `prefs.clear()` → only remove auth-specific keys (`keyUserId`, `keyUsername`, `keyRole`)

```diff
-  static const String baseUrl = 'http://172.20.10.9:5003/api';
+  // Server URL resolved dynamically via AppServerConfig
```

```diff
   static Future<void> logout() async {
     final prefs = await SharedPreferences.getInstance();
-    await prefs.clear();
+    await prefs.remove(keyUserId);
+    await prefs.remove(keyUsername);
+    await prefs.remove(keyRole);
   }
```

---

#### [MODIFY] [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart)

- **Remove** the private `_discoverServer()` method and `_serverDiscovered` / `_doclingServerUrl` fields
- **Replace** all `$_doclingServerUrl` references with `AppServerConfig.instance.baseUrl`
- The `ServerDiscoveryService` import is no longer needed directly — `AppServerConfig` wraps it

---

#### [MODIFY] [main.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/main.dart)

- **Add** early initialization of `AppServerConfig` during app startup (after dotenv load, before `runApp`)
- This ensures the server is discovered once at launch rather than on each service's first call

---

## Verification Plan

### Build Check
Run the Flutter build to ensure there are no compile errors:
```bash
cd /Users/habtamu/Documents/pharmacy_pickup_app_dev && flutter analyze
```

### Existing Tests
The existing tests in `test/app_test.dart` reference `TextParser` and `DatabaseService` — they don't test server connectivity or auth directly, so they should remain unaffected.

### Manual Verification
Since this is a networking change that requires a physical device or running server:
1. Start the Python server: `cd python_server && python docling_server.py`
2. Run the app on a connected device or simulator
3. Verify the login screen successfully connects (no hardcoded IP mismatch)
4. Verify OCR scanning still works with the same server URL
