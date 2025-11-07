import 'medication_processor.dart';
import '../models/med_item.dart';

void debugMedicationProcessing(List<MedItem> input, List<MedItem> output) {
  print('\n=== MEDICATION PROCESSING DEBUG ===');
  print('Input: ${input.length} medications');
  for (var med in input) {
    print('  IN: ${med.name} ${med.dose} ${med.form} | Floor: ${med.floor} | Location: ${med.location}');
  }
  
  print('\nOutput: ${output.length} medications');
  for (var med in output) {
    print('  OUT: ${med.name} ${med.dose} ${med.form} | Pick: ${med.pickAmount} | Location: ${med.location}');
    if (med.notes != null) {
      print('       Notes: ${med.notes}');
    }
  }
  print('=== END DEBUG ===\n');
}
