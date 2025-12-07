import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pharmacy_pickup_app/main.dart';
import 'package:pharmacy_pickup_app/screens/process_screen.dart';

void main() {
  testWidgets('App smoke test - loads home screen', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const PharmacyPickerApp());
    await tester.pumpAndSettle();

    // Verify home screen title
    expect(find.text('Pharmacy Picker'), findsOneWidget);

    // Verify tabs
    expect(find.text('Floor Stock'), findsOneWidget);
    expect(find.text('Cart-Fill'), findsOneWidget);

    // Verify we are on Floor Stock tab by default
    expect(find.text('Start Floor Stock Scan'), findsOneWidget);
  });
}
