import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:async';
import '../utils/app_logger.dart';

/// Service to automatically discover the OCR server on the local network.
/// Works across WiFi and hotspot networks by scanning common IP ranges.
/// For fixed production deployments, set SERVER_URL in .env.
class ServerDiscoveryService {
  static const int serverPort = 5003;
  static const List<String> ipRangesToScan = [
    '172.20.10',   // iPhone hotspot range
    '192.168.1',   // Common home network
    '192.168.0',   // Another common home range
    '10.0.0',      // Corporate/VPN range
  ];
  static const int ipRangeStart = 1;
  static const int ipRangeEnd = 254;
  static const Duration discoveryTimeout = Duration(milliseconds: 500);
  static const String healthEndpoint = '/health';

  static const String fallbackIp = '192.168.1.134';

  static String? _cachedServerUrl;
  static DateTime? _cacheTime;
  // Re-discover if cache is older than 5 minutes (handles network switches)
  static const Duration _cacheTtl = Duration(minutes: 5);

  /// Discover the server on the local network.
  /// Validates cached server is still reachable before reusing.
  static Future<String?> discoverServer() async {
    // Use cache if fresh AND still reachable
    if (_cachedServerUrl != null && _cacheTime != null) {
      final age = DateTime.now().difference(_cacheTime!);
      if (age < _cacheTtl) {
        final stillAlive = await _testServer(_extractIp(_cachedServerUrl!));
        if (stillAlive != null) {
          return _cachedServerUrl;
        }
        AppLogger.info('Cached server unreachable, re-discovering...', name: 'Discovery');
      }
      _cachedServerUrl = null;
      _cacheTime = null;
    }

    // Check .env for an explicit server URL (production mode)
    try {
      final envUrl = dotenv.env['SERVER_URL'];
      if (envUrl != null && envUrl.isNotEmpty && !envUrl.contains('localhost')) {
        // Verify .env URL is reachable before trusting it
        final envIp = _extractIp(envUrl);
        final reachable = await _testServer(envIp);
        if (reachable != null) {
          _cachedServerUrl = envUrl;
          _cacheTime = DateTime.now();
          AppLogger.info('Using SERVER_URL from .env: $envUrl', name: 'Discovery');
          return envUrl;
        }
        AppLogger.info('.env SERVER_URL unreachable, falling back to discovery', name: 'Discovery');
      }
    } catch (_) {}

    // Network discovery
    AppLogger.info('Starting network discovery on port $serverPort', name: 'Discovery');
    final startTime = DateTime.now();

    // Step 1: Try common server IPs first (fast path)
    final commonIps = [
      '192.168.1.134', // Mac on WiFi
      '172.20.10.9',   // Mac on hotspot
      '172.20.10.7',   // Alternative hotspot IP
      '192.168.0.1',   // Some home routers
      '10.0.0.1',      // Corporate range
    ];

    for (String ip in commonIps) {
      final serverUrl = await _testServer(ip);
      if (serverUrl != null) {
        _cachedServerUrl = serverUrl;
        _cacheTime = DateTime.now();
        final duration = DateTime.now().difference(startTime);
        AppLogger.info('Server found at common IP: $serverUrl (${duration.inMilliseconds}ms)', name: 'Discovery');
        return serverUrl;
      }
    }

    // Step 2: Full subnet scan in parallel
    AppLogger.info('Common IPs failed, scanning subnets...', name: 'Discovery');
    final futures = <Future<String?>>[];

    for (String ipRange in ipRangesToScan) {
      for (int i = ipRangeStart; i <= ipRangeEnd; i++) {
        final ip = '$ipRange.$i';
        if (!commonIps.contains(ip)) {
          futures.add(_testServer(ip));
        }
      }
    }

    try {
      final results = await Future.wait(futures).timeout(
        const Duration(seconds: 15),
        onTimeout: () => futures.map((_) => null as String?).toList(),
      );

      final validServers = results.where((url) => url != null).toList();

      if (validServers.isNotEmpty) {
        _cachedServerUrl = validServers.first;
        _cacheTime = DateTime.now();
        final duration = DateTime.now().difference(startTime);
        AppLogger.info('Server discovered: $_cachedServerUrl (${duration.inMilliseconds}ms)', name: 'Discovery');
        return _cachedServerUrl;
      }
    } catch (e) {
      AppLogger.error('Discovery error: $e', name: 'Discovery');
    }

    final duration = DateTime.now().difference(startTime);
    AppLogger.error('Discovery failed after ${duration.inMilliseconds}ms, using fallback', name: 'Discovery');
    _cachedServerUrl = 'http://$fallbackIp:$serverPort';
    _cacheTime = DateTime.now();
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
        return 'http://$ip:$serverPort';
      }
    } catch (_) {}
    return null;
  }

  /// Extract IP from a server URL like 'http://192.168.1.134:5003'
  static String _extractIp(String url) {
    final uri = Uri.parse(url);
    return uri.host;
  }

  /// Clear cached server URL (forces re-discovery on next request)
  static void clearCache() {
    _cachedServerUrl = null;
    _cacheTime = null;
    AppLogger.info('Server cache cleared', name: 'Discovery');
  }

  static bool get hasDiscoveredServer => _cachedServerUrl != null;
  static String? get cachedServerUrl => _cachedServerUrl;
}
