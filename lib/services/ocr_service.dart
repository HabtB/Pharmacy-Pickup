import 'dart:io';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import '../models/med_item.dart';
import 'parsing_service.dart';
import 'server_discovery_service.dart';

class OCRService {
  static String _doclingServerUrl = 'http://172.20.10.7:5003'; // Fallback, will be auto-discovered
  static bool _serverDiscovered = false;
  static const int _maxRetries = 1;  // Reduced from 3 to 1 for faster processing
  static const Duration _retryDelay = Duration(milliseconds: 500);  // Reduced from 2s to 0.5s

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

    // CLIENT-SIDE BATCHING: Split large image sets into batches of 5
    // This prevents connection issues with large payloads (30MB+)
    if (images.length > 5) {
      print('📦 BATCHING: Processing ${images.length} images in batches of 5');
      List<MedItem> allMedications = [];

      // Process in batches of 5
      for (int batchNum = 0; batchNum < (images.length / 5).ceil(); batchNum++) {
        int startIdx = batchNum * 5;
        int endIdx = (startIdx + 5 < images.length) ? startIdx + 5 : images.length;
        List<XFile> batch = images.sublist(startIdx, endIdx);

        print('📦 [BATCH ${batchNum + 1}/${(images.length / 5).ceil()}] Processing images ${startIdx + 1}-${endIdx}...');

        try {
          final batchResults = await _parseImagesParallel(batch, mode);
          print('✓ [BATCH ${batchNum + 1}] Found ${batchResults.length} medications');
          allMedications.addAll(batchResults);
        } catch (e) {
          print('✗ [BATCH ${batchNum + 1}] Failed: $e');
          print('Falling back to sequential processing for this batch...');

          // Sequential fallback for failed batch
          for (int i = startIdx; i < endIdx; i++) {
            try {
              final imageBytes = await File(images[i].path).readAsBytes();
              final base64Image = base64Encode(imageBytes);
              final medications = await _parseWithRetry(base64Image, mode);
              allMedications.addAll(medications);
            } catch (seqError) {
              print('✗ [IMAGE ${i + 1}] Sequential fallback also failed: $seqError');
            }
          }
        }
      }

      print('✅ BATCHING COMPLETE: Total ${allMedications.length} medications from ${images.length} images');
      return allMedications;
    }

    // If processing multiple images (≤5), use parallel endpoint for better performance
    if (images.length > 1) {
      print('Using PARALLEL processing for ${images.length} images');
      try {
        final allMedications = await _parseImagesParallel(images, mode);
        if (allMedications.isNotEmpty) {
          print('✓ Parallel processing complete: ${allMedications.length} medications found');
          return allMedications;
        }
        print('⚠️ Parallel processing returned no medications, falling back to sequential');
      } catch (e) {
        print('✗ Parallel processing failed: $e');
        print('Falling back to sequential processing...');
      }
    }

    // Single image or fallback to sequential processing
    List<MedItem> allMedications = [];

    // Process each image
    for (int i = 0; i < images.length; i++) {
      print('\n🔄 [IMAGE ${i + 1}/${images.length}] STARTING PROCESSING...');
      
      try {
        final image = images[i];
        print('📁 [IMAGE ${i + 1}] Reading file: ${image.path}');
        final imageBytes = await File(image.path).readAsBytes();
        print('✓ [IMAGE ${i + 1}] File read: ${imageBytes.length} bytes');

        print('🔐 [IMAGE ${i + 1}] Encoding to base64...');
        final base64Image = base64Encode(imageBytes);
        print('✓ [IMAGE ${i + 1}] Base64 encoded: ${base64Image.length} characters');

        print('📡 [IMAGE ${i + 1}] Sending to server for parsing...');
        List<MedItem> medications = await _parseWithRetry(base64Image, mode);
        print('✓ [IMAGE ${i + 1}] Server responded');

        if (medications.isNotEmpty) {
          print('✅ [IMAGE ${i + 1}] SUCCESS: Found ${medications.length} medications');
          allMedications.addAll(medications);
        } else {
          print('⚠️ [IMAGE ${i + 1}] WARNING: No medications found');
        }
      } catch (e, stackTrace) {
        print('❌ [IMAGE ${i + 1}] ERROR: $e');
        print('Stack trace: $stackTrace');
      }
      
      print('✓ [IMAGE ${i + 1}] COMPLETED\n');
    }

    print('\n📊 FINAL RESULTS:');
    print('   Total images processed: ${images.length}');
    print('   Total medications found: ${allMedications.length}');
    
    if (allMedications.isNotEmpty) {
      print('✅ PROCESSING COMPLETE - Returning ${allMedications.length} medications');
      return allMedications;
    }

    // Fallback to mock data for demo if all parsing fails
    print('⚠️ All images failed, using mock data for demo');
    return _createMockMedications(mode);
  }

  /// Parse multiple images in parallel using server-side concurrency
  static Future<List<MedItem>> _parseImagesParallel(List<XFile> images, String mode) async {
    // Encode all images to base64
    final List<String> base64Images = [];

    for (int i = 0; i < images.length; i++) {
      final imageBytes = await File(images[i].path).readAsBytes();
      final base64Image = base64Encode(imageBytes);
      base64Images.add(base64Image);
      print('[Image ${i+1}/${images.length}] Encoded: ${imageBytes.length} bytes');
    }

    print('Sending ${base64Images.length} images to parallel processing endpoint...');

    final response = await http.post(
      Uri.parse('$_doclingServerUrl/parse-documents-parallel'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'images': base64Images,
        'mode': mode,
      }),
    ).timeout(Duration(minutes: 5)); // Longer timeout for multiple images

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);

      if (data['success'] == true) {
        final summary = data['summary'];
        print('✓ Parallel processing summary:');
        print('  Total images: ${summary['total_images']}');
        print('  Successful: ${summary['successful']}');
        print('  Failed: ${summary['failed']}');
        print('  Total medications: ${summary['total_medications']}');

        final List<MedItem> allMedications = [];

        // Process results from each image
        final results = data['results'] as List<dynamic>;
        for (int i = 0; i < results.length; i++) {
          final result = results[i];

          if (result['success'] == true && result['medications'] != null) {
            final medications = result['medications'] as List<dynamic>;
            print('[Image ${i+1}] Found ${medications.length} medications');

            for (var medData in medications) {
              allMedications.add(_convertMapToMedItem(medData, mode));
            }
          } else {
            print('[Image ${i+1}] ✗ Failed: ${result['error'] ?? 'Unknown error'}');
          }
        }

        return allMedications;
      }
    }

    throw Exception('Parallel processing request failed: ${response.statusCode}');
  }

  /// Parse with retry logic and multiple fallback strategies
  static Future<List<MedItem>> _parseWithRetry(String base64Image, String mode) async {
    // Use only 'enhanced' strategy since it's the most reliable
    List<String> strategies = ['enhanced'];  // Reduced from 3 strategies to 1 for speed

    // Skip health check - adds unnecessary delay when server is cached
    // The POST request itself will fail quickly if server is down
    print('Using cached server: $_doclingServerUrl');

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
          ).timeout(Duration(seconds: 60));  // Increased to 60s for large images + API processing time

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
