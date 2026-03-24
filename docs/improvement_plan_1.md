# Pharmacy Pickup App Improvement Plan

## Goal Description
Based on a comprehensive review of the `pharmacy_pickup_app_dev` codebase, I have evaluated the app's structural integrity, UI code, and underlying services. While the app has a good foundation—especially in branding and theming (`AppTheme`)—there are significant shortcomings in architecture, state management, security, and efficiency that must be addressed to make the app robust, scalable, and secure.

Below is the robust improvement plan to resolve these issues.

---

## 1. Architecture & State Management Improvements

### Current Shortcomings
*   **Coupled Logic:** Screens like `process_screen.dart` (~600 lines) are monolithic. They heavily blend UI rendering with complex business logic (e.g., managing OCR batching, parsing, error handling, and dialog state).
*   **Rudimentary State Management:** The app relies primarily on basic `setState()`, making it difficult to test logic independently from the UI and prone to unnecessary widget rebuilds.

### Proposed Changes
*   **Implement a robust State Management pattern:** Introduce `Riverpod` or `flutter_bloc`. This will separate business logic into ViewModels/Controllers/Blocs.
*   **Refactor `process_screen.dart`:**
    *   Extract the OCR processing logic into an independent controller (e.g., `ProcessController`).
    *   Break down the massive UI into smaller, reusable widgets (e.g., `ProcessHeaderWidget`, `MedicationListWidget`, `ProcessControlsWidget`).

## 2. Efficiency & Database Performance

### Current Shortcomings
*   **In-Memory Database Search:** `database_service.dart` loads all 255 records into memory for fuzzy matching. While acceptable for a small dataset, it will freeze the UI or consume excessive memory if the database scales to thousands of medications.
*   **Inefficient Data Transfer:** `ocr_service.dart` converts large `XFile` images to `Base64` strings and wraps them in a JSON payload. Base64 adds ~33% overhead, leading to inflated memory usage and slower network requests.

### Proposed Changes
*   **Optimize SQLite Database:** Refactor `database_service.dart` to utilize SQLite Full-Text Search (FTS4/FTS5) or efficient SQL queries `LIKE` with indexing instead of in-memory Dart filtering.
*   **Adopt Multipart Requests:** Refactor `ocr_service.dart` API calls to use `http.MultipartRequest` for sending raw image bytes, avoiding Base64 encoding overhead and reducing memory spikes.

## 3. Security Hardening

### Current Shortcomings
*   **Insecure Data Storage:** `auth_service.dart` stores sensitive user data (`auth_user_id`, `auth_username`, `auth_role`) in plain text using `SharedPreferences`.
*   **API Security:** The application implies transmission of PHI (Protected Health Information like patient names and medications) to backend services. 

### Proposed Changes
*   **Migrate to Secure Storage:** Replace `SharedPreferences` for sensitive data with `flutter_secure_storage` to encrypt tokens and user data at rest.
*   **Implement Token-Based Authentication:** Revise `AuthService` to request and store a secure access token (JWT), preventing direct storage of user credentials.
*   **Enforce HTTPS for PHI:** Ensure `AppServerConfig` STRICTLY enforces HTTPS (TLS) connections when communicating with the OCR backend to protect PHI data in transit.

## 4. Code Quality & GUI Modularity

### Current Shortcomings
*   **UI Modularity:** While the centralized theme (`AppTheme`) is excellent, heavily nested UI code exists in multiple screen files.
*   **Linting:** The app uses baseline `flutter_lints`. It can benefit from stricter rules.

### Proposed Changes
*   **Enhance Linting Rules:** Upgrade `analysis_options.yaml` to use stricter guidelines (e.g., `very_good_analysis` or stricter flutter lints) to enforce better code structure across the team.
*   **Component Extraction:** Audit remaining screens (like `scan_screen.dart`) and extract reusable layout components.

---

## Verification Plan

### Automated Tests
*   Run `flutter analyze` ensuring 0 warnings after upgrading linting rules.
*   Write unit tests for the newly extracted State Controllers (e.g., `ProcessController`) testing logic without the UI.
*   Write a unit test for `database_service.dart` using `sqflite_common_ffi` to verify database query performance and correctness without in-memory loading.

### Manual Verification
*   **Security:** Verify that `SharedPreferences` files on Android/iOS do not expose plain text usernames/ids after the fix.
*   **Efficiency:** Use Flutter DevTools' Network profiler to confirm that `MultipartRequest` image payloads are smaller and faster than the previous Base64 JSON approach.
*   **UI/UX:** Perform a full sweep of `ProcessScreen` on a physical device to ensure the UI remains totally responsive during processing through the new abstracted State Management flow.
