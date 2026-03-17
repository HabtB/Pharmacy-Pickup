import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/med_item.dart';
import '../utils/app_logger.dart';
import 'server_discovery_service.dart';

// ─────────────────────────────────────────────────────────────────────
// Auth state: represents whether the user is logged in or not.
// This is what the UI watches to decide which screen to show.
// ─────────────────────────────────────────────────────────────────────
class AuthState {
  final bool isLoggedIn;
  final Map<String, dynamic>? user;

  const AuthState({this.isLoggedIn = false, this.user});

  AuthState copyWith({bool? isLoggedIn, Map<String, dynamic>? user}) {
    return AuthState(
      isLoggedIn: isLoggedIn ?? this.isLoggedIn,
      user: user ?? this.user,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// AuthNotifier: replaces the old singleton. Holds auth state and
// exposes login/logout/register methods. Riverpod manages the
// lifecycle — no manual singleton needed.
// ─────────────────────────────────────────────────────────────────────
class AuthNotifier extends Notifier<AuthState> {
  /// Cached server base URL, discovered on first use.
  String? _baseUrl;

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
  static const String _keyBiometricEnabled = 'biometric_enabled';
  static const String _keyBiometricUser = 'biometric_username';
  static const String _keyBiometricPass = 'biometric_password';

  final _localAuth = LocalAuthentication();

  @override
  AuthState build() {
    // Initial state: not logged in. The app calls checkAuthStatus()
    // during startup to read from secure storage and update this.
    return const AuthState();
  }

  Future<String> _getApiUrl() async {
    if (_baseUrl != null) return '$_baseUrl/api';
    final discovered = await ServerDiscoveryService.discoverServer();
    _baseUrl = discovered ?? 'http://${ServerDiscoveryService.fallbackIp}:${ServerDiscoveryService.serverPort}';
    return '$_baseUrl/api';
  }

  // ─── Check if a session exists in secure storage ───────────────────
  // Called once at app startup to restore login state.
  Future<void> checkAuthStatus() async {
    try {
      final token = await _secureStorage
          .read(key: _keyToken)
          .timeout(const Duration(seconds: 2));
      final loggedIn = token != null && token.isNotEmpty;

      if (loggedIn) {
        final user = await getCurrentUser();
        state = AuthState(isLoggedIn: true, user: user);
      } else {
        state = const AuthState(isLoggedIn: false);
      }
    } catch (e) {
      AppLogger.error('Auth check failed or timed out: $e', name: 'Auth');
      state = const AuthState(isLoggedIn: false);
    }
  }

  // ─── Login ─────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final apiUrl = await _getApiUrl();
      final response = await http.post(
        Uri.parse('$apiUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success']) {
          await _saveSession(data['user'], data['token']);
          // Update Riverpod state so the UI reacts automatically
          state = AuthState(isLoggedIn: true, user: data['user']);
          return {'success': true, 'user': data['user']};
        }
      }
      return {'success': false, 'message': 'Invalid credentials'};
    } catch (e) {
      return {'success': false, 'message': 'Unable to connect to server. Please check your connection.'};
    }
  }

  // ─── Biometric authentication ────────────────────────────────────
  /// Check if the device supports biometrics and user has enrolled.
  Future<bool> canUseBiometrics() async {
    try {
      final isAvailable = await _localAuth.canCheckBiometrics;
      final isDeviceSupported = await _localAuth.isDeviceSupported();
      return isAvailable && isDeviceSupported;
    } catch (e) {
      AppLogger.error('Biometric check failed: $e', name: 'Auth');
      return false;
    }
  }

  /// Check if biometric login is enabled (user previously opted in).
  Future<bool> isBiometricEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyBiometricEnabled) ?? false;
  }

  /// Save credentials for biometric re-login after a successful password login.
  Future<void> enableBiometric(String username, String password) async {
    await _secureStorage.write(key: _keyBiometricUser, value: username);
    await _secureStorage.write(key: _keyBiometricPass, value: password);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyBiometricEnabled, true);
  }

  /// Disable biometric login and clear stored credentials.
  Future<void> disableBiometric() async {
    await _secureStorage.delete(key: _keyBiometricUser);
    await _secureStorage.delete(key: _keyBiometricPass);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyBiometricEnabled, false);
  }

  /// Authenticate with biometrics, then use stored credentials to log in.
  Future<Map<String, dynamic>> loginWithBiometrics() async {
    try {
      final authenticated = await _localAuth.authenticate(
        localizedReason: 'Authenticate to access MedPick',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
        ),
      );

      if (!authenticated) {
        return {'success': false, 'message': 'Biometric authentication cancelled'};
      }

      final username = await _secureStorage.read(key: _keyBiometricUser);
      final password = await _secureStorage.read(key: _keyBiometricPass);

      if (username == null || password == null) {
        await disableBiometric();
        return {'success': false, 'message': 'Saved credentials not found. Please log in with password.'};
      }

      return await login(username, password);
    } catch (e) {
      AppLogger.error('Biometric login failed: $e', name: 'Auth');
      return {'success': false, 'message': 'Biometric authentication failed'};
    }
  }

  // ─── Register ──────────────────────────────────────────────────────
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
      ).timeout(const Duration(seconds: 30));

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
      return {'success': false, 'message': 'Unable to connect to server. Please check your connection.'};
    }
  }

  // ─── Logout ────────────────────────────────────────────────────────
  Future<void> logout({bool clearBiometric = false}) async {
    await _secureStorage.delete(key: _keyToken);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(keyUserId);
    await prefs.remove(keyUsername);
    await prefs.remove(keyRole);
    if (clearBiometric) {
      await disableBiometric();
    }
    // Update Riverpod state — UI will react and show login screen
    state = const AuthState(isLoggedIn: false, user: null);
  }

  // ─── Session persistence ───────────────────────────────────────────
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

  Future<Map<String, dynamic>?> getCurrentUser() async {
    final prefs = await SharedPreferences.getInstance();
    if (!prefs.containsKey(keyUserId)) return null;
    return {
      'id': prefs.getInt(keyUserId),
      'username': prefs.getString(keyUsername),
      'role': prefs.getString(keyRole),
    };
  }

  /// Check if a response indicates an expired/invalid token.
  /// If so, clear the session and update state so the UI shows login.
  bool _isTokenExpired(http.Response response) {
    if (response.statusCode == 401) {
      AppLogger.warn('Token expired or invalid — logging out', name: 'Auth');
      logout();
      return true;
    }
    return false;
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
      ).timeout(const Duration(seconds: 30));

      if (_isTokenExpired(response)) return false;
      return response.statusCode == 200;
    } catch (e) {
      AppLogger.error('Error saving session: $e', name: 'Auth');
      return false;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────
// The provider. This is what you import and use everywhere instead of
// AuthService.instance. Access the notifier via ref.read(authProvider.notifier).
// Watch the state via ref.watch(authProvider).
// ─────────────────────────────────────────────────────────────────────
final authProvider = NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);
