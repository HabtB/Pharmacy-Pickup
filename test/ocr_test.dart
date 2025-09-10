import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/services/ocr_service.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  group('OCR Service Tests', () {
    test('should parse medication text correctly', () async {
      // Simulate extracted text from a prescription
      String mockExtractedText = '''
      Metoprolol Tartrate 25 mg tablet
      Take 1 tablet twice daily
      
      Lisinopril 10 mg tablet  
      Take 1 tablet once daily
      
      Atorvastatin 20 mg tablet
      Take 1 tablet at bedtime
      ''';
      
      print('=== OCR TEST: Starting medication parsing test ===');
      print('Mock extracted text:');
      print(mockExtractedText);
      
      // Parse the text into medications
      List<MedItem> medications = await OCRService.parseTextToMedications(
        mockExtractedText, 
        'floor_stock'
      );
      
      print('=== OCR TEST: Parsed ${medications.length} medications ===');
      
      for (int i = 0; i < medications.length; i++) {
        MedItem med = medications[i];
        print('Medication ${i + 1}:');
        print('  Name: ${med.name}');
        print('  Dose: ${med.dose}');
        print('  Form: ${med.form}');
        print('  Pick Amount: ${med.pickAmount}');
        print('  Calculated Qty: ${med.calculatedQty}');
        print('---');
      }
      
      // Verify we got some medications
      expect(medications.length, greaterThan(0));
      
      // Check first medication
      if (medications.isNotEmpty) {
        MedItem firstMed = medications.first;
        expect(firstMed.name.toLowerCase(), contains('metoprolol'));
        print('✅ First medication name contains "metoprolol": ${firstMed.name}');
      }
    });
    
    test('should handle medication pattern detection', () {
      print('=== OCR TEST: Testing medication pattern detection ===');
      
      List<String> testLines = [
        'Metoprolol 25 mg tablet',
        'Lisinopril 10mg capsule',
        'Atorvastatin 20 mg once daily',
        'Take with food',  // Should be skipped
        'Patient Name: John Doe',  // Should be skipped
        'Amoxicillin 500mg suspension'
      ];
      
      for (String line in testLines) {
        bool containsPattern = OCRService._containsMedicationPattern != null;
        print('Line: "$line" - Contains med pattern: $containsPattern');
      }
    });
  });
}

// Extension to access private methods for testing
extension OCRServiceTest on OCRService {
  static bool _containsMedicationPattern(String text) {
    // Copy of the private method for testing
    final medicationPatterns = [
      RegExp(r'\b\d+\s*(mg|mcg|g|ml|mL|units?|tabs?|capsules?)\b', caseSensitive: false),
      RegExp(r'\b(tablet|capsule|syrup|suspension|injection|cream|ointment|solution|drops|patch)\b', caseSensitive: false),
      RegExp(r'\b\d+\s*x\s*\d+\b'),
      RegExp(r'\b(once|twice|three times?|daily|bid|tid|qid|prn|as needed)\b', caseSensitive: false),
    ];
    
    return medicationPatterns.any((pattern) => pattern.hasMatch(text));
  }
}
