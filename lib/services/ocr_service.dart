import 'dart:io';
import 'dart:async';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../models/med_item.dart';
import 'parsing_service.dart';
import 'processing_controller.dart';
import 'server_discovery_service.dart';
import '../utils/app_logger.dart';

class OCRService {
  static String _doclingServerUrl = 'http://192.168.1.134:5003';
  static bool _serverDiscovered = false;
  static const int _maxRetries = 1;
  static const Duration _retryDelay = Duration(milliseconds: 500);

  /// Discover server on network (called automatically before first request)
  /// Delegates entirely to ServerDiscoveryService which handles .env, caching, and network scanning.
  static Future<void> _discoverServer() async {
    // Always let discovery service decide (it handles caching and network switches)
    final discoveredUrl = await ServerDiscoveryService.discoverServer();
    if (discoveredUrl != null) {
      _doclingServerUrl = discoveredUrl;
      _serverDiscovered = true;
      AppLogger.info('OCR Service using server: $_doclingServerUrl', name: 'OCR');
    } else {
      AppLogger.error('Server discovery failed, using fallback: $_doclingServerUrl', name: 'OCR');
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
      
      AppLogger.info('Sending image to Docling server...', name: 'OCR');
      
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
        AppLogger.error('Docling server error: ${response.statusCode}', name: 'OCR');
        return '';
      }
    } catch (e) {
      AppLogger.error('Error communicating with Docling server: $e', name: 'OCR');
      return '';
    }
  }


  /// Parse text to medications using local parsing service
  static Future<List<MedItem>> parseTextToMedications(String extractedText, String mode, {String? apiKey}) async {
    try {
      AppLogger.info('=== OCR SERVICE: Using local parsing service ===', name: 'OCR');
      AppLogger.info('Text to parse: ${extractedText.substring(0, extractedText.length > 200 ? 200 : extractedText.length)}...', name: 'OCR');

      // Use the local parsing service to parse the text
      final medications = await parseExtractedText(extractedText, mode, apiKey);

      AppLogger.info('=== OCR SERVICE: Local parsing found ${medications.length} medications ===', name: 'OCR');

      // Convert to MedItem objects
      return medications.map((medData) => _convertMapToMedItem(medData, mode)).toList();
    } catch (e) {
      AppLogger.error('Error in parseTextToMedications: $e', name: 'OCR');
      return [];
    }
  }
  
  /// Parse images directly using enhanced Docling server with retry logic
  /// Helper to wait while paused / check if stopped
  static Future<bool> _checkController(ProcessingController? controller) async {
    if (controller == null) return false;
    if (controller.isStopped) return true;
    while (controller.isPaused) {
      await Future.delayed(const Duration(milliseconds: 300));
      if (controller.isStopped) return true;
    }
    return false;
  }

  static Future<List<MedItem>> parseImagesDirectly(List<XFile> images, String mode, {ProcessingController? controller}) async {
    if (images.isEmpty) return [];

    // Auto-discover server before first request
    await _discoverServer();

    AppLogger.info('Processing ${images.length} images', name: 'OCR');

    // CLIENT-SIDE BATCHING: Split large image sets into batches of 5
    if (images.length > 5) {
      AppLogger.info('BATCHING: Processing ${images.length} images in batches of 3', name: 'OCR');
      List<MedItem> allMedications = [];

      const int batchSize = 3;

      for (int batchNum = 0; batchNum < (images.length / batchSize).ceil(); batchNum++) {
        if (await _checkController(controller)) {
          AppLogger.info('Processing stopped by user after ${allMedications.length} medications', name: 'OCR');
          return allMedications;
        }

        int startIdx = batchNum * batchSize;
        int endIdx = (startIdx + batchSize < images.length) ? startIdx + batchSize : images.length;
        List<XFile> batch = images.sublist(startIdx, endIdx);

        AppLogger.info('[BATCH ${batchNum + 1}/${(images.length / batchSize).ceil()}] Processing images ${startIdx + 1}-${endIdx}...', name: 'OCR');

        try {
          final batchResults = await _parseImagesParallel(batch, mode).timeout(
            Duration(minutes: 4),
            onTimeout: () {
              AppLogger.error('[BATCH ${batchNum + 1}] TIMEOUT after 4 minutes', name: 'OCR');
              throw TimeoutException('Batch processing timeout');
            },
          );
          AppLogger.info('[BATCH ${batchNum + 1}] Found ${batchResults.length} medications', name: 'OCR');
          allMedications.addAll(batchResults);

          if (batchNum < (images.length / batchSize).ceil() - 1) {
            await Future.delayed(Duration(seconds: 2));
          }
        } catch (e) {
          AppLogger.error('[BATCH ${batchNum + 1}] Failed: $e', name: 'OCR');
          AppLogger.info('Falling back to sequential processing for this batch...', name: 'OCR');

          for (int i = startIdx; i < endIdx; i++) {
            if (await _checkController(controller)) {
              return allMedications;
            }
            try {
              final imageBytes = await File(images[i].path).readAsBytes();
              final base64Image = base64Encode(imageBytes);
              final medications = await _parseWithRetry(base64Image, mode);
              allMedications.addAll(medications);
            } catch (seqError) {
              AppLogger.error('[IMAGE ${i + 1}] Sequential fallback also failed: $seqError', name: 'OCR');
            }
          }
        }
      }

      AppLogger.info('BATCHING COMPLETE: Total ${allMedications.length} medications from ${images.length} images', name: 'OCR');
      return allMedications;
    }

    // If processing multiple images (≤5), use parallel endpoint for better performance
    if (images.length > 1) {
      AppLogger.info('Using PARALLEL processing for ${images.length} images', name: 'OCR');
      try {
        final allMedications = await _parseImagesParallel(images, mode);
        if (allMedications.isNotEmpty) {
          AppLogger.info('Parallel processing complete: ${allMedications.length} medications found', name: 'OCR');
          return allMedications;
        }
        AppLogger.error('Parallel processing returned no medications, falling back to sequential', name: 'OCR');
      } catch (e) {
        AppLogger.error('Parallel processing failed: $e', name: 'OCR');
        AppLogger.info('Falling back to sequential processing...', name: 'OCR');
      }
    }

    // Single image or fallback to sequential processing
    List<MedItem> allMedications = [];

    for (int i = 0; i < images.length; i++) {
      if (await _checkController(controller)) {
        AppLogger.info('Processing stopped by user after ${allMedications.length} medications', name: 'OCR');
        return allMedications;
      }

      AppLogger.info('[IMAGE ${i + 1}/${images.length}] Processing...', name: 'OCR');

      try {
        final imageBytes = await File(images[i].path).readAsBytes();
        final base64Image = base64Encode(imageBytes);
        List<MedItem> medications = await _parseWithRetry(base64Image, mode);

        if (medications.isNotEmpty) {
          AppLogger.info('[IMAGE ${i + 1}] Found ${medications.length} medications', name: 'OCR');
          allMedications.addAll(medications);
        } else {
          AppLogger.error('[IMAGE ${i + 1}] No medications found', name: 'OCR');
        }
      } catch (e) {
        AppLogger.error('[IMAGE ${i + 1}] ERROR: $e', name: 'OCR');
      }
    }

    AppLogger.info('Total: ${allMedications.length} medications from ${images.length} images', name: 'OCR');
    
    if (allMedications.isNotEmpty) {
      AppLogger.info('PROCESSING COMPLETE - Returning ${allMedications.length} medications', name: 'OCR');
      return allMedications;
    }

    // All parsing failed — return empty list so the UI can show an error
    AppLogger.error('All images failed — no medications found', name: 'OCR');
    return [];
  }

  /// Parse multiple images in parallel using server-side concurrency
  /// NOTE: Only call this with 5 or fewer images to prevent memory freeze
  static Future<List<MedItem>> _parseImagesParallel(List<XFile> images, String mode) async {
    // Encode images to base64 one at a time (max 5 images per batch)
    final List<String> base64Images = [];

    for (int i = 0; i < images.length; i++) {
      AppLogger.info('[Image ${i+1}/${images.length}] Reading file...', name: 'OCR');
      final imageBytes = await File(images[i].path).readAsBytes();
      AppLogger.info('[Image ${i+1}/${images.length}] Encoding to base64 (${imageBytes.length} bytes)...', name: 'OCR');
      final base64Image = base64Encode(imageBytes);
      base64Images.add(base64Image);
      AppLogger.info('[Image ${i+1}/${images.length}] Encoded successfully', name: 'OCR');
    }

    AppLogger.info('Sending ${base64Images.length} images to parallel processing endpoint...', name: 'OCR');

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
        AppLogger.info('Parallel processing summary:', name: 'OCR');
        AppLogger.info('  Total images: ${summary['total_images']}', name: 'OCR');
        AppLogger.info('  Successful: ${summary['successful']}', name: 'OCR');
        AppLogger.info('  Failed: ${summary['failed']}', name: 'OCR');
        AppLogger.info('  Total medications: ${summary['total_medications']}', name: 'OCR');

        final List<MedItem> allMedications = [];

        // Process results from each image
        final results = data['results'] as List<dynamic>;
        for (int i = 0; i < results.length; i++) {
          final result = results[i];

          if (result['success'] == true && result['medications'] != null) {
            final medications = result['medications'] as List<dynamic>;
            AppLogger.info('[Image ${i+1}] Found ${medications.length} medications', name: 'OCR');

            for (var medData in medications) {
              allMedications.add(_convertMapToMedItem(medData, mode));
            }
          } else {
            AppLogger.error('[Image ${i+1}] Failed: ${result['error'] ?? 'Unknown error'}', name: 'OCR');
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
    AppLogger.info('Using cached server: $_doclingServerUrl', name: 'OCR');

    for (String strategy in strategies) {
      for (int attempt = 1; attempt <= _maxRetries; attempt++) {
        try {
          AppLogger.info('=== Attempting $strategy parsing (attempt $attempt/$_maxRetries) ===', name: 'OCR');
          AppLogger.info('POST to: $_doclingServerUrl/parse-document', name: 'OCR');

          final response = await http.post(
            Uri.parse('$_doclingServerUrl/parse-document'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'image_base64': base64Image,
              'mode': mode,
              'strategy': strategy, // Tell server which strategy to use
            }),
          ).timeout(Duration(seconds: 60));  // Increased to 60s for large images + API processing time

          AppLogger.info('Response status: ${response.statusCode}', name: 'OCR');

          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            AppLogger.info('Server response: ${data['success']}', name: 'OCR');
            AppLogger.info('Method used: ${data['method'] ?? 'unknown'}', name: 'OCR');
            AppLogger.info('Raw text: "${data['raw_text'] ?? 'NO TEXT'}"', name: 'OCR');

            final medications = <MedItem>[];

            if (data['success'] == true && data['medications'] != null) {
              for (var medData in data['medications']) {
                medications.add(_convertMapToMedItem(medData, mode));
              }

              AppLogger.info('Parsed ${medications.length} medications using $strategy', name: 'OCR');

              if (medications.isNotEmpty) {
                // Add debug info to each medication
                for (int i = 0; i < medications.length; i++) {
                  AppLogger.info('  ${i + 1}. ${medications[i].name} ${medications[i].dose} ${medications[i].form}', name: 'OCR');
                }
                return medications;
              }
            }

            // If we got a response but no medications, try next strategy
            AppLogger.error('$strategy parsing returned no medications, trying next strategy...', name: 'OCR');
            break; // Exit retry loop for this strategy
          } else {
            AppLogger.error('$strategy parsing failed with status ${response.statusCode}', name: 'OCR');
            if (attempt < _maxRetries) {
              AppLogger.info('Retrying in ${_retryDelay.inSeconds} seconds...', name: 'OCR');
              await Future.delayed(_retryDelay);
            }
          }
        } catch (e) {
          AppLogger.error('$strategy parsing error (attempt $attempt): $e', name: 'OCR');
          if (attempt < _maxRetries) {
            AppLogger.info('Retrying in ${_retryDelay.inSeconds} seconds...', name: 'OCR');
            await Future.delayed(_retryDelay);
          }
        }
      }
    }

    AppLogger.error('All parsing strategies failed', name: 'OCR');
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
      pickLocation: data['pick_location'],
      pickLocationDesc: data['pick_location_desc'],
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
