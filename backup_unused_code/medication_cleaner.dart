import '../models/med_item.dart';

class MedicationCleaner {
  static List<MedItem> cleanParsedMeds(List<Map<String, dynamic>> parsed) {
    List<MedItem> cleaned = [];
    for (var med in parsed) {
      // Normalize name: Capitalize words, insert spaces for glued camelCase
      String name = med['name'].toString()
          .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (match) => '${match[1]} ${match[2]}')
          .split(' ')
          .map((word) => _capitalize(word))
          .join(' ');
      
      // OCR fixes
      name = name.replaceAll('O', '0').replaceAll('l', 'I');

      // Dose: Remove spaces, standardize units, fix OCR errors
      String dose = med['dose'].toString()
          .trim()
          .replaceAll(' ', '')
          .toLowerCase()
          .replaceAll('\$', '5')  // OCR error: $ → 5
          .replaceAll('s', '5')   // OCR error: s → 5 in numbers
          .replaceAll('o', '0')   // OCR error: o → 0
          .replaceAll('l', '1')   // OCR error: l → 1
          .replaceAll('mcg', 'mcg')
          .replaceAll('mg', 'mg');

      // Form: Standardize common variations
      String form = med['form'].toString().toLowerCase();
      if (form.contains('capsul')) form = 'capsule';
      if (form.contains('tab')) form = 'tablet';
      if (form == 'susp') form = 'suspension';

      int pick = med['pick_amount'] as int? ?? med['pickAmount'] as int? ?? 0;

      cleaned.add(MedItem(name: name, dose: dose, form: form, pickAmount: pick));
    }
    return cleaned;
  }

  static String _capitalize(String word) {
    if (word.isEmpty) return word;
    return word[0].toUpperCase() + word.substring(1).toLowerCase();
  }

  // Enhanced cleaning for existing MedItem objects
  static MedItem cleanMedItem(MedItem med) {
    // Normalize name: Handle camelCase and common OCR errors
    String cleanName = med.name
        .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (match) => '${match[1]} ${match[2]}')
        .split(' ')
        .map((word) => _capitalize(word))
        .join(' ');
    
    // Common OCR fixes
    cleanName = cleanName
        .replaceAll('O', '0')
        .replaceAll('l', 'I')
        .replaceAll('rn', 'm')  // Common OCR error
        .replaceAll('cl', 'd');  // Common OCR error

    // Normalize dose format and fix OCR errors
    String cleanDose = med.dose
        .replaceAll(' ', '')
        .toLowerCase()
        .replaceAll('\$', '5')  // OCR error: $ → 5
        .replaceAll('s', '5')   // OCR error: s → 5 in numbers
        .replaceAll('o', '0')   // OCR error: o → 0
        .replaceAll('l', '1')   // OCR error: l → 1
        .replaceAll(RegExp(r'(\d+)mg'), r'$1 mg')
        .replaceAll(RegExp(r'(\d+)mcg'), r'$1 mcg')
        .replaceAll(RegExp(r'(\d+)g'), r'$1 g');

    // Normalize form
    String cleanForm = med.form.toLowerCase().trim();
    Map<String, String> formMappings = {
      'tab': 'tablet',
      'tabs': 'tablet',
      'cap': 'capsule',
      'caps': 'capsule',
      'capsul': 'capsule',
      'susp': 'suspension',
      'sol': 'solution',
      'inj': 'injection',
      'cr': 'controlled release',
      'er': 'extended release',
      'xl': 'extended release',
      'sr': 'sustained release',
    };

    for (String key in formMappings.keys) {
      if (cleanForm.contains(key)) {
        cleanForm = formMappings[key]!;
        break;
      }
    }

    return MedItem(
      name: cleanName,
      dose: cleanDose,
      form: cleanForm,
      pickAmount: med.pickAmount,
      location: med.location,
      notes: med.notes,
    );
  }
}
