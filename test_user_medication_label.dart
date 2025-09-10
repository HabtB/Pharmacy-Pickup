import 'package:flutter_test/flutter_test.dart';
import 'lib/services/ocr_service.dart';

void main() {
  group('User Medication Label Tests', () {
    test('Parse user provided Oxybutynin label - full text', () async {
      // Based on the uploaded medication label image
      String labelText = '''Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr
AT BEDTIME
Medication
Oxybutynin 5 mg tablet extended release 24hr
Dose: 5 mg
Admin: 1 tablet
MOUNT SINAI MORNINGSIDE NY''';
      
      var medications = await OCRService.parseTextToMedications(
        labelText, 
        'cart_fill',
        apiKey: null, // Test regex only
      );
      
      print('Full label parsing result:');
      for (var med in medications) {
        print('- Name: ${med.name}');
        print('- Dose: ${med.dose}');
        print('- Form: ${med.form}');
        print('- Patient: ${med.patient}');
        print('- Sig: ${med.sig}');
        print('---');
      }
      
      expect(medications.length, greaterThan(0));
      expect(medications.first.name, contains('Oxybutynin'));
    });
    
    test('Parse individual lines from user label', () {
      var testLines = [
        'Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr',
        'AT BEDTIME',
        'Oxybutynin 5 mg tablet extended release 24hr',
        'Admin: 1 tablet',
      ];
      
      for (var line in testLines) {
        var result = OCRService.parseMedicationLine(line, 'cart_fill');
        print('Line: "$line"');
        print('Result: $result');
        print('---');
      }
    });
    
    test('Parse mock text that was failing in app', () async {
      String mockText = '''Metoprolol Tartrate 25 mg tablet
Take 1 tablet twice daily

Lisinopril 10 mg tablet  
Take 1 tablet once daily

Atorvastatin 20 mg tablet
Take 1 tablet at bedtime''';
      
      var medications = await OCRService.parseTextToMedications(
        mockText, 
        'cart_fill',
        apiKey: null,
      );
      
      print('Mock text parsing results:');
      for (var med in medications) {
        print('- ${med.name}: ${med.dose} ${med.form}');
      }
      
      expect(medications.length, greaterThan(0));
      expect(medications.any((m) => m.name.contains('Metoprolol')), true);
      expect(medications.any((m) => m.name.contains('Lisinopril')), true);
      expect(medications.any((m) => m.name.contains('Atorvastatin')), true);
    });
  });
}
