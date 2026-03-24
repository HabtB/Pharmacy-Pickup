import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  group('MedItem', () {
    MedItem _base() => const MedItem(
          name: 'Metoprolol',
          dose: '25 mg',
          form: 'tablet',
          pickAmount: 2,
          location: 'Shelf A',
          pickLocation: 'PHRM',
          pickLocationDesc: 'Main Pharmacy',
        );

    // ── Equality (Equatable) ─────────────────────────────────────────────

    test('two identical MedItems are equal', () {
      final a = _base();
      final b = _base();
      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });

    test('different name breaks equality', () {
      final a = _base();
      final b = _base().copyWith(name: 'Lisinopril');
      expect(a, isNot(equals(b)));
    });

    test('different isPicked breaks equality', () {
      final a = _base();
      final b = _base().copyWith(isPicked: true);
      expect(a, isNot(equals(b)));
    });

    test('different floorBreakdown breaks equality', () {
      final a = MedItem(
        name: 'X',
        dose: '1 mg',
        form: 'tab',
        pickAmount: 1,
        floorBreakdown: [
          {'floor': '6W', 'amount': 1}
        ],
      );
      final b = MedItem(
        name: 'X',
        dose: '1 mg',
        form: 'tab',
        pickAmount: 1,
        floorBreakdown: [
          {'floor': '7E', 'amount': 2}
        ],
      );
      expect(a, isNot(equals(b)));
    });

    // ── copyWith ─────────────────────────────────────────────────────────

    test('copyWith preserves unchanged fields', () {
      final original = _base();
      final copy = original.copyWith(pickAmount: 5);
      expect(copy.name, original.name);
      expect(copy.dose, original.dose);
      expect(copy.pickAmount, 5);
    });

    test('copyWith creates a new instance', () {
      final original = _base();
      final copy = original.copyWith();
      expect(copy, equals(original));
      expect(identical(copy, original), false);
    });

    // ── fromMap / toMap round-trip ────────────────────────────────────────

    test('toMap produces correct keys', () {
      final map = _base().toMap();
      expect(map['name'], 'Metoprolol');
      expect(map['dose'], '25 mg');
      expect(map['form'], 'tablet');
      expect(map['pick_amount'], 2);
      expect(map['pick_location'], 'PHRM');
      expect(map['is_picked'], false);
    });

    test('fromMap → toMap round-trip preserves data', () {
      final original = _base();
      final roundTripped = MedItem.fromMap(original.toMap());
      expect(roundTripped.name, original.name);
      expect(roundTripped.dose, original.dose);
      expect(roundTripped.form, original.form);
      expect(roundTripped.pickAmount, original.pickAmount);
      expect(roundTripped.pickLocation, original.pickLocation);
    });

    // ── _calculateFromSig ────────────────────────────────────────────────

    test('calculatedQty defaults to 1.0 when no sig', () {
      expect(_base().calculatedQty, 1.0);
    });

    test('fromMap calculates qty from sig "bid" → 2', () {
      final med = MedItem.fromMap({
        'name': 'Test',
        'dose': '10 mg',
        'form': 'tablet',
        'pick_amount': 1,
        'sig': 'bid',
      });
      expect(med.calculatedQty, 2.0);
    });

    test('fromMap calculates qty from sig "tid" → 3', () {
      final med = MedItem.fromMap({
        'name': 'Test',
        'dose': '10 mg',
        'form': 'tablet',
        'pick_amount': 1,
        'sig': 'tid',
      });
      expect(med.calculatedQty, 3.0);
    });

    // ── hashCode quality ─────────────────────────────────────────────────

    test('hashCode differs for minimally different items', () {
      // XOR-chain hashCode would often collide here; Equatable should not
      final a = const MedItem(
        name: 'A',
        dose: '1 mg',
        form: 'tab',
        pickAmount: 1,
      );
      final b = const MedItem(
        name: 'B',
        dose: '1 mg',
        form: 'tab',
        pickAmount: 1,
      );
      // Not guaranteed by spec, but Equatable's implementation should
      // produce different hashes for different names
      expect(a.hashCode, isNot(equals(b.hashCode)));
    });
  });
}
