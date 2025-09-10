import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:camera/camera.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image/image.dart' as img_lib;
import '../models/med_item.dart';
import 'parsing_service.dart';
import '../utils/string_extensions.dart';

class OCRService {
  static final TextRecognizer _textRecognizer = TextRecognizer(
    script: TextRecognitionScript.latin,
  );
  
  // Enhanced text recognizer for better pharmaceutical text detection
  static final TextRecognizer _enhancedTextRecognizer = TextRecognizer(
    script: TextRecognitionScript.latin,
  );

  /// Extract text from a list of scanned images using enhanced ML Kit OCR
  static Future<String> extractTextFromImages(List<XFile> images) async {
    List<String> allText = [];
    
    for (XFile image in images) {
      try {
        print('=== OCR DEBUG: Processing image ${image.path} ===');
        print('Image exists: ${await File(image.path).exists()}');
        print('Image size: ${await File(image.path).length()} bytes');
        
        // Use simple ML Kit OCR with high resolution settings
        String? mlKitText = await _tryMLKitOCR(image.path);
        
        if (mlKitText != null && mlKitText.isNotEmpty) {
          allText.add(mlKitText);
          print('ML Kit successfully extracted text: ${mlKitText.length} characters');
        } else {
          print('ERROR: ML Kit returned null or empty text from image');
        }
      } catch (e, stackTrace) {
        print('ERROR processing image ${image.path}: $e');
        print('Stack trace: $stackTrace');
      }
    }
    
    String finalText = allText.join('\n\n--- PAGE BREAK ---\n\n');
    
    // Log final extraction summary
    if (finalText.isNotEmpty) {
      print('OCR complete: Extracted ${allText.length} total lines from ${images.length} image(s)');
      print('=== RAW EXTRACTED TEXT ===');
      print(finalText);
      print('=== END RAW TEXT ===');
      print('=== TEXT LENGTH: ${finalText.length} characters ===');
    } else {
      print('OCR warning: No text extracted from ${images.length} image(s)');
    }
    
    return finalText;
  }

  /// Simple ML Kit OCR extraction (original working version)
  static Future<String?> _tryMLKitOCR(String imagePath) async {
    try {
      print('Creating InputImage from path: $imagePath');
      final inputImage = InputImage.fromFilePath(imagePath);
      
      print('Processing image with text recognizer...');
      final RecognizedText recognizedText = await _textRecognizer.processImage(inputImage);
      
      print('ML Kit raw blocks: ${recognizedText.blocks.length}');
      if (recognizedText.blocks.isNotEmpty) {
        print('First block text: ${recognizedText.blocks.first.text}');
        print('Total text length: ${recognizedText.text.length}');
        return recognizedText.text;
      } else {
        print('ERROR: ML Kit found 0 text blocks in image');
        return null;
      }
    } catch (e, stackTrace) {
      print('ERROR in ML Kit OCR: $e');
      print('Stack trace: $stackTrace');
      return null;
    }
  }

  /// Parse extracted text into medication items with intelligent parsing and LLM enhancement
  static Future<List<MedItem>> parseTextToMedications(String extractedText, String mode, {String? apiKey}) async {
    try {
      print('=== PARSING START: Mode $mode, Text length ${extractedText.length} ===');
      print('API Key provided: ${apiKey != null && apiKey.isNotEmpty}');
      print('First 200 chars of text: ${extractedText.substring(0, extractedText.length > 200 ? 200 : extractedText.length)}');
      
      // Use parsing service's async function with proper await
      List<Map<String, dynamic>> parsed = await parseExtractedText(extractedText, mode, apiKey);
      
      print('=== PARSING RESULT: ${parsed.length} items parsed ===');
      if (parsed.isEmpty) {
        print('WARNING: No medications parsed from text');
      }
      
      List<MedItem> medications = [];
      for (var data in parsed) {
        if (data['name'] != null && data['name'].toString().isNotEmpty) {
          var med = _convertMapToMedItem(data, mode);
          medications.add(med);
          print('Added medication: ${med.name} - ${med.dose} - ${med.form}');
        }
      }
      
      print('=== PARSING END: ${medications.length} MedItems created ===');
      return medications;
    } catch (e, stackTrace) {
      print('ERROR in parseTextToMedications: $e');
      print('Stack trace: $stackTrace');
      return [];
    }
  }

  /// Parse extracted text based on mode (floor_stock vs cart_fill) - LOCAL HELPER ONLY
  static List<Map<String, dynamic>> _parseExtractedTextLocal(String text, String mode) {
    print('=== LOCAL PARSING MODE: $mode ===');
    
    if (mode == 'floor_stock') {
      return _parseFloorStockText(text);
    } else {
      return _parseCartFillText(text);
    }
  }
  
