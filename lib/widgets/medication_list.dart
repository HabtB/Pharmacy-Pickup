import 'package:flutter/material.dart';
import '../models/med_item.dart';
import 'medication_card.dart';

class MedicationList extends StatelessWidget {
  final List<MedItem> medications;

  const MedicationList({
    super.key,
    required this.medications,
  });

  // Helper function to check if medication is an IV bag
  bool _isIVBag(MedItem med) {
    final ivMedications = [
      'cefazolin', 'ceftriaxone', 'ampicillin', 'vancomycin', 'piperacillin',
      'meropenem', 'ertapenem', 'ceftazidime', 'cefepime', 'gentamicin',
      'tobramycin', 'azithromycin', 'levofloxacin', 'ciprofloxacin', 'metronidazole',
      'normal saline', 'lactated ringers', 'dextrose', 'sodium chloride'
    ];

    String nameLower = med.name.toLowerCase();
    String formLower = med.form.toLowerCase();

    if (formLower.contains('iv') || formLower.contains('bag') || formLower.contains('infusion')) {
      return true;
    }

    return ivMedications.any((ivMed) => nameLower.contains(ivMed));
  }

  @override
  Widget build(BuildContext context) {
    // Separate regular meds and IV bags
    final regularMeds = medications.where((med) => !_isIVBag(med)).toList();
    final ivBags = medications.where((med) => _isIVBag(med)).toList();

    return ListView(
      children: [
        // Regular Medications Section
        if (regularMeds.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Icon(Icons.medication, color: Colors.blue.shade700, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Regular Medications (${regularMeds.length})',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.blue.shade700,
                  ),
                ),
              ],
            ),
          ),
          ...regularMeds.asMap().entries.map((entry) {
            final index = entry.key;
            final med = entry.value;
            return MedicationCard(
              med: med,
              displayNumber: index + 1,
            );
          }),
        ],

        // IV Bags Section
        if (ivBags.isNotEmpty) ...[
          if (regularMeds.isNotEmpty) const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Icon(Icons.local_hospital, color: Colors.red.shade700, size: 20),
                const SizedBox(width: 8),
                Text(
                  'IV Bags (${ivBags.length})',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.red.shade700,
                  ),
                ),
              ],
            ),
          ),
          ...ivBags.asMap().entries.map((entry) {
            final index = entry.key;
            final med = entry.value;
            return MedicationCard(
              med: med,
              displayNumber: regularMeds.length + index + 1,
              isIV: true,
            );
          }),
        ],
      ],
    );
  }
}
