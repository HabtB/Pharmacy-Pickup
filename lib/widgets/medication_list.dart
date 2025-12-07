import 'package:flutter/material.dart';
import '../models/med_item.dart';
import 'medication_card.dart';

class MedicationList extends StatelessWidget {
  final List<MedItem> medications;

  const MedicationList({
    super.key,
    required this.medications,
  });

  // Helper function to check if medication is a Fridge item
  bool _isFridge(MedItem med) {
    return med.pickLocation == 'FRIDGE';
  }

  // Helper function to check if medication is an IV bag
  bool _isIVBag(MedItem med) {
    if (_isFridge(med)) return false; // Fridge takes precedence

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
    // 1. Separate items into groups
    final fridgeMeds = medications.where((med) => _isFridge(med)).toList();
    final ivBags = medications.where((med) => _isIVBag(med)).toList();
    final regularMeds = medications.where((med) => !_isFridge(med) && !_isIVBag(med)).toList();

    // 2. Sort alpabetically
    fridgeMeds.sort((a, b) => a.name.compareTo(b.name));
    ivBags.sort((a, b) => a.name.compareTo(b.name));
    regularMeds.sort((a, b) => a.name.compareTo(b.name));

    return ListView(
      children: [
        // Regular Medications Section (First)
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

        // Fridge Section (Second - "End of Pharmacy items before IV")
        if (fridgeMeds.isNotEmpty) ...[
          if (regularMeds.isNotEmpty) const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Icon(Icons.ac_unit, color: Colors.cyan.shade700, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Refrigerated Items (${fridgeMeds.length})',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.cyan.shade900, 
                  ),
                ),
              ],
            ),
          ),
          ...fridgeMeds.asMap().entries.map((entry) {
            final index = entry.key;
            final med = entry.value;
            return MedicationCard(
              med: med,
              displayNumber: regularMeds.length + index + 1,
              isFridge: true,
            );
          }),
        ],

        // IV Bags Section (Last)
        if (ivBags.isNotEmpty) ...[
          if (regularMeds.isNotEmpty || fridgeMeds.isNotEmpty) const SizedBox(height: 16),
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
              displayNumber: regularMeds.length + fridgeMeds.length + index + 1,
              isIV: true,
            );
          }),
        ],
      ],
    );
  }
}
