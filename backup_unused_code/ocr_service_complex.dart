import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:camera/camera.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image/image.dart' as img_lib;
import '../models/med_item.dart';
import 'parsing_service.dart';
import 'image_enhancement_service.dart';
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
        
        // Use simple ML Kit OCR with high resolution settings
        String? mlKitText = await _tryMLKitOCR(image.path);
        
        if (mlKitText != null && mlKitText.isNotEmpty) {
          allText.add(mlKitText);
          print('ML Kit successfully extracted text');
        } else {
          print('ML Kit failed to extract text from image');
        }
      } catch (e) {
        print('Error processing image ${image.path}: $e');
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

  /// Enhanced OCR processing using image enhancement and ML Kit
  static Future<String?> _processOcrWithRawPixels(String imagePath) async {
    try {
      print('=== ENHANCED OCR: Processing image $imagePath ===');
      
      // Try image enhancement first
      String enhancedPath = await ImageEnhancementService.enhanceImageForOCR(imagePath);
      print('=== ENHANCED OCR: Using enhanced image: $enhancedPath ===');
      
      // Use ML Kit on enhanced image
      final inputImage = InputImage.fromFilePath(enhancedPath);
      final RecognizedText recognizedText = await _enhancedTextRecognizer.processImage(inputImage);
      
      print('=== ENHANCED OCR: Blocks found: ${recognizedText.blocks.length} ===');
      
      if (recognizedText.blocks.isNotEmpty && recognizedText.text.trim().isNotEmpty) {
        print('=== ENHANCED OCR: Success! Text: ${recognizedText.text} ===');
        return recognizedText.text;
      } else {
        print('=== ENHANCED OCR: No meaningful text found ===');
        return null;
      }
    } catch (e) {
      print('=== ENHANCED OCR ERROR: $e ===');
      return null;
    }
  }

  /// Legacy raw pixel processing (backup method)
  static Future<String?> _processOcrWithRawPixelsLegacy(String imagePath) async {
    try {
      print('=== RAW PIXEL OCR: Processing image $imagePath ===');
      
      // Read and decode image to raw pixels
      File imageFile = File(imagePath);
      Uint8List bytes = await imageFile.readAsBytes();
      print('=== RAW PIXEL OCR: Read ${bytes.length} bytes ===');
      
      img_lib.Image? image = img_lib.decodeImage(bytes);
      
      if (image == null) {
        print('=== RAW PIXEL OCR: Failed to decode image ===');
        return null;
      }
      
      int width = image.width;
      int height = image.height;
      int rotation = _getRotationFromExif(image.exif);
      
      print('=== RAW PIXEL OCR: Image size: ${width}x${height}, rotation: ${rotation}° ===');
      
      // Get raw bytes in platform-specific format
      Uint8List rawBytes;
      InputImageFormat format;
      int bytesPerRow;
      
      if (Platform.isIOS) {
        // Use uint8 format for iOS (raw pixels)
        rawBytes = image.getBytes();
        format = InputImageFormat.bgra8888;
        bytesPerRow = width * 4; // 4 bytes per pixel for BGRA
        print('=== RAW PIXEL OCR: Using iOS raw bytes->BGRA8888 format ===');
      } else {
        rawBytes = image.getBytes();
        format = InputImageFormat.nv21;
        bytesPerRow = width * 3; // 3 bytes per pixel for RGB
        print('=== RAW PIXEL OCR: Using Android raw bytes format ===');
      }
      
      print('=== RAW PIXEL OCR: Raw bytes length: ${rawBytes.length} ===');
      
      InputImageMetadata metadata = InputImageMetadata(
        size: ui.Size(width.toDouble(), height.toDouble()),
        rotation: InputImageRotation.values[rotation ~/ 90],
        format: format,
        bytesPerRow: bytesPerRow,
      );
      
      InputImage inputImage = InputImage.fromBytes(bytes: rawBytes, metadata: metadata);
      
      final RecognizedText recognizedText = await _textRecognizer.processImage(inputImage);
      print('=== RAW PIXEL OCR: Processed, blocks: ${recognizedText.blocks.length} ===');
      
      if (recognizedText.blocks.isNotEmpty) {
        print('=== RAW PIXEL OCR: Success! Text: ${recognizedText.text} ===');
        return recognizedText.text;
      } else {
        print('=== RAW PIXEL OCR: No blocks found ===');
        return null;
      }
      
    } catch (e) {
      print('=== RAW PIXEL OCR ERROR: $e ===');
      return null;
    }
  }
  
  /// Helper function to get rotation from EXIF data
  static int _getRotationFromExif(img_lib.ExifData exif) {
    try {
      var orientation = exif['Orientation']; // EXIF orientation tag
      if (orientation == 3) return 180;
      if (orientation == 6) return 90;
      if (orientation == 8) return 270;
      return 0;
    } catch (e) {
      print('=== EXIF DEBUG: No orientation data, using 0° ===');
      return 0;
    }
  }

  /// Simple ML Kit OCR extraction (original working version)
  static Future<String?> _tryMLKitOCR(String imagePath) async {
    try {
      final inputImage = InputImage.fromFilePath(imagePath);
      final RecognizedText recognizedText = await _textRecognizer.processImage(inputImage);
      
      print('ML Kit raw blocks: ${recognizedText.blocks.length}');
      if (recognizedText.blocks.isNotEmpty) {
        print('Raw ML Kit text: ${recognizedText.text}');
        return recognizedText.text;
      } else {
        print('ML Kit: No text extracted');
        return null;
      }
    } catch (e) {
      print('ML Kit error: $e');
      return null;
    }
  }


  /// Helper method to detect medication-like patterns in text
  static bool _containsMedicationPattern(String text) {
    // Expanded medication patterns to preserve even with low confidence
    final medicationPatterns = [
      RegExp(r'\b\d+\s*(mg|mcg|g|ml|mL|units?|tabs?|capsules?)\b', caseSensitive: false),
      RegExp(r'\b(tablet|capsule|syrup|suspension|injection|cream|ointment|solution|drops|patch)\b', caseSensitive: false),
      RegExp(r'\b\d+\s*x\s*\d+\b'), // Dosage patterns like "2 x 5"
      RegExp(r'\b(once|twice|three times?|daily|bid|tid|qid|prn|as needed)\b', caseSensitive: false),
      RegExp(r'\b[A-Z][a-z]+[A-Z][a-z]+\b'), // CamelCase drug names
      RegExp(r'\b\w+cillin\b', caseSensitive: false), // Antibiotics
      RegExp(r'\b\w+prazole\b', caseSensitive: false), // PPIs
      RegExp(r'\b\w+statin\b', caseSensitive: false), // Statins
      RegExp(r'\b\w+olol\b', caseSensitive: false), // Beta blockers
      RegExp(r'\b\w+pril\b', caseSensitive: false), // ACE inhibitors
      RegExp(r'\b\w+sartan\b', caseSensitive: false), // ARBs
      RegExp(r'\b(metformin|insulin|aspirin|ibuprofen|acetaminophen|tylenol|advil)\b', caseSensitive: false), // Common meds
      RegExp(r'#\s*\d{5,}'), // Prescription numbers
      RegExp(r'\bRx\b', caseSensitive: false), // Prescription indicator
    ];
    
    return medicationPatterns.any((pattern) => pattern.hasMatch(text));
  }

  /// Parse extracted text into medication items with intelligent parsing and LLM enhancement
  static Future<List<MedItem>> parseTextToMedications(String extractedText, String mode, {String? apiKey}) async {
    print('=== PARSING START: Mode $mode, Text length ${extractedText.length} ===');
    print('Full input text: $extractedText');
    
    // Use mode-specific parsing
    List<Map<String, dynamic>> parsed = parseExtractedText(extractedText, mode);
    
    // If no results and LLM available, try LLM fallback
    if (parsed.isEmpty && apiKey != null) {
      print('All parsing failed, trying LLM');
      var llmResult = await parseWithLLM(extractedText, apiKey);
      if (llmResult.isNotEmpty) parsed.add(llmResult);
      print('LLM result: $llmResult');
    }
    
    print('=== PARSING END: ${parsed.length} items ===');
    List<MedItem> medications = [];
    for (var data in parsed) {
      if (data['name'] != null && data['name'].toString().isNotEmpty) {
        medications.add(_convertMapToMedItem(data, mode));
      }
    }
    
    return medications;
  }

  /// Parse extracted text based on mode (floor_stock vs cart_fill)
  static List<Map<String, dynamic>> parseExtractedText(String text, String mode) {
    print('=== PARSING MODE: $mode ===');
    
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

  /// Parse a single line of text into a medication map with intelligent recognition
  static Map<String, dynamic> parseMedicationLine(String line, String mode) {
    print('Trying regex on: $line');
    
    // Try multiple patterns for different label formats
    
    // Pattern 1: Brand name in parentheses before strength (e.g., "Zonisamide (ZONEGRAN) 100 mg capsule")
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
    
    // Pattern 1b: Brand name in parentheses with form before strength (e.g., "zonisamide (ZONEGRAN) capsule 100 mg")
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
    
    // Pattern 2: Complex label with brand and patient info
    RegExp complexRegex = RegExp(
      r'([A-Za-z]+)\s*(?:\(([^)]+)\))?\s+(\d+\s*(?:mg|mcg|unit))\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release).*?(BEDTIME|bid|tid|qd|qhs|prn|daily|once|twice).*?for\s+(?:patient\s+)?([A-Za-z,\s]+)',
      caseSensitive: false
    );
    
    var match = complexRegex.firstMatch(line);
    if (match != null) {
      return {
        'name': match.group(1)?.trim(),
        'brand': match.group(2)?.trim(),
        'strength': match.group(3)?.trim(),
        'type': match.group(4)?.trim() ?? 'tablet',
        'dose': match.group(5)?.trim(),
        'patient': match.group(6)?.trim(),
        'floor': null,
      };
    }
    
    // Pattern 3: Simple medication format (name strength form)
    RegExp simpleRegex = RegExp(
      r'([A-Za-z\s]+?)\s+(\d+\s*(?:mg|mcg|unit))\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)',
      caseSensitive: false
    );
    
    // Pattern 3b: Name form strength format (e.g., "Valproic Acid capsule 250 mg")
    RegExp nameFormStrengthRegex = RegExp(
      r'([A-Za-z\s]+?)\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral|extended release)\s+(\d+\s*(?:mg|mcg|unit))',
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
    
    // Pattern 4: Dosing instructions
    RegExp doseRegex = RegExp(
      r'(take|admin)\s+(\d+)\s+(tablet|capsule)\s+(once|twice|daily|bid|tid|qd|qhs|prn|at bedtime)',
      caseSensitive: false
    );
    
    var doseMatch = doseRegex.firstMatch(line);
    if (doseMatch != null) {
      return {
        'dose': '${doseMatch.group(4)}',
        'admin': '${doseMatch.group(2)} ${doseMatch.group(3)}',
      };
    }

    // Number patterns (separate)
    RegExp numberRegex = RegExp(r'\b(MRN|Rx|Order #|BABCOCK #)?\s*([A-Za-z0-9-]{6,15})\b', caseSensitive: false);
    var numMatch = numberRegex.firstMatch(line);
    if (numMatch != null) {
      return {
        'mrn': numMatch.group(1)?.toLowerCase().contains('mrn') == true ? numMatch.group(2) : null,
        'rx_number': numMatch.group(1)?.toLowerCase().contains('rx') == true ? numMatch.group(2) : null,
        'order_number': numMatch.group(1)?.toLowerCase().contains('order') == true ? numMatch.group(2) : null,
      };
    }

    return {};
  }

  /// Extract MRN (Medical Record Number) from line
  static String? _extractMRN(String line) {
    RegExp mrnPattern = RegExp(r'(?:MRN|mrn|medical\s*record|patient\s*id)\s*:?\s*(\d{6,12})', caseSensitive: false);
    Match? match = mrnPattern.firstMatch(line);
    return match?.group(1)?.trim();
  }

  /// Extract order number from line
  static String? _extractOrderNumber(String line) {
    RegExp orderPattern = RegExp(r'(?:order|rx|prescription)\s*#?\s*:?\s*(\d{6,15})', caseSensitive: false);
    Match? match = orderPattern.firstMatch(line);
    return match?.group(1)?.trim();
  }

  /// Check if line should be skipped (headers, labels, etc.)
  static bool _shouldSkipLine(String line) {
    List<String> skipPatterns = [
      'PAGE BREAK', 'pharmacy', 'medication', 'prescription', 'doctor', 'physician',
      'hospital', 'clinic', 'patient', 'date', 'time', 'address', 'phone',
      'instructions', 'directions', 'warning', 'caution', 'side effects',
      'allergies', 'insurance', 'copay', 'total', 'subtotal', 'quantity',
      'refills', 'generic', 'brand', 'manufacturer', 'lot', 'exp', 'ndc'
    ];
    
    String lowerLine = line.toLowerCase();
    
    // Skip if line is too short or contains only numbers/symbols
    if (line.length < 5 || RegExp(r'^[\d\s\-\.\(\)]+$').hasMatch(line)) {
      return true;
    }
    
    // Skip if line contains skip patterns but no medication indicators
    for (String pattern in skipPatterns) {
      if (lowerLine.contains(pattern) && !_containsMedicationIndicators(lowerLine)) {
        return true;
      }
    }
    
    return false;
  }

  /// Check if line contains medication indicators
  static bool _containsMedicationIndicators(String line) {
    List<String> medicationIndicators = [
      'mg', 'mcg', 'g', 'ml', 'unit', 'tablet', 'capsule', 'injection',
      'cream', 'ointment', 'solution', 'suspension', 'syrup', 'daily',
      'bid', 'tid', 'qid', 'prn', 'once', 'twice'
    ];
    
    return medicationIndicators.any((indicator) => line.contains(indicator));
  }

  /// Validate if a name is a legitimate medication name
  static bool _isValidMedicationName(String name) {
    if (name.length < 3 || name.length > 50) return false;
    
    // Common non-medication words to exclude
    List<String> excludeWords = [
      'the', 'and', 'for', 'with', 'take', 'use', 'apply', 'inject',
      'patient', 'doctor', 'pharmacy', 'prescription', 'medication',
      'instructions', 'directions', 'warning', 'caution', 'side',
      'effects', 'allergies', 'generic', 'brand', 'manufacturer'
    ];
    
    String lowerName = name.toLowerCase();
    
    // Exclude if name is entirely common words
    List<String> words = lowerName.split(' ');
    if (words.every((word) => excludeWords.contains(word))) {
      return false;
    }
    
    // Must contain at least one letter and not be all numbers
    if (!RegExp(r'[A-Za-z]').hasMatch(name) || RegExp(r'^\d+$').hasMatch(name)) {
      return false;
    }
    
    return true;
  }

  /// Calculate pick amount based on frequency
  static int _calculatePickAmount(String frequency) {
    if (frequency.isEmpty) return 1;
    
    String freq = frequency.toUpperCase();
    
    if (freq.contains('DAILY') || freq.contains('ONCE')) return 1;
    if (freq.contains('BID') || freq.contains('TWICE')) return 2;
    if (freq.contains('TID') || freq.contains('THREE')) return 3;
    if (freq.contains('QID') || freq.contains('FOUR')) return 4;
    
    // Extract number from Q4H, Q6H, etc.
    RegExp qPattern = RegExp(r'Q(\d+)H?');
    Match? match = qPattern.firstMatch(freq);
    if (match != null) {
      int hours = int.tryParse(match.group(1) ?? '24') ?? 24;
      return (24 / hours).round().clamp(1, 6);
    }
    
    return 1;
  }

  /// Build sig from frequency information
  static String _buildSigFromFrequency(String frequency, String dose, String unit) {
    if (frequency.isEmpty) return 'Take as directed';
    
    String freq = frequency.toUpperCase();
    String baseInstruction = 'Take $dose $unit';
    
    if (freq.contains('DAILY') || freq.contains('ONCE')) {
      return '$baseInstruction once daily';
    }
    if (freq.contains('BID') || freq.contains('TWICE')) {
      return '$baseInstruction twice daily';
    }
    if (freq.contains('TID') || freq.contains('THREE')) {
      return '$baseInstruction three times daily';
    }
    if (freq.contains('QID') || freq.contains('FOUR')) {
      return '$baseInstruction four times daily';
    }
    if (freq.contains('PRN')) {
      return '$baseInstruction as needed';
    }
    
    return '$baseInstruction $frequency';
  }

  /// Build notes with context information
  static String _buildNotesWithContext(String? existingNotes, String? orderNumber) {
    List<String> notes = [];
    
    if (existingNotes != null && existingNotes.isNotEmpty) {
      notes.add(existingNotes);
    }
    
    if (orderNumber != null) {
      notes.add('Order #$orderNumber');
    }
    
    return notes.join(' | ');
  }

  /// Clean and standardize medication names
  static String _cleanMedicationName(String name) {
    return name
        .replaceAll(RegExp(r'[^\w\s]'), '')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim()
        .split(' ')
        .where((word) => word.length > 1)
        .take(3) // Limit to 3 words max
        .join(' ');
  }

  /// Extract patient information from line (for cart-fill mode)
  static String? _extractPatientInfo(String line) {
    RegExp patientPattern = RegExp(r'(?:patient|pt)\s*:?\s*([A-Za-z\s]+)', caseSensitive: false);
    Match? match = patientPattern.firstMatch(line);
    return match?.group(1)?.trim();
  }

  /// Extract sig (directions) information from line
  static String? _extractSigInfo(String line) {
    RegExp sigPattern = RegExp(r'(?:take|sig)\s*:?\s*(.+)', caseSensitive: false);
    Match? match = sigPattern.firstMatch(line);
    return match?.group(1)?.trim();
  }

  /// Extract floor information from line
  static String? _extractFloorInfo(String line) {
    RegExp floorPattern = RegExp(r'(\d+[A-Z]+(?:-\d+)?)', caseSensitive: false);
    Match? match = floorPattern.firstMatch(line);
    return match?.group(1)?.trim();
  }

  /// Convert parsed map to MedItem object
  static MedItem _convertMapToMedItem(Map<String, dynamic> data, String mode) {
    return MedItem(
      name: data['name'] ?? 'Unknown',
      dose: data['strength'] ?? '1 unit',
      form: data['type'] ?? 'tablet',
      pickAmount: 1,
      calculatedQty: 1.0,
      patient: data['patient'],
      floor: data['floor'],
      sig: data['dose'],
    );
  }

  /// Dispose of resources
  static void dispose() {
    _textRecognizer.close();
  }
}
