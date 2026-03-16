import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:async';
import '../utils/app_logger.dart';

/// Service to automatically discover the OCR server on the local network.
/// In production, set SERVER_URL in .env to skip network scanning entirely.
class ServerDiscoveryService {
  // CONFIGURABLE SETTINGS - You can edit these:
  static const int serverPort = 5003;
  static const List<String> ipRangesToScan = [
    '172.20.10',   // iPhone hotspot range
    '192.168.1',   // Common home network
    '10.0.0',      // Another common range
  ];
  static const int ipRangeStart = 1;
  static const int ipRangeEnd = 254;  // Scan entire subnet to find server anywhere
  static const Duration discoveryTimeout = Duration(milliseconds: 300); // Fast timeout per IP
  static const String healthEndpoint = '/health';

  // Fallback IP if discovery fails (updated to current WiFi network)
  static const String fallbackIp = '192.168.1.134';

  // Cache discovered server
  static String? _cachedServerUrl;

  /// Discover the server on the local network
  /// Returns the full server URL (e.g., 'http://172.20.10.7:5003') or null if not found
  ///
  /// If SERVER_URL is set in .env (and is not localhost), it is used directly
  /// without any network scanning — ideal for production deployments.
  static Future<String?> discoverServer() async {
    // Check .env for an explicit server URL (production mode)
    try {
      final envUrl = dotenv.env['SERVER_URL'];
      if (envUrl != null && envUrl.isNotEmpty && !envUrl.contains('localhost')) {
        _cachedServerUrl = envUrl;
        AppLogger.info('Using SERVER_URL from .env: $envUrl', name: 'Discovery');
        return envUrl;
      }
    } catch (_) {
      // dotenv may not be loaded (e.g. release builds without .env)
    }

    // No production URL set — fall back to local network discovery
    AppLogger.info('No production SERVER_URL set, starting network discovery', name: 'Discovery');
    AppLogger.info('Scanning IP ranges: ${ipRangesToScan.join(", ")}', name: 'Discovery');
    AppLogger.info('Port: $serverPort', name: 'Discovery');

    final startTime = DateTime.now();

    // OPTIMIZATION: Try common server IPs first before full scan
    final commonIps = [
      '192.168.1.134', // Mac on WiFi (most common)
      '172.20.10.9',   // Mac on hotspot
      '172.20.10.7',   // Alternative Mac IP on hotspot
      '192.168.1.1',   // Router (unlikely but check)
      '10.0.0.1',      // Another common router IP
    ];

    AppLogger.info('Step 1: Checking common server locations...', name: 'Discovery');
    for (String ip in commonIps) {
      final serverUrl = await _testServer(ip);
      if (serverUrl != null) {
        _cachedServerUrl = serverUrl;
        final duration = DateTime.now().difference(startTime);
        AppLogger.info('Server found at common IP: $serverUrl (took ${duration.inMilliseconds}ms)', name: 'Discovery');
        return serverUrl;
      }
    }

    AppLogger.info('Step 2: Common IPs failed, starting full subnet scan...', name: 'Discovery');

    // Try all IP ranges in parallel for speed
    final futures = <Future<String?>>[];

    for (String ipRange in ipRangesToScan) {
      for (int i = ipRangeStart; i <= ipRangeEnd; i++) {
        final ip = '$ipRange.$i';
        // Skip IPs we already checked
        if (!commonIps.contains(ip)) {
          futures.add(_testServer(ip));
        }
      }
    }

    // Wait for ALL responses
    try {
      final results = await Future.wait(futures);

      // Filter out nulls to get all valid servers
      final validServers = results.where((url) => url != null).toList();

      if (validServers.isNotEmpty) {
        AppLogger.info('Found ${validServers.length} server(s): ${validServers.join(", ")}', name: 'Discovery');

        // Use the first server found (fastest response)
        final preferredServer = validServers.first;

        _cachedServerUrl = preferredServer;
        final duration = DateTime.now().difference(startTime);
        AppLogger.info('Server discovered at: $preferredServer (took ${duration.inMilliseconds}ms)', name: 'Discovery');
        return preferredServer;
      }
    } catch (e) {
      AppLogger.error('Error during server discovery: $e', name: 'Discovery');
    }

    final duration = DateTime.now().difference(startTime);
    AppLogger.error('Server discovery failed after ${duration.inMilliseconds}ms', name: 'Discovery');
    AppLogger.info('Using fallback IP: $fallbackIp:$serverPort', name: 'Discovery');

    // Cache and return fallback
    _cachedServerUrl = 'http://$fallbackIp:$serverPort';
    return _cachedServerUrl;
  }

  /// Test if server is running at the given IP
  static Future<String?> _testServer(String ip) async {
    final url = 'http://$ip:$serverPort$healthEndpoint';

    try {
      final response = await http.get(
        Uri.parse(url),
        headers: {'Accept': 'application/json'},
      ).timeout(discoveryTimeout);

      if (response.statusCode == 200) {
        final serverUrl = 'http://$ip:$serverPort';
        AppLogger.info('Found server at $ip', name: 'Discovery');
        return serverUrl;
      }
    } catch (e) {
      // Silently fail - expected for most IPs
      // print('  ✗ No server at $ip');
    }

    return null;
  }

  /// Clear cached server URL (useful for forcing re-discovery)
  static void clearCache() {
    _cachedServerUrl = null;
    AppLogger.info('Server cache cleared - will re-discover on next request', name: 'Discovery');
  }

  /// Check if server is currently cached
  static bool get hasDiscoveredServer => _cachedServerUrl != null;

  /// Get the cached server URL (or null if not discovered yet)
  static String? get cachedServerUrl => _cachedServerUrl;
}
