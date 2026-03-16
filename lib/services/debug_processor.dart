import 'medication_processor.dart';
import '../models/med_item.dart';
import '../utils/app_logger.dart';

void debugMedicationProcessing(List<MedItem> input, List<MedItem> output) {
  AppLogger.info('=== MEDICATION PROCESSING DEBUG ===', name: 'DebugProcessor');
  AppLogger.info('Input: ${input.length} medications', name: 'DebugProcessor');
  for (var med in input) {
    AppLogger.info('  IN: ${med.name} ${med.dose} ${med.form} | Floor: ${med.floor} | Location: ${med.location}', name: 'DebugProcessor');
  }

  AppLogger.info('Output: ${output.length} medications', name: 'DebugProcessor');
  for (var med in output) {
    AppLogger.info('  OUT: ${med.name} ${med.dose} ${med.form} | Pick: ${med.pickAmount} | Location: ${med.location}', name: 'DebugProcessor');
    if (med.notes != null) {
      AppLogger.info('       Notes: ${med.notes}', name: 'DebugProcessor');
    }
  }
  AppLogger.info('=== END DEBUG ===', name: 'DebugProcessor');
}
