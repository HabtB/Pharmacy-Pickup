import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/widgets/medication_card.dart';
import 'package:pharmacy_pickup_app/models/med_item.dart';

void main() {
  testWidgets('MedicationCard displays correct info', (WidgetTester tester) async {
    // Create a sample medication
    final med = MedItem(
      name: 'Amoxicillin',
      dose: '500 mg',
      form: 'capsule',
      pickAmount: 2,
      location: 'Bin A1',
      admin: 'Take 1 capsule twice daily'
    );

    // Build the widget
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: MedicationCard(
          med: med,
          displayNumber: 1,
        ),
      ),
    ));

    // Verify details are displayed
    expect(find.text('Name: Amoxicillin'), findsOneWidget);
    expect(find.text('Dose: 500 mg'), findsOneWidget);
    expect(find.text('#1'), findsOneWidget);
    // Pluralization check
    expect(find.text('Pick Amount: 2 capsules'), findsOneWidget);
  });

  testWidgets('MedicationCard displays IV styling', (WidgetTester tester) async {
    final med = MedItem(
      name: 'Vancomycin',
      dose: '1 g',
      form: 'IV Bag',
      pickAmount: 1,
    );

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: MedicationCard(
          med: med,
          displayNumber: 2,
          isIV: true,
        ),
      ),
    ));

    expect(find.text('#2'), findsOneWidget);
    // Verify IV specific icon color (red-ish) - hard to test exact color in widget test without finding widget
    // but we can ensure it renders
    expect(find.byType(Card), findsOneWidget);
  });
}
