import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/services/ocr_service.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  test('OCR Service - Parse medication text', () async {
    // Mock prescription text
    String mockText = '''
    Metoprolol Tartrate 25 mg tablet
    Take 1 tablet twice daily
    
    Lisinopril 10 mg tablet
    Take 1 tablet once daily
    ''';
    
    print('=== TESTING OCR PARSING ===');
    print('Input text: $mockText');
    
    List<MedItem> medications = await OCRService.parseTextToMedications(
      mockText, 
      'floor_stock'
    );
    
    print('=== RESULTS ===');
    print('Found ${medications.length} medications');
    
    for (var med in medications) {
      print('- ${med.name}: ${med.dose} (${med.form})');
    }
    
    expect(medications.length, greaterThan(0));
  });
}
