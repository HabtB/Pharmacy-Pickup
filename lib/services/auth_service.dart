import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/med_item.dart';
import '../utils/app_logger.dart';
import 'server_discovery_service.dart';

/// Singleton auth service — uses the server URL from ServerDiscoveryService.
class AuthService {
  AuthService._();
  static final AuthService instance = AuthService._();

  /// Cached server base URL, discovered on first use.
  String? _baseUrl;

  Future<String> _getApiUrl() async {
    if (_baseUrl != null) return '$_baseUrl/api';
    final discovered = await ServerDiscoveryService.discoverServer();
    _baseUrl = discovered ?? 'http://${ServerDiscoveryService.fallbackIp}:${ServerDiscoveryService.serverPort}';
    return '$_baseUrl/api';
  }

  final _secureStorage = const FlutterSecureStorage(
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
  );

  static const String _keyToken = 'auth_token';
  static const String keyUserId = 'auth_user_id';
  static const String keyUsername = 'auth_username';
  static const String keyRole = 'auth_role';

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final apiUrl = await _getApiUrl();
      final response = await http.post(
        Uri.parse('$apiUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success']) {
          await _saveSession(data['user'], data['token']);
          return {'success': true, 'user': data['user']};
        }
      }
      return {'success': false, 'message': 'Invalid credentials'};
    } catch (e) {
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  Future<Map<String, dynamic>> register({
    required String username,
    required String password,
    required String confirmPassword,
    String role = 'picker',
  }) async {
    try {
      final apiUrl = await _getApiUrl();
      final response = await http.post(
        Uri.parse('$apiUrl/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
          'confirm_password': confirmPassword,
          'role': role,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return {
          'success': true,
          'message': data['message'],
          'user': data['user']
        };
      } else {
        return {
          'success': false,
          'message': data['message'] ?? 'Registration failed'
        };
      }
    } catch (e) {
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  Future<void> _saveSession(
      Map<String, dynamic> user, String? token) async {
    if (token != null) {
      await _secureStorage.write(key: _keyToken, value: token);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(keyUserId, user['id']);
    await prefs.setString(keyUsername, user['username']);
    await prefs.setString(keyRole, user['role']);
  }

  Future<String?> getToken() async {
    return await _secureStorage.read(key: _keyToken);
  }

  Future<Map<String, String>> getAuthHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<bool> isLoggedIn() async {
    try {
      final token = await _secureStorage
          .read(key: _keyToken)
          .timeout(const Duration(seconds: 2));
      return token != null && token.isNotEmpty;
    } catch (e) {
      AppLogger.error('Auth check failed or timed out: $e', name: 'Auth');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getCurrentUser() async {
    final prefs = await SharedPreferences.getInstance();
    if (!prefs.containsKey(keyUserId)) return null;
    return {
      'id': prefs.getInt(keyUserId),
      'username': prefs.getString(keyUsername),
      'role': prefs.getString(keyRole),
    };
  }

  Future<void> logout() async {
    await _secureStorage.delete(key: _keyToken);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(keyUserId);
    await prefs.remove(keyUsername);
    await prefs.remove(keyRole);
  }

  Future<bool> savePickSession(List<MedItem> items) async {
    try {
      final user = await getCurrentUser();
      if (user == null) return false;

      final apiUrl = await _getApiUrl();
      final headers = await getAuthHeaders();
      final response = await http.post(
        Uri.parse('$apiUrl/save_session'),
        headers: headers,
        body: jsonEncode({
          'user_id': user['id'],
          'items': items.map((e) => e.toMap()).toList(),
        }),
      );

      return response.statusCode == 200;
    } catch (e) {
      AppLogger.error('Error saving session: $e', name: 'Auth');
      return false;
    }
  }
}
