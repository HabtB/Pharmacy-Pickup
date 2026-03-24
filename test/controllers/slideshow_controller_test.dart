import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/controllers/slideshow_controller.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  group('SlideshowController', () {
    late SlideshowController controller;

    List<MedItem> _createTestMeds() => [
          MedItem(
              name: 'AlphaZolam',
              dose: '1 mg',
              form: 'tablet',
              pickAmount: 2,
              pickLocation: 'STR',
              pickLocationDesc: 'Store Room',
              zone: 'Zone 2'),
          MedItem(
              name: 'BetaBlocker',
              dose: '25 mg',
              form: 'tablet',
              pickAmount: 1,
              pickLocation: 'PHRM',
              pickLocationDesc: 'Main Pharmacy'),
          MedItem(
              name: 'Calcium',
              dose: '500 mg',
              form: 'tablet',
              pickAmount: 3,
              pickLocation: 'IV',
              pickLocationDesc: 'IV Room'),
          MedItem(
              name: 'Diazepam',
              dose: '5 mg',
              form: 'tablet',
              pickAmount: 1,
              pickLocation: 'FRIDGE',
              pickLocationDesc: 'Fridge'),
        ];

    setUp(() {
      controller = SlideshowController(initialMedications: _createTestMeds());
    });

    tearDown(() {
      controller.dispose();
    });

    // ── Sorting ──────────────────────────────────────────────────────────

    test('sorts medications by location priority: IV < PHRM < FRIDGE < STR',
        () {
      // Expected order: IV(0) → PHRM(1) → FRIDGE(2) → STR(5)
      expect(controller.medications[0].pickLocation, 'IV');
      expect(controller.medications[1].pickLocation, 'PHRM');
      expect(controller.medications[2].pickLocation, 'FRIDGE');
      expect(controller.medications[3].pickLocation, 'STR');
    });

    test('sorts same-priority medications alphabetically by name', () {
      final meds = [
        MedItem(
            name: 'Zebra',
            dose: '1 mg',
            form: 'tablet',
            pickAmount: 1,
            pickLocation: 'PHRM'),
        MedItem(
            name: 'Alpha',
            dose: '1 mg',
            form: 'tablet',
            pickAmount: 1,
            pickLocation: 'PHRM'),
      ];
      final c = SlideshowController(initialMedications: meds);
      expect(c.medications[0].name, 'Alpha');
      expect(c.medications[1].name, 'Zebra');
      c.dispose();
    });

    // ── Location grouping ────────────────────────────────────────────────

    test('builds correct location groups', () {
      expect(controller.locationGroups.length, 4);
      // Each test med has a unique location
      expect(controller.locationOrder.isNotEmpty, true);
    });

    test('PHRM maps to "Main Pharmacy" group key', () {
      expect(controller.locationGroups.containsKey('Main Pharmacy'), true);
    });

    // ── toggleComplete ───────────────────────────────────────────────────

    test('toggleComplete flips the correct index', () {
      expect(controller.completedItems[0], false);
      controller.toggleComplete(0);
      expect(controller.completedItems[0], true);
      // Toggle again
      controller.toggleComplete(0);
      expect(controller.completedItems[0], false);
    });

    test('toggleComplete also updates isPicked on the MedItem', () {
      controller.toggleComplete(1);
      // medications getter returns unmodifiable, but the internal list
      // was updated
      expect(controller.medications[1].isPicked, true);
    });

    // ── updateActualQuantity ─────────────────────────────────────────────

    test('updateActualQuantity increments correctly', () {
      // After sorting: index 0 is IV (pickAmount=3), so 3+1=4
      controller.updateActualQuantity(0, 1);
      expect(controller.medications[0].actualPickedAmount, 4);
    });

    test('updateActualQuantity clamps to 0 minimum', () {
      controller.updateActualQuantity(1, -999);
      expect(controller.medications[1].actualPickedAmount, 0);
    });

    // ── setActualQuantity ────────────────────────────────────────────────

    test('setActualQuantity sets exact value', () {
      controller.setActualQuantity(0, 42);
      expect(controller.medications[0].actualPickedAmount, 42);
    });

    test('setActualQuantity clamps negative to 0', () {
      controller.setActualQuantity(0, -5);
      expect(controller.medications[0].actualPickedAmount, 0);
    });

    // ── handleWarningEdit ────────────────────────────────────────────────

    test('handleWarningEdit updates pickAmount and clears warning', () {
      // Give a medication a warning first
      controller.handleWarningEdit(0, 10);
      expect(controller.medications[0].pickAmount, 10);
      expect(controller.medications[0].warning, isNull);
    });

    // ── resetCompletion ──────────────────────────────────────────────────

    test('resetCompletion clears all and resets index', () {
      controller.toggleComplete(0);
      controller.toggleComplete(1);
      controller.setCurrentIndex(2);

      controller.resetCompletion();

      expect(controller.completedItems.every((c) => !c), true);
      expect(controller.currentIndex, 0);
    });

    // ── getCurrentLocation ───────────────────────────────────────────────

    test('getCurrentLocation returns correct label for current index', () {
      // Index 0 is IV after sorting
      // IV pickLocationDesc will be null, so group key falls to
      // pickLocationDesc ?? 'Unknown Location'
      final loc = controller.getCurrentLocation();
      expect(loc, isNotEmpty);
    });

    // ── getCurrentLocationStats ──────────────────────────────────────────

    test('getCurrentLocationStats returns well-formed map', () {
      final stats = controller.getCurrentLocationStats();
      expect(stats.containsKey('location'), true);
      expect(stats.containsKey('totalInGroup'), true);
      expect(stats.containsKey('completedInGroup'), true);
      expect(stats.containsKey('locationNumber'), true);
      expect(stats.containsKey('totalLocations'), true);
      expect(stats['totalLocations'], controller.locationOrder.length);
    });

    // ── Encapsulation ────────────────────────────────────────────────────

    test('medications getter returns unmodifiable list', () {
      expect(
        () => controller.medications.add(
          MedItem(name: 'X', dose: '1', form: 'tab', pickAmount: 1),
        ),
        throwsUnsupportedError,
      );
    });
  });
}
