import 'dart:developer' as developer;

/// Centralized logger for the Pharmacy Pickup App.
///
/// Uses `dart:developer` log() which:
/// - Shows in DevTools and debug console
/// - Is stripped in release builds
/// - Supports named log channels for filtering
class AppLogger {
  AppLogger._();

  /// Informational messages (level 0).
  static void info(String message, {String name = 'App'}) {
    developer.log(message, name: name);
  }

  /// Warning messages (level 500).
  static void warn(String message, {String name = 'App'}) {
    developer.log(message, name: name, level: 500);
  }

  /// Error messages (level 1000). Optionally attach the error object.
  static void error(String message, {String name = 'App', Object? error}) {
    developer.log(message, name: name, level: 1000, error: error);
  }
}
