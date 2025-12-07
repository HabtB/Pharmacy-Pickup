import 'package:flutter/material.dart';
import '../models/med_item.dart';

class MedicationCard extends StatelessWidget {
  final MedItem med;
  final int displayNumber;
  final bool isIV;
  final bool isFridge;

  const MedicationCard({
    super.key,
    required this.med,
    required this.displayNumber,
    this.isIV = false,
    this.isFridge = false,
  });

  // Helper function to get plural form of medication form
  String _getPluralForm(int amount, String form) {
    if (amount == 1) return form;

    // Handle common forms
    if (form == 'tablet') return 'tablets';
    if (form == 'capsule') return 'capsules';
    if (form == 'drop') return 'drops';
    if (form == 'solution') return 'solution';
    if (form == 'liquid') return 'liquid';

    // Default: add 's'
    return '${form}s';
  }

  @override
  Widget build(BuildContext context) {
    // Define colors based on type
    final Color bgColor = isIV ? Colors.red.shade50 : (isFridge ? Colors.cyan.shade50 : Colors.blue.shade50);
    final Color borderColor = isIV ? Colors.red.shade200 : (isFridge ? Colors.cyan.shade200 : Colors.blue.shade200);
    final Color textColor = isIV ? Colors.red.shade700 : (isFridge ? Colors.cyan.shade800 : Colors.blue.shade700);
    final Color iconColor = isIV ? Colors.red.shade600 : (isFridge ? Colors.cyan.shade700 : Colors.blue.shade600);

    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      // Add a subtle border or tint for fridge items if needed, but the number box color is the main indicator
      color: isFridge ? Colors.cyan.shade50.withOpacity(0.3) : null, 
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Medication number
            SizedBox(
              width: 50,
              child: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: borderColor),
                ),
                child: Text(
                  '#$displayNumber',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            const SizedBox(width: 12),
            // Medication details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name line with icon
                  Row(
                    children: [
                      Icon(Icons.medication, size: 16, color: isIV ? Colors.red.shade600 : Colors.blue.shade600),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          'Name: ${med.name}',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  // Dose line with icon
                  if (med.dose.isNotEmpty)
                    Row(
                      children: [
                        Icon(Icons.speed, size: 14, color: Colors.green.shade600),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            'Dose: ${med.dose}',
                            style: const TextStyle(
                              fontSize: 14,
                              color: Colors.black87,
                            ),
                          ),
                        ),
                      ],
                    ),
                  if (med.dose.isNotEmpty) const SizedBox(height: 4),
                  // Admin line with icon
                  if (med.admin != null && med.admin!.isNotEmpty)
                    Row(
                      children: [
                        Icon(Icons.schedule, size: 14, color: Colors.orange.shade600),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            'Admin: ${med.admin}',
                            style: const TextStyle(
                              fontSize: 14,
                              color: Colors.black87,
                            ),
                          ),
                        ),
                      ],
                    ),
                  if (med.admin != null && med.admin!.isNotEmpty) const SizedBox(height: 4),
                  // Pick Amount (24-hour quantity)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.inventory_2, size: 14, color: Colors.purple.shade600),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              'Pick Amount: ${med.pickAmount} ${_getPluralForm(med.pickAmount, med.form)}',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: Colors.purple.shade700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      // Floor Breakdown
                      if (med.floorBreakdown != null && med.floorBreakdown!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(left: 18.0, top: 2.0),
                          child: Text(
                             // Format: "- 23 - 7 West1, 15 - 6-CICU"
                             med.floorBreakdown!.map((item) => '${item['amount']} - ${item['floor']}').join(', '),
                             style: TextStyle(
                               fontSize: 13,
                               color: Colors.grey.shade700,
                               fontStyle: FontStyle.italic,
                             ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            // Location indicator
            Container(
              margin: const EdgeInsets.only(left: 8),
              child: med.location != null
                  ? Icon(Icons.location_on, color: Colors.green.shade600, size: 20)
                  : Icon(Icons.location_off, color: Colors.grey.shade400, size: 20),
            ),
          ],
        ),
      ),
    );
  }
}
