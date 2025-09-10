import 'package:flutter_test/flutter_test.dart';
import 'lib/services/ocr_service.dart';

void main() {
  group('Additional Medication Label Tests', () {
    test('Parse Zonisamide (ZONEGRAN) 100mg capsule', () {
      var line = 'Zonisamide (ZONEGRAN) 100 mg capsule';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Zonisamide result: $result');
      
      expect(result['name'], 'Zonisamide');
      expect(result['brand'], 'ZONEGRAN');
      expect(result['strength'], '100 mg');
      expect(result['type'], 'capsule');
    });
    
    test('Parse Valproic Acid 250mg capsule', () {
      var line = 'Valproic Acid 250 mg capsule';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Valproic Acid result: $result');
      
      expect(result['name'], contains('Valproic'));
      expect(result['strength'], '250 mg');
      expect(result['type'], 'capsule');
    });
    
    test('Parse Fluoxetine (PROZAC) 80mg capsule', () {
      var line = 'Fluoxetine (PROZAC) 80 mg capsule';
      var result = OCRService.parseMedicationLine(line, 'cart_fill');
      
      print('Fluoxetine result: $result');
      
      expect(result['name'], 'Fluoxetine');
      expect(result['brand'], 'PROZAC');
      expect(result['strength'], '80 mg');
      expect(result['type'], 'capsule');
    });
    
    test('Parse full medication label text from images', () async {
      // Test case 1: Zonisamide label
      String zonisamideText = '''zonisamide (ZONEGRAN) capsule 100 mg
Dose: 100 mg = 1 x 100 mg capsule
Dispense Qty: x 1 capsule
MOUNT SINAI MORNINGSIDE NY''';
      
      var medications1 = await OCRService.parseTextToMedications(
        zonisamideText, 
        'cart_fill',
        apiKey: null,
      );
      
      print('Zonisamide full text results:');
      for (var med in medications1) {
        print('- ${med.name}: ${med.dose} ${med.form}');
      }
      
      expect(medications1.length, greaterThan(0));
      expect(medications1.any((m) => m.name.toLowerCase().contains('zonisamide')), true);
      
      // Test case 2: Valproic Acid label  
      String valproicText = '''Valproic Acid capsule 250 mg
Dose: 750 mg = 3 x 250 mg capsule
Dispense Qty: x 3 capsule
MOUNT SINAI MORNINGSIDE NY''';
      
      var medications2 = await OCRService.parseTextToMedications(
        valproicText,
        'cart_fill', 
        apiKey: null,
      );
      
      print('Valproic Acid full text results:');
      for (var med in medications2) {
        print('- ${med.name}: ${med.dose} ${med.form}');
      }
      
      expect(medications2.length, greaterThan(0));
      expect(medications2.any((m) => m.name.toLowerCase().contains('valproic')), true);
      
      // Test case 3: Fluoxetine label
      String fluoxetineText = '''fluOXETINE (PROZAC) capsule 80 mg
Dose: 80 mg
Medication fluOXETINE 20 mg capsule
Admin 4 capsule
MOUNT SINAI MORNINGSIDE NY''';
      
      var medications3 = await OCRService.parseTextToMedications(
        fluoxetineText,
        'cart_fill',
        apiKey: null,
      );
      
      print('Fluoxetine full text results:');
      for (var med in medications3) {
        print('- ${med.name}: ${med.dose} ${med.form}');
      }
      
      expect(medications3.length, greaterThan(0));
      expect(medications3.any((m) => m.name.toLowerCase().contains('fluoxetine')), true);
    });
    
    test('Test case sensitivity and variations', () {
      var testCases = [
        'zonisamide (ZONEGRAN) 100 mg capsule',
        'ZONISAMIDE (Zonegran) 100 mg capsule', 
        'Fluoxetine (prozac) 80 mg capsule',
        'fluOXETINE (PROZAC) 80 mg capsule',
        'valproic acid 250 mg capsule',
        'VALPROIC ACID 250 MG CAPSULE'
      ];
      
      for (var testCase in testCases) {
        var result = OCRService.parseMedicationLine(testCase, 'cart_fill');
        print('Test: "$testCase"');
        print('Result: $result');
        print('---');
        
        // Should extract medication name regardless of case
        expect(result.isNotEmpty, true, reason: 'Should parse: $testCase');
      }
    });
  });
}