  /// Parse floor stock pick lists (tabular format)
  static List<Map<String, dynamic>> _parseFloorStockText(String text) {
    print('=== FLOOR STOCK PARSING ===');
    List<Map<String, dynamic>> meds = [];
    var lines = text.split('\n').where((line) => line.trim().isNotEmpty).toList();
    
    print('Total lines: ${lines.length}');
    
    // Skip header line (assume line 0 is header, data starts at line 1)
    for (var i = 1; i < lines.length; i++) {
      var line = lines[i];
      print('Processing floor stock line: $line');
      
      // Split by multiple spaces (column separator in tabular data)
      var columns = line.split(RegExp(r'\s{2,}'));
      print('Columns found: ${columns.length} - $columns');
      
      if (columns.length >= 4) { // Min: Description, Pick Amount, Current, Max
        var description = columns[0].trim().toLowerCase();
        
        // Regex for floor stock format: name (BRAND) dose form
        RegExp floorStockRegex = RegExp(r'(\w+)\s*\((.*?)\)\s*([\d.]+\s*.*?)\s+(tablet|capsule|oral susp|cup|inhalation)', caseSensitive: false);
        var match = floorStockRegex.firstMatch(description);
        
        if (match != null) {
          var pickAmount = int.tryParse(columns[1].trim()) ?? 0;
          var currentAmount = int.tryParse(columns[2].trim()) ?? 0;
          var maxAmount = int.tryParse(columns[3].trim()) ?? 0;
          
          var medData = {
            'name': match.group(1)?.capitalize(),
            'brand': match.group(2),
            'dose': match.group(3)?.trim(),
            'form': match.group(4),
            'pick_amount': pickAmount,
            'current_amount': currentAmount,
            'max': maxAmount,
          };
          
          print('Floor stock medication parsed: $medData');
          meds.add(medData);
        } else {
          print('Floor stock regex failed for: $description');
        }
      } else {
        print('Insufficient columns for floor stock parsing');
      }
    }
    
    print('=== FLOOR STOCK PARSING COMPLETE: ${meds.length} medications ===');
    return meds;
  }
  
  /// Parse cart-fill individual medication labels
  static List<Map<String, dynamic>> _parseCartFillText(String text) {
    print('=== CART-FILL PARSING ===');
    List<Map<String, dynamic>> meds = [];
    var lines = text.split('\n').where((line) => line.trim().isNotEmpty).toList();
    
    for (var line in lines) {
      var medData = _parseMedicationLine(line);
      if (medData.isNotEmpty && medData['name'] != null) {
        meds.add(medData);
      }
    }
    
    print('=== CART-FILL PARSING COMPLETE: ${meds.length} medications ===');
    return meds;
  }

  /// Parse a single line of text into a medication map (for cart-fill mode)
  static Map<String, dynamic> _parseMedicationLine(String line) {
    print('Trying regex on: $line');
    
    // Pattern 1: Brand name in parentheses before strength
    RegExp brandBeforeStrengthRegex = RegExp(
      r'([A-Za-z]+)\s*\(([^)]+)\)\s+(\d+\s*(?:mg|mcg|unit))\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)',
      caseSensitive: false
    );
    
    var brandMatch = brandBeforeStrengthRegex.firstMatch(line);
    if (brandMatch != null) {
      return {
        'name': brandMatch.group(1)?.trim(),
        'brand': brandMatch.group(2)?.trim(),
        'strength': brandMatch.group(3)?.trim(),
        'type': brandMatch.group(4)?.trim() ?? 'tablet',
        'dose': null,
        'patient': null,
        'floor': null,
      };
    }
    
    // Pattern 1b: Brand name in parentheses with form before strength
    RegExp brandFormStrengthRegex = RegExp(
      r'([A-Za-z]+)\s*\(([^)]+)\)\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)\s+(\d+\s*(?:mg|mcg|unit))',
      caseSensitive: false
    );
    
    var brandFormMatch = brandFormStrengthRegex.firstMatch(line);
    if (brandFormMatch != null) {
      return {
        'name': brandFormMatch.group(1)?.trim(),
        'brand': brandFormMatch.group(2)?.trim(),
        'type': brandFormMatch.group(3)?.trim() ?? 'tablet',
        'strength': brandFormMatch.group(4)?.trim(),
        'dose': null,
        'patient': null,
        'floor': null,
      };
    }
    
    // Pattern 2: Simple medication format (name strength form)
    RegExp simpleRegex = RegExp(
      r'([A-Za-z\s]+?)\s+(\d+\s*(?:mg|mcg|unit))\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)',
      caseSensitive: false
    );
    
    var simpleMatch = simpleRegex.firstMatch(line);
    if (simpleMatch != null) {
      return {
        'name': simpleMatch.group(1)?.trim(),
        'strength': simpleMatch.group(2)?.trim(),
        'type': simpleMatch.group(3)?.trim() ?? 'tablet',
        'brand': null,
        'dose': null,
        'patient': null,
        'floor': null,
      };
    }
    
    // Pattern 3: Name form strength format
    RegExp nameFormStrengthRegex = RegExp(
      r'([A-Za-z\s]+?)\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)\s+(\d+\s*(?:mg|mcg|unit))',
      caseSensitive: false
    );
    
    var nameFormMatch = nameFormStrengthRegex.firstMatch(line);
    if (nameFormMatch != null) {
      return {
        'name': nameFormMatch.group(1)?.trim(),
        'type': nameFormMatch.group(2)?.trim() ?? 'tablet',
        'strength': nameFormMatch.group(3)?.trim(),
        'brand': null,
        'dose': null,
        'patient': null,
        'floor': null,
      };
    }
    
    return {};
  }

  /// Convert parsed medication map to MedItem object
  static MedItem _convertMapToMedItem(Map<String, dynamic> data, String mode) {
    return MedItem(
      name: data['name'] ?? '',
      dose: data['dose'] ?? data['strength'] ?? '',
      form: data['form'] ?? data['type'] ?? 'tablet',
      pickAmount: data['pick_amount'] ?? 1,
      location: '', // Will be filled by database lookup
      notes: data['brand'] != null ? 'Brand: ${data['brand']}' : null,
      patient: data['patient'],
      floor: data['floor'],
      sig: data['dose'] ?? data['sig'],
      calculatedQty: (data['calculated_qty'] ?? 1.0).toDouble(),
    );
  }

  /// Dispose of text recognizer resources
  static void dispose() {
    _textRecognizer.close();
  }
}
