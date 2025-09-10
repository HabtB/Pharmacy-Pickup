import 'package:flutter_test/flutter_test.dart';
import 'lib/services/ocr_service.dart';

void main() {
  group('Enhanced Parsing Tests', () {
    test('Parse simple medication format', () {
      var line = 'Metoprolol Tartrate 25 mg tablet';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Simple format result: $result');
      
      expect(result['name'], 'Metoprolol Tartrate');
      expect(result['strength'], '25 mg');
      expect(result['type'], 'tablet');
    });
    
    test('Parse dosing instruction', () {
      var line = 'Take 1 tablet twice daily';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Dosing result: $result');
      
      expect(result['dose'], 'twice');
      expect(result['admin'], '1 tablet');
    });
    
    test('Parse user medication label', () {
      var line = 'Oxybutynin 5 mg tablet extended release';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('User label result: $result');
      
      expect(result['name'], 'Oxybutynin');
      expect(result['strength'], '5 mg');
      expect(result['type'], contains('tablet'));
    });
    
    test('Parse complex label with brand', () {
      var line = 'Oxybutynin (DITROPAN XL) 5 mg tablet extended release BEDTIME for patient Smith';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Complex label result: $result');
      
      expect(result['name'], 'Oxybutynin');
      expect(result['brand'], 'DITROPAN XL');
      expect(result['strength'], '5 mg');
      expect(result['dose'], 'BEDTIME');
      expect(result['patient'], contains('Smith'));
    });
  });
}
