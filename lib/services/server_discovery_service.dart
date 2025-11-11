import 'package:http/http.dart' as http;
import 'dart:async';

/// Service to automatically discover the OCR server on the local network
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
  static Future<String?> discoverServer() async {
    // Always re-discover to handle network changes (cache disabled for reliability)
    // User can manually cache if needed
    print('Starting fresh server discovery (cache disabled)');

    print('=== SERVER DISCOVERY: Starting network scan ===');
    print('Scanning IP ranges: ${ipRangesToScan.join(", ")}');
    print('Port: $serverPort');

    final startTime = DateTime.now();

    // OPTIMIZATION: Try common server IPs first before full scan
    final commonIps = [
      '192.168.1.134', // Mac on WiFi (most common)
      '172.20.10.9',   // Mac on hotspot
      '172.20.10.7',   // Alternative Mac IP on hotspot
      '192.168.1.1',   // Router (unlikely but check)
      '10.0.0.1',      // Another common router IP
    ];

    print('Step 1: Checking common server locations...');
    for (String ip in commonIps) {
      final serverUrl = await _testServer(ip);
      if (serverUrl != null) {
        _cachedServerUrl = serverUrl;
        final duration = DateTime.now().difference(startTime);
        print('✓ Server found at common IP: $serverUrl (took ${duration.inMilliseconds}ms)');
        return serverUrl;
      }
    }

    print('Step 2: Common IPs failed, starting full subnet scan...');

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
        print('Found ${validServers.length} server(s): ${validServers.join(", ")}');

        // Use the first server found (fastest response)
        final preferredServer = validServers.first;

        _cachedServerUrl = preferredServer;
        final duration = DateTime.now().difference(startTime);
        print('✓ Server discovered at: $preferredServer (took ${duration.inMilliseconds}ms)');
        return preferredServer;
      }
    } catch (e) {
      print('Error during server discovery: $e');
    }

    final duration = DateTime.now().difference(startTime);
    print('✗ Server discovery failed after ${duration.inMilliseconds}ms');
    print('Using fallback IP: $fallbackIp:$serverPort');

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
        print('  ✓ Found server at $ip');
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
    print('Server cache cleared - will re-discover on next request');
  }

  /// Check if server is currently cached
  static bool get hasDiscoveredServer => _cachedServerUrl != null;

  /// Get the cached server URL (or null if not discovered yet)
  static String? get cachedServerUrl => _cachedServerUrl;
}
