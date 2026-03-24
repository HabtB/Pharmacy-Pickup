import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'ocr_service.dart';

class TestOCRService {
  /// Test OCR parsing with the user-provided medication label
  static Future<void> testMedicationLabelParsing() async {
    print('=== TEST OCR: Starting medication label parsing test ===');
    
    try {
      // Create test text based on the uploaded medication label
      String testText = '''Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr
Dose: 5 mg
Admin: 1 tablet
MOUNT SINAI MORNINGSIDE NY
LOT: 8/8/25 230''';
      
      print('=== TEST OCR: Using sample text from medication label ===');
      print('Test text: $testText');
      
      // Test our enhanced parsing with cart_fill mode
      var medications = await OCRService.parseTextToMedications(
        testText, 
        'cart_fill',
        apiKey: null, // Test regex parsing first
      );
      
      print('=== TEST OCR: Parsing results ===');
      print('Found ${medications.length} medications');
      
      for (var med in medications) {
        print('Medication: ${med.name}');
        print('Dose: ${med.dose}');
        print('Form: ${med.form}');
        print('Patient: ${med.patient}');
        print('Sig: ${med.sig}');
        print('---');
      }
      
      // Test individual line parsing
      print('=== TEST OCR: Testing individual line parsing ===');
      var testLine = 'Oxybutynin (DITROPAN XL) 5 mg tablet';
      var singleLineMeds = await OCRService.parseTextToMedications(
        testLine,
        'cart_fill',
        apiKey: null,
      );
      print('Line: $testLine');
      print('Parsed ${singleLineMeds.length} medication(s) from single line');
      
    } catch (e) {
      print('=== TEST OCR ERROR: $e ===');
    }
  }
  
  /// Test with the exact text that should be extracted from the image
  static Future<void> testExpectedOCRText() async {
    print('=== TEST OCR: Testing expected OCR extraction ===');
    
    // This is what ML Kit should ideally extract from the image
    String expectedText = '''Oxybutynin
(DITROPAN XL) 24 hr tablet 5 mg
AT BEDTIME
Medication
Oxybutynin 5 mg tablet extended release 24hr
Dose
5 mg
Admin
1 tablet
MOUNT SINAI MORNINGSIDE NY''';
    
    print('Expected OCR text: $expectedText');
    
    var medications = await OCRService.parseTextToMedications(
      expectedText, 
      'cart_fill',
      apiKey: null,
    );
    
    print('Parsed ${medications.length} medications from expected text');
    for (var med in medications) {
      print('- ${med.name}: ${med.dose} ${med.form}');
    }
  }
}
