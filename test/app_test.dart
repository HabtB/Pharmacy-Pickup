import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';
import 'package:pharmacy_pickup_app/services/database_service.dart';
import 'package:pharmacy_pickup_app/services/medication_processor.dart';
import 'package:pharmacy_pickup_app/services/text_parser.dart';

void main() {
  group('Text Parsing Tests', () {
    test('Parses and cleans example line', () {
      String sample = 'lamotrigine (LAMICTAL) 100 mg tablet 1';
      var parsed = TextParser.parseExtractedText(sample);
      var cleaned = TextParser.cleanParsedMeds(parsed);
      
      expect(cleaned.length, 1);
      expect(cleaned[0].name, 'Lamotrigine');
      expect(cleaned[0].dose, '100 mg');
      expect(cleaned[0].form, 'tablet');
      expect(cleaned[0].pickAmount, 1);
    });

    test('Parses multiple medications', () {
      String sample = '''
        Gabapentin 100 mg capsule 3
        Metoprolol 25 mg tablet 2
        Lisinopril 10 mg tablet 1
      ''';
      var parsed = TextParser.parseExtractedText(sample);
      var cleaned = TextParser.cleanParsedMeds(parsed);
      
      expect(cleaned.length, 3);
      expect(cleaned[0].name, 'Gabapentin');
      expect(cleaned[1].name, 'Metoprolol');
      expect(cleaned[2].name, 'Lisinopril');
    });

    test('Handles malformed input gracefully', () {
      String sample = '''
        Invalid line without numbers
        Another bad line
        Gabapentin 100 mg capsule 3
      ''';
      var parsed = TextParser.parseExtractedText(sample);
      var cleaned = TextParser.cleanParsedMeds(parsed);
      
      expect(cleaned.length, 1);
      expect(cleaned[0].name, 'Gabapentin');
    });
  });

  group('Database Matching Tests', () {
    test('DB match for example med', () async {
      var med = MedItem(
        name: 'Gabapentin', 
        dose: '100 mg', 
        form: 'capsule', 
        pickAmount: 3
      );
      var locInfo = await DatabaseService.getLocationAndNotesForMed(med);
      
      expect(locInfo, isNotNull);
      expect(locInfo?['location'], contains('Front Shelf 7'));
      expect(locInfo?['location'], contains('Row 2'));
      expect(locInfo?['location'], contains('Bin 4'));
    });

    test('Fuzzy matching works for OCR variations', () async {
      // Test with slight OCR variations
      var med1 = MedItem(
        name: 'metoprolol', // lowercase
        dose: '25mg', // no space
        form: 'tab', // abbreviated
        pickAmount: 1
      );
      var locInfo1 = await DatabaseService.getLocationAndNotesForMed(med1);
      
      expect(locInfo1, isNotNull);
      expect(locInfo1?['location'], contains('Front Shelf 1'));
    });

    test('Returns null for unknown medication', () async {
      var unknownMed = MedItem(
        name: 'UnknownMedication',
        dose: '999 mg',
        form: 'tablet',
        pickAmount: 1
      );
      var locInfo = await DatabaseService.getLocationAndNotesForMed(unknownMed);
      
      expect(locInfo, isNull);
    });

    test('Handles safety notes correctly', () async {
      var med = MedItem(
        name: 'NIFEdipine ER',
        dose: '30 mg',
        form: 'tablet',
        pickAmount: 1
      );
      var locInfo = await DatabaseService.getLocationAndNotesForMed(med);
      
      expect(locInfo, isNotNull);
      expect(locInfo?['notes'], contains('LOOK ALIKE'));
    });
  });

  group('Medication Processing Tests', () {
    test('Aggregates duplicate medications', () async {
      List<MedItem> testMeds = [
        MedItem(name: 'Gabapentin', dose: '100 mg', form: 'capsule', pickAmount: 3),
        MedItem(name: 'Gabapentin', dose: '100 mg', form: 'capsule', pickAmount: 2),
        MedItem(name: 'Metoprolol', dose: '25 mg', form: 'tablet', pickAmount: 1),
      ];
      
      var processed = await MedicationProcessor.processAndOrganizeMedications(testMeds);
      
      expect(processed.length, 2);
      
      // Find the aggregated Gabapentin
      var gabapentin = processed.firstWhere((med) => med.name == 'Gabapentin');
      expect(gabapentin.pickAmount, 5); // 3 + 2
    });

    test('Sorting by location works correctly', () async {
      List<MedItem> testMeds = [
        MedItem(name: 'Gabapentin', dose: '100 mg', form: 'capsule', pickAmount: 1),
        MedItem(name: 'Metoprolol Tartrate', dose: '25 mg', form: 'tablet', pickAmount: 1),
        MedItem(name: 'Levothyroxine', dose: '50 mcg', form: 'tablet', pickAmount: 1),
      ];
      
      var processed = await MedicationProcessor.processAndOrganizeMedications(testMeds);
      
      // Should be sorted by shelf number (1, 3, 7)
      expect(processed[0].location, contains('Front Shelf 1')); // Metoprolol
      expect(processed[1].location, contains('Front Shelf 3')); // Levothyroxine
      expect(processed[2].location, contains('Front Shelf 7')); // Gabapentin
    });
  });

  group('Performance Tests', () {
    test('Processes large batch efficiently', () async {
      // Generate 50 mock medications (simulating large prescription batch)
      List<MedItem> largeBatch = TextParser.generateMockMedications(50);
      
      Stopwatch stopwatch = Stopwatch()..start();
      var processed = await MedicationProcessor.processAndOrganizeMedications(largeBatch);
      stopwatch.stop();
      
      expect(processed.isNotEmpty, true);
      expect(stopwatch.elapsedMilliseconds, lessThan(5000)); // Should complete in under 5 seconds
      
      print('Processed ${largeBatch.length} medications in ${stopwatch.elapsedMilliseconds}ms');
    });

    test('Database query performance', () async {
      List<Future<Map<String, String>?>> queries = [];
      
      // Create 20 concurrent database queries
      for (int i = 0; i < 20; i++) {
        var med = MedItem(
          name: 'Gabapentin',
          dose: '100 mg',
          form: 'capsule',
          pickAmount: 1
        );
        queries.add(DatabaseService.getLocationAndNotesForMed(med));
      }
      
      Stopwatch stopwatch = Stopwatch()..start();
      var results = await Future.wait(queries);
      stopwatch.stop();
      
      expect(results.length, 20);
      expect(results.every((result) => result != null), true);
      expect(stopwatch.elapsedMilliseconds, lessThan(2000)); // Should complete in under 2 seconds
      
      print('Completed 20 database queries in ${stopwatch.elapsedMilliseconds}ms');
    });
  });

  group('Edge Cases Tests', () {
    test('Handles empty input', () {
      var parsed = TextParser.parseExtractedText('');
      expect(parsed.isEmpty, true);
    });

    test('Handles medications with no location', () async {
      var unknownMed = MedItem(
        name: 'UnknownMedication',
        dose: '100 mg',
        form: 'tablet',
        pickAmount: 1
      );
      
      var processed = await MedicationProcessor.processAndOrganizeMedications([unknownMed]);
      
      expect(processed.length, 1);
      expect(processed[0].location, isNull);
    });

    test('Handles zero pick amount', () {
      var med = MedItem(
        name: 'TestMed',
        dose: '100 mg',
        form: 'tablet',
        pickAmount: 0
      );
      
      expect(med.pickAmount, 0);
    });

    test('Handles very long medication names', () {
      String longName = 'VeryLongMedicationNameThatExceedsNormalLength';
      var med = MedItem(
        name: longName,
        dose: '100 mg',
        form: 'tablet',
        pickAmount: 1
      );
      
      expect(med.name.length, greaterThan(30));
      expect(med.name, equals(longName));
    });

    test('Handles special characters in medication names', () async {
      var med = MedItem(
        name: 'Co-trimoxazole',
        dose: '400 mg',
        form: 'tablet',
        pickAmount: 1
      );
      
      // Should not crash when processing special characters
      var processed = await MedicationProcessor.processAndOrganizeMedications([med]);
      expect(processed.length, 1);
    });
  });

  group('Data Integrity Tests', () {
    test('MedItem equality works correctly', () {
      var med1 = MedItem(name: 'Test', dose: '100 mg', form: 'tablet', pickAmount: 1);
      var med2 = MedItem(name: 'Test', dose: '100 mg', form: 'tablet', pickAmount: 2);
      var med3 = MedItem(name: 'Different', dose: '100 mg', form: 'tablet', pickAmount: 1);
      
      expect(med1 == med2, true); // Same medication, different amounts
      expect(med1 == med3, false); // Different medications
    });

    test('MedItem copyWith works correctly', () {
      var original = MedItem(name: 'Test', dose: '100 mg', form: 'tablet', pickAmount: 1);
      var updated = original.copyWith(location: 'Front Shelf 1, Row 1, Bin 1');
      
      expect(updated.name, equals(original.name));
      expect(updated.location, equals('Front Shelf 1, Row 1, Bin 1'));
      expect(original.location, isNull); // Original unchanged
    });

    test('Database contains expected number of medications', () async {
      var allMeds = await DatabaseService.getAllMedications();
      
      expect(allMeds.length, greaterThan(100)); // Should have 150+ medications
      expect(allMeds.every((med) => med.name.isNotEmpty), true);
      expect(allMeds.every((med) => med.location != null), true);
    });
  });
}
