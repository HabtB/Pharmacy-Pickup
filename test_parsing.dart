import 'package:flutter_test/flutter_test.dart';
import 'lib/services/ocr_service.dart';

void main() {
  test('Parse label line', () {
    var line = 'oxybutynin 5 mg tablet (DITROPAN XL) oral 24 hr extended release tablet, Dose 5 mg, Admin 1 tablet, BEDTIME; oral for Polanco, Milena';
    var med = OCRService.parseMedicationLine(line, 'cart_fill');
    
    print('Parsing result: $med');
    
    expect(med['name'], 'oxybutynin');
    expect(med['brand'], 'DITROPAN XL');
    expect(med['strength'], contains('5 mg'));
    expect(med['type'], contains('tablet'));
    expect(med['dose'], 'BEDTIME');
    expect(med['patient'], contains('Polanco'));
  });
}
