# Phase 4 — Code Quality Improvements

Covers improvement_plan_2.md §3.1 (mock/debug guards), §3.2 (logging cleanup), §3.5 (form validation), §3.6 (accessibility), §3.7 (stricter linting).

> [!NOTE]
> §3.3 (go_router for named routes) is deferred — it's a large refactor that would touch every screen's navigation. §3.4 (duplicated priority logic) was fixed in Phase 2.

---

## Proposed Changes

### 4.1 Guard Mock/Debug Code Behind `kDebugMode`

The "Test OCR" button and "Add More" button are already guarded. One gap remains:

#### [MODIFY] [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart)

- Guard `_createMockMedications()` fallback (line ~232) behind `kDebugMode`
- In production, return an empty list and log a clear error instead of silently injecting fake data

---

### 4.2 Logging Cleanup

#### [MODIFY] [ocr_service.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/services/ocr_service.dart)

- Reduce verbose `=== DEBUG ===` style prefixes — use concise `AppLogger` messages instead

#### [MODIFY] [docling_server.py](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/python_server/docling_server.py)

- Reduce verbose `[DEBUG]` prefixed log lines to `logger.debug()` level so they don't appear at default INFO level

---

### 4.3 Login Form Validation

#### [MODIFY] [login_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/login_screen.dart)

- Wrap inputs in a `Form` widget with a `GlobalKey<FormState>`
- Replace `TextField` → `TextFormField` with `validator` callbacks
- Add `dispose()` to clean up `_usernameController` and `_passwordController`
- Use `_formKey.currentState!.validate()` in `_handleLogin()` instead of manual empty checks

---

### 4.4 Accessibility Improvements

#### [MODIFY] [login_screen.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/screens/login_screen.dart)

- Add `Semantics` label to the logo
- Add `autofillHints` to username/password fields

#### [MODIFY] [scan_action_buttons.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/scan/scan_action_buttons.dart)

- Add `Tooltip` wrappers to icon-only buttons

#### [MODIFY] [process_action_buttons.dart](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/lib/widgets/process/process_action_buttons.dart)

- Add `Tooltip` wrappers to icon-only buttons

---

### 4.5 Stricter Lint Rules

#### [MODIFY] [analysis_options.yaml](file:///Users/habtamu/Documents/pharmacy_pickup_app_dev/analysis_options.yaml)

- Enable: `prefer_const_constructors`, `prefer_const_declarations`, `always_use_package_imports`, `sort_child_properties_last`, `prefer_final_locals`, `use_key_in_widget_constructors`
- Keep existing `avoid_print: true`
- Will **not** auto-fix all lint violations — just enable the rules so future code follows them

---

## Verification Plan

```bash
flutter analyze lib/
flutter test test/controllers/ test/models/
```
