import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/med_item.dart';
import '../utils/app_logger.dart';

class StorageService {
  static const String _sessionKey = 'active_picking_session_v1';
  static const String _sessionTimestampKey = 'session_timestamp';

  /// Save the current list of medications to persistent storage
  static Future<void> saveSession(List<MedItem> medications) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Convert list to JSON string
      final List<Map<String, dynamic>> jsonList = medications
          .map((med) => med.toMap())
          .toList();
      final String jsonString = json.encode(jsonList);
      
      await prefs.setString(_sessionKey, jsonString);
      await prefs.setString(_sessionTimestampKey, DateTime.now().toIso8601String());
      
      AppLogger.info('Session saved with ${medications.length} items', name: 'Storage');
    } catch (e) {
      AppLogger.error('Failed to save session: $e', name: 'Storage');
    }
  }

  /// Load a saved session if it exists
  static Future<List<MedItem>?> loadSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      if (!prefs.containsKey(_sessionKey)) {
        return null;
      }

      final String? jsonString = prefs.getString(_sessionKey);
      if (jsonString == null || jsonString.isEmpty) {
        return null;
      }

      final List<dynamic> decodedList = json.decode(jsonString);
      final List<MedItem> medications = decodedList
          .map((item) => MedItem.fromMap(item as Map<String, dynamic>))
          .toList();

      AppLogger.info('Session loaded with ${medications.length} items', name: 'Storage');
      return medications;
    } catch (e) {
      AppLogger.error('Failed to load session: $e', name: 'Storage');
      return null;
    }
  }

  /// Check if a saved session exists
  static Future<bool> hasSavedSession() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey(_sessionKey);
  }

  /// Get the timestamp of the saved session
  static Future<DateTime?> getSessionTimestamp() async {
    final prefs = await SharedPreferences.getInstance();
    final String? ts = prefs.getString(_sessionTimestampKey);
    if (ts != null) {
      return DateTime.tryParse(ts);
    }
    return null;
  }

  /// Clear the saved session (e.g., when picking is genuinely completed)
  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
    await prefs.remove(_sessionTimestampKey);
    AppLogger.info('Session cleared', name: 'Storage');
  }
}
