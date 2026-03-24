import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/controllers/process_controller.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  group('ProcessController', () {
    late ProcessController controller;

    setUp(() {
      controller = ProcessController(mode: 'floor_stock');
    });

    tearDown(() {
      controller.dispose();
    });

    // ── Initial state ────────────────────────────────────────────────────

    test('starts with empty medication lists', () {
      expect(controller.scannedMedications, isEmpty);
      expect(controller.processedMedications, isEmpty);
      expect(controller.isProcessing, false);
    });

    test('mode is stored correctly', () {
      final c = ProcessController(mode: 'cart_fill');
      expect(c.mode, 'cart_fill');
      c.dispose();
    });

    // ── restoreSession ───────────────────────────────────────────────────

    test('restoreSession populates scannedMedications', () {
      final meds = [
        MedItem(name: 'Test', dose: '10 mg', form: 'tablet', pickAmount: 1),
        MedItem(name: 'Test2', dose: '20 mg', form: 'capsule', pickAmount: 2),
      ];

      controller.restoreSession(meds);

      expect(controller.scannedMedications.length, 2);
      expect(controller.scannedMedications[0].name, 'Test');
      expect(controller.scannedMedications[1].name, 'Test2');
    });

    test('restoreSession creates a defensive copy', () {
      final meds = [
        MedItem(name: 'Test', dose: '10 mg', form: 'tablet', pickAmount: 1),
      ];

      controller.restoreSession(meds);
      meds.clear(); // Mutating original list
      expect(controller.scannedMedications.length, 1);
    });

    // ── setScannedMedications ────────────────────────────────────────────

    test('setScannedMedications replaces the list', () {
      controller.restoreSession([
        MedItem(name: 'Old', dose: '1 mg', form: 'tab', pickAmount: 1),
      ]);

      controller.setScannedMedications([
        MedItem(name: 'New', dose: '2 mg', form: 'cap', pickAmount: 2),
        MedItem(name: 'New2', dose: '3 mg', form: 'tab', pickAmount: 3),
      ]);

      expect(controller.scannedMedications.length, 2);
      expect(controller.scannedMedications[0].name, 'New');
    });

    // ── clearAll ─────────────────────────────────────────────────────────

    test('clearAll empties both lists', () {
      controller.restoreSession([
        MedItem(name: 'A', dose: '1', form: 'tab', pickAmount: 1),
      ]);

      controller.clearAll();

      expect(controller.scannedMedications, isEmpty);
      expect(controller.processedMedications, isEmpty);
    });

    // ── addMedications ───────────────────────────────────────────────────

    test('addMedications appends to existing list', () {
      controller.restoreSession([
        MedItem(name: 'A', dose: '1', form: 'tab', pickAmount: 1),
      ]);

      controller.addMedications([
        MedItem(name: 'B', dose: '2', form: 'cap', pickAmount: 2),
      ]);

      expect(controller.scannedMedications.length, 2);
      expect(controller.scannedMedications[1].name, 'B');
    });

    // ── Encapsulation ────────────────────────────────────────────────────

    test('scannedMedications getter returns unmodifiable list', () {
      controller.restoreSession([
        MedItem(name: 'A', dose: '1', form: 'tab', pickAmount: 1),
      ]);

      expect(
        () => controller.scannedMedications.add(
          MedItem(name: 'X', dose: '1', form: 'tab', pickAmount: 1),
        ),
        throwsUnsupportedError,
      );
    });

    // ── resetProcessingController ────────────────────────────────────────

    test('resetProcessingController creates a new instance', () {
      final original = controller.processingController;
      controller.resetProcessingController();
      expect(identical(controller.processingController, original), false);
    });

    // ── Change notifications ─────────────────────────────────────────────

    test('restoreSession triggers notifyListeners', () {
      int callCount = 0;
      controller.addListener(() => callCount++);

      controller.restoreSession([
        MedItem(name: 'A', dose: '1', form: 'tab', pickAmount: 1),
      ]);

      expect(callCount, 1);
    });

    test('clearAll triggers notifyListeners', () {
      int callCount = 0;
      controller.addListener(() => callCount++);

      controller.clearAll();

      expect(callCount, 1);
    });

    test('addMedications triggers notifyListeners', () {
      int callCount = 0;
      controller.addListener(() => callCount++);

      controller.addMedications([
        MedItem(name: 'A', dose: '1', form: 'tab', pickAmount: 1),
      ]);

      expect(callCount, 1);
    });

    // ── processScannedImages with empty list ─────────────────────────────

    test('processScannedImages with empty list is a no-op', () async {
      await controller.processScannedImages([]);
      expect(controller.scannedMedications, isEmpty);
      expect(controller.isProcessing, false);
    });
  });
}
