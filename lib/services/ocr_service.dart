import 'dart:io';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import '../models/med_item.dart';
import 'parsing_service.dart';
import 'server_discovery_service.dart';

class OCRService {
  static String _doclingServerUrl = 'http://172.20.10.9:5003'; // Fallback, will be auto-discovered
  static bool _serverDiscovered = false;
  static const int _maxRetries = 3;
  static const Duration _retryDelay = Duration(seconds: 2);

  /// Discover server on network (called automatically before first request)
  static Future<void> _discoverServer() async {
    if (_serverDiscovered) return;

    final discoveredUrl = await ServerDiscoveryService.discoverServer();
    if (discoveredUrl != null) {
      _doclingServerUrl = discoveredUrl;
      _serverDiscovered = true;
      print('✓ OCR Service using server: $_doclingServerUrl');
    } else {
      print('✗ Server discovery failed, using fallback: $_doclingServerUrl');
      _serverDiscovered = true; // Don't keep trying
    }
  }

  /// Extract text from images using Docling server
  static Future<String> extractTextFromImages(List<XFile> images) async {
    try {
      // For now, process only the first image
      if (images.isEmpty) return '';
      
      final image = images.first;
      final imageBytes = await File(image.path).readAsBytes();
      final base64Image = base64Encode(imageBytes);
      
      print('Sending image to Docling server...');
      
      final response = await http.post(
        Uri.parse('$_doclingServerUrl/parse-document'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_base64': base64Image,
          'mode': 'cart_fill'
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['raw_text'] ?? '';
      } else {
        print('Docling server error: ${response.statusCode}');
        return '';
      }
    } catch (e) {
      print('Error communicating with Docling server: $e');
      return '';
    }
  }


  /// Parse text to medications using local parsing service
  static Future<List<MedItem>> parseTextToMedications(String extractedText, String mode, {String? apiKey}) async {
    try {
      print('=== OCR SERVICE: Using local parsing service ===');
      print('Text to parse: ${extractedText.substring(0, extractedText.length > 200 ? 200 : extractedText.length)}...');

      // Use the local parsing service to parse the text
      final medications = await parseExtractedText(extractedText, mode, apiKey);

      print('=== OCR SERVICE: Local parsing found ${medications.length} medications ===');

      // Convert to MedItem objects
      return medications.map((medData) => _convertMapToMedItem(medData, mode)).toList();
    } catch (e) {
      print('Error in parseTextToMedications: $e');
      return [];
    }
  }
  
  /// Parse images directly using enhanced Docling server with retry logic
  static Future<List<MedItem>> parseImagesDirectly(List<XFile> images, String mode) async {
    if (images.isEmpty) return [];

    // Auto-discover server before first request
    await _discoverServer();

    print('=== OCR DEBUG: Processing ${images.length} images ===');

    List<MedItem> allMedications = [];

    // Process each image
    for (int i = 0; i < images.length; i++) {
      final image = images[i];
      final imageBytes = await File(image.path).readAsBytes();

      print('=== Processing image ${i + 1}/${images.length} ===');
      print('Image path: ${image.path}');
      print('Image size: ${imageBytes.length} bytes');

      final base64Image = base64Encode(imageBytes);
      print('Base64 encoded length: ${base64Image.length} characters');

      // Try enhanced parsing with retry logic
      List<MedItem> medications = await _parseWithRetry(base64Image, mode);

      if (medications.isNotEmpty) {
        print('✓ Image ${i + 1}: Found ${medications.length} medications');
        allMedications.addAll(medications);
      } else {
        print('⚠️ Image ${i + 1}: No medications found');
      }
    }

    if (allMedications.isNotEmpty) {
      print('✓ Total medications found across all images: ${allMedications.length}');
      return allMedications;
    }

    // Fallback to mock data for demo if all parsing fails
    print('⚠️ All images failed, using mock data for demo');
    return _createMockMedications(mode);
  }

  /// Parse with retry logic and multiple fallback strategies
  static Future<List<MedItem>> _parseWithRetry(String base64Image, String mode) async {
    List<String> strategies = ['enhanced', 'docling', 'regex'];

    // First check server connectivity
    print('=== NETWORK DEBUG: Testing server connectivity ===');
    print('Server URL: $_doclingServerUrl');

    try {
      final healthResponse = await http.get(
        Uri.parse('$_doclingServerUrl/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(Duration(seconds: 10));

      print('Health check status: ${healthResponse.statusCode}');
      if (healthResponse.statusCode == 200) {
        print('✓ Server is reachable and healthy');
      } else {
        print('✗ Server health check failed: ${healthResponse.statusCode}');
        print('Response: ${healthResponse.body}');
      }
    } catch (e) {
      print('✗ Server connectivity test failed: $e');
      print('This suggests network connectivity issues between app and server');
    }

    for (String strategy in strategies) {
      for (int attempt = 1; attempt <= _maxRetries; attempt++) {
        try {
          print('=== Attempting $strategy parsing (attempt $attempt/$_maxRetries) ===');
          print('POST to: $_doclingServerUrl/parse-document');

          final response = await http.post(
            Uri.parse('$_doclingServerUrl/parse-document'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'image_base64': base64Image,
              'mode': mode,
              'strategy': strategy, // Tell server which strategy to use
            }),
          ).timeout(Duration(seconds: 30));

          print('Response status: ${response.statusCode}');

          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            print('Server response: ${data['success']}');
            print('Method used: ${data['method'] ?? 'unknown'}');
            print('Raw text: "${data['raw_text'] ?? 'NO TEXT'}"');

            final medications = <MedItem>[];

            if (data['success'] == true && data['medications'] != null) {
              for (var medData in data['medications']) {
                medications.add(_convertMapToMedItem(medData, mode));
              }

              print('✓ Parsed ${medications.length} medications using $strategy');

              if (medications.isNotEmpty) {
                // Add debug info to each medication
                for (int i = 0; i < medications.length; i++) {
                  print('  ${i + 1}. ${medications[i].name} ${medications[i].dose} ${medications[i].form}');
                }
                return medications;
              }
            }

            // If we got a response but no medications, try next strategy
            print('⚠️ $strategy parsing returned no medications, trying next strategy...');
            break; // Exit retry loop for this strategy
          } else {
            print('✗ $strategy parsing failed with status ${response.statusCode}');
            if (attempt < _maxRetries) {
              print('Retrying in ${_retryDelay.inSeconds} seconds...');
              await Future.delayed(_retryDelay);
            }
          }
        } catch (e) {
          print('✗ $strategy parsing error (attempt $attempt): $e');
          if (attempt < _maxRetries) {
            print('Retrying in ${_retryDelay.inSeconds} seconds...');
            await Future.delayed(_retryDelay);
          }
        }
      }
    }

    print('✗ All parsing strategies failed');
    return [];
  }

  /// Create fallback medication entry when parsing fails completely
  static List<MedItem> _createMockMedications(String mode) {
    if (mode == 'floor_stock') {
      return [
        MedItem(
          name: 'Unable to Read Medication',
          dose: 'Check label',
          form: 'unknown',
          pickAmount: 1,
          location: 'Please verify',
          notes: 'OCR parsing failed - verify medication manually',
        ),
      ];
    } else {
      return [
        MedItem(
          name: 'Unable to Read Medication',
          dose: 'Check label',
          form: 'unknown',
          pickAmount: 1,
          patient: 'Please verify',
          sig: 'Check directions',
          calculatedQty: 1.0,
          notes: 'OCR parsing failed - verify medication manually',
        ),
      ];
    }
  }


  /// Convert parsed medication map to MedItem object
  static MedItem _convertMapToMedItem(Map<String, dynamic> data, String mode) {
    // Parse pick amount safely
    int pickAmount = 1;
    if (data['pick_amount'] != null) {
      pickAmount = data['pick_amount'] is int
          ? data['pick_amount']
          : int.tryParse(data['pick_amount'].toString()) ?? 1;
    } else if (data['quantity'] != null) {
      pickAmount = int.tryParse(data['quantity'].toString()) ?? 1;
    }

    return MedItem(
      name: data['name'] ?? '',
      dose: data['dose'] ?? data['strength'] ?? data['dosage'] ?? '',
      form: data['form'] ?? data['type'] ?? 'tablet',
      pickAmount: pickAmount,
      location: '', // Will be filled by database lookup
      notes: data['brand'] != null ? 'Brand: ${data['brand']}' : null,
      patient: data['patient'],
      floor: data['floor'],
      sig: data['sig'] ?? data['frequency'] ?? data['directions'] ?? '',
      admin: data['admin'],
      calculatedQty: (data['calculated_qty'] ?? data['quantity']?.toDouble() ?? 1.0),
    );
  }

  /// Check if Docling server is available
  static Future<bool> isDoclingServerAvailable() async {
    try {
      final response = await http.get(Uri.parse('$_doclingServerUrl/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
