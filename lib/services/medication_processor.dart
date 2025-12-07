import 'package:collection/collection.dart';
import '../models/med_item.dart';
import 'database_service.dart';
import 'location_service.dart';

class MedicationProcessor {
  // IV antibiotics and solutions that should be separated
  static final List<String> _ivMedications = [
    'cefazolin', 'ceftriaxone', 'ampicillin', 'vancomycin', 'piperacillin',
    'meropenem', 'ertapenem', 'ceftazidime', 'cefepime', 'gentamicin',
    'tobramycin', 'azithromycin', 'levofloxacin', 'ciprofloxacin', 'metronidazole',
    'normal saline', 'lactated ringers', 'dextrose', 'sodium chloride'
  ];

  // Check if medication is an IV bag
  static bool _isIVBag(MedItem med) {
    String nameLower = med.name.toLowerCase();
    String formLower = med.form.toLowerCase();

    // Check by form
    if (formLower.contains('iv') || formLower.contains('bag') || formLower.contains('infusion')) {
      return true;
    }

    // Check by medication name
    return _ivMedications.any((ivMed) => nameLower.contains(ivMed));
  }

  static Future<List<MedItem>> processAndOrganizeMedications(List<MedItem> scannedMeds, {bool disableAggregation = false}) async {
    List<MedItem> processedMeds = [];

    print('Processing ${scannedMeds.length} medications... (aggregation: ${!disableAggregation})');

    // Check if medications already have pickLocation from server
    int serverLocationCount = scannedMeds.where((med) =>
      med.pickLocation != null && med.pickLocation != 'UNKNOWN'
    ).length;

    print('✓ ${serverLocationCount}/${scannedMeds.length} medications already have locations from server');

    // For medications WITHOUT server location, do database lookup (legacy CSV fallback)
    List<MedItem> medsNeedingLookup = scannedMeds.where((med) =>
      med.pickLocation == null || med.pickLocation == 'UNKNOWN'
    ).toList();

    Map<MedItem, Map<String, String>?> batchResults = {};
    if (medsNeedingLookup.isNotEmpty) {
      print('Performing database lookup for ${medsNeedingLookup.length} medications without server locations...');
      batchResults = await DatabaseService.batchGetLocationsForMeds(medsNeedingLookup);
      print('Batch lookup complete!');
    }

    // Process each medication
    for (MedItem med in scannedMeds) {
      // If medication already has pickLocation from server, use it directly
      if (med.pickLocation != null && med.pickLocation != 'UNKNOWN') {
        print('✓ Using server location for ${med.name}: ${med.pickLocationDesc}');
        processedMeds.add(med);
        continue;
      }

      // Otherwise, try database lookup (legacy fallback)
      final locationData = batchResults[med];
      String? finalLocation;
      if (locationData != null && locationData['location'] != null && locationData['location'].toString().isNotEmpty) {
        finalLocation = locationData['location'];
      } else {
        // Use LocationService to get general location (Front Top, Back Top, etc.)
        finalLocation = await LocationService.getGeneralLocation(med);
      }

      MedItem updatedMed = med.withLocationAndNotes(
        finalLocation,
        locationData?['notes'],
      );

      processedMeds.add(updatedMed);
    }

    // Step 2: Aggregate medications by type (floor stock vs patient labels)
    List<MedItem> aggregated;
    if (disableAggregation) {
      print('⚠️ AGGREGATION DISABLED - Skipping aggregation step');
      aggregated = processedMeds;
    } else {
      aggregated = _aggregateByType(processedMeds);
    }

    // Step 3: Sort by pick location in user's preferred order:
    // 1. PHRM (Main Pharmacy)
    // 2. IV (Where IVs are)
    // 3. VIT (Vitamins Section)
    // 4. STR (Store Room)
    // 5. UNKNOWN (Location not found)
    aggregated.sort((a, b) {
      int priorityA = _getPickLocationPriority(a.pickLocation);
      int priorityB = _getPickLocationPriority(b.pickLocation);

      if (priorityA != priorityB) {
        return priorityA.compareTo(priorityB);
      }

      // Within same location, sort alphabetically by medication name
      return a.name.compareTo(b.name);
    });

    print('\n✓ Sorted ${aggregated.length} medications by pick location');
    return aggregated;
  }
  
  static List<MedItem> _aggregateByType(List<MedItem> medications) {
    print('\n=== AGGREGATION DEBUG ===');
    print('Input: ${medications.length} medications');
    for (var med in medications) {
      print('  IN: ${med.name} ${med.dose} ${med.form} | Floor: ${med.floor} | Location: ${med.location} | Pick: ${med.pickAmount}');
    }

    // Group by medication ONLY (name-dose-form) WITHOUT location for floor stock aggregation
    // This allows combining medications from different floors into a single entry with breakdown
    Map<String, List<MedItem>> grouped = groupBy(
      medications,
      (med) => '${med.name.toLowerCase()}-${med.dose.toLowerCase()}-${med.form.toLowerCase()}',
    );

    print('\nGrouped into ${grouped.length} groups:');
    for (var entry in grouped.entries) {
      print('  Group "${entry.key}": ${entry.value.length} items');
    }

    List<MedItem> aggregated = [];
    for (var entry in grouped.entries) {
      List<MedItem> sameMeds = entry.value;
      
      // Separate floor stock and patient label meds (mutually exclusive)
      // Floor stock: medications with floor field
      // Patient labels: medications with patient/sig fields BUT NO floor field
      List<MedItem> floorStockMeds = sameMeds.where((med) => med.floor != null).toList();
      List<MedItem> patientLabelMeds = sameMeds.where((med) => (med.patient != null || med.sig != null) && med.floor == null).toList();

      // Process floor stock medications (medications with floor assignments)
      if (floorStockMeds.isNotEmpty) {
        MedItem floorStockAggregated = _aggregateFloorStock(floorStockMeds);
        aggregated.add(floorStockAggregated);
      }

      // Process patient label medications (medications with patient/sig but no floor)
      if (patientLabelMeds.isNotEmpty) {
        MedItem patientLabelAggregated = _aggregatePatientLabels(patientLabelMeds);
        aggregated.add(patientLabelAggregated);
      }
    }

    print('\nOutput: ${aggregated.length} medications');
    for (var med in aggregated) {
      print('  OUT: ${med.name} ${med.dose} ${med.form} | Pick: ${med.pickAmount} | Location: ${med.location}');
      if (med.notes != null) {
        print('       Notes: ${med.notes}');
      }
    }
    print('=== END AGGREGATION DEBUG ===\n');

    return aggregated;
  }
  
  static MedItem _aggregateFloorStock(List<MedItem> floorStockMeds) {
    int totalQty = floorStockMeds.fold(0, (sum, med) => sum + med.pickAmount);

    // Group by floor and create breakdown
    Map<String, int> floorBreakdown = {};
    for (MedItem med in floorStockMeds) {
      String floor = med.floor ?? 'Unknown Floor';
      floorBreakdown[floor] = (floorBreakdown[floor] ?? 0) + med.pickAmount;
    }

    // Use first med as template
    MedItem representative = floorStockMeds.first;

    // Store floor breakdown in a special format that can be parsed by UI
    // Format: "FLOOR_BREAKDOWN: 8E-1=7, 8E-2=4" (machine-readable)
    String floorBreakdownForUI = 'FLOOR_BREAKDOWN: ${floorBreakdown.entries.map((e) => '${e.key}=${e.value}').join(', ')}';

    // Keep original notes separate, append floor breakdown data
    String enhancedNotes = floorBreakdownForUI;
    if (representative.notes != null && representative.notes!.isNotEmpty) {
      enhancedNotes = '${representative.notes}|||$floorBreakdownForUI';
    }

    return representative.copyWith(
      pickAmount: totalQty,
      notes: enhancedNotes,
    );
  }

  static String _getPluralForm(String form) {
    if (form == 'tablet') return 'tablets';
    if (form == 'capsule') return 'capsules';
    if (form == 'bag') return 'bags';
    if (form == 'vial') return 'vials';
    if (form == 'drop') return 'drops';
    if (form == 'solution') return 'solution';
    if (form == 'liquid') return 'liquid';
    return '${form}s';
  }
  
  static MedItem _aggregatePatientLabels(List<MedItem> patientLabelMeds) {
    double totalQty = patientLabelMeds.fold(0.0, (sum, med) => sum + med.calculatedQty);
    
    // Group by patient and create breakdown
    Map<String, double> patientBreakdown = {};
    for (MedItem med in patientLabelMeds) {
      String patient = med.patient ?? 'Unknown Patient';
      patientBreakdown[patient] = (patientBreakdown[patient] ?? 0.0) + med.calculatedQty;
    }
    
    // Create breakdown string
    String breakdown = patientBreakdown.entries
        .map((e) => '${e.value} for ${e.key}')
        .join(', ');
    
    // Use first med as template
    MedItem representative = patientLabelMeds.first;
    String enhancedNotes = '${representative.notes ?? ''} Breakdown: $breakdown'.trim();
    
    return representative.copyWith(
      pickAmount: totalQty.round(),
      notes: enhancedNotes,
      calculatedQty: totalQty,
    );
  }
  
  static int _compareLocations(String locationA, String locationB) {
    try {
      // Determine location types for priority sorting
      int priorityA = _getLocationPriority(locationA);
      int priorityB = _getLocationPriority(locationB);
      
      // Sort by priority first (Front Fridge > Front Shelf > Back Shelf)
      if (priorityA != priorityB) {
        return priorityA.compareTo(priorityB);
      }
      
      // Parse location format: "Front Shelf X, Row Y, Bin Z" or "Front Fridge X, Row Y, Bin Z"
      List<String> partsA = locationA.split(', ');
      List<String> partsB = locationB.split(', ');
      
      if (partsA.length < 3 || partsB.length < 3) return locationA.compareTo(locationB);
      
      // Extract shelf/fridge number
      int shelfA = int.parse(partsA[0].split(' ').last);
      int shelfB = int.parse(partsB[0].split(' ').last);
      
      if (shelfA != shelfB) return shelfA.compareTo(shelfB);
      
      // Extract row number
      int rowA = int.parse(partsA[1].split(' ').last);
      int rowB = int.parse(partsB[1].split(' ').last);
      
      if (rowA != rowB) return rowA.compareTo(rowB); // Top rows first
      
      // Extract bin number
      int binA = int.parse(partsA[2].split(' ').last);
      int binB = int.parse(partsB[2].split(' ').last);
      
      return binA.compareTo(binB); // Left to right
    } catch (e) {
      // Fallback to string comparison if parsing fails
      return locationA.compareTo(locationB);
    }
  }
  
  /// Get priority for pick location sorting
  /// Order: PHRM (1) -> IV (2) -> VIT (3) -> STR (4) -> UNKNOWN (5)
  static int _getPickLocationPriority(String? pickLocation) {
    if (pickLocation == null || pickLocation == 'UNKNOWN') {
      return 5; // Unknown locations last
    }

    switch (pickLocation.toUpperCase()) {
      case 'PHRM':
        return 1; // Main Pharmacy first
      case 'IV':
        return 2; // IVs second
      case 'VIT':
        return 3; // Vitamins third
      case 'STR':
        return 4; // Store Room fourth
      default:
        return 5; // Unknown/unrecognized locations last
    }
  }

  static int _getLocationPriority(String location) {
    if (location.startsWith('Front Fridge')) {
      return 1; // Highest priority - refrigerated items first
    } else if (location.startsWith('Front Shelf')) {
      return 2; // Second priority - front shelves
    } else if (location.startsWith('Back Shelf')) {
      return 3; // Third priority - back shelves
    } else {
      return 4; // Lowest priority - unknown locations
    }
  }
  
  static List<MedItem> simulateScannedMedications({String mode = 'floor_stock'}) {
    if (mode == 'floor_stock') {
      // Simulate floor stock scan with floor assignments including refrigerated medications
      return [
        MedItem(name: 'Gabapentin', dose: '100 mg', form: 'capsule', pickAmount: 3, floor: '6W'),
        MedItem(name: 'Insulin Aspart', dose: '100 unit / mL', form: 'vial', pickAmount: 2, floor: '7E1'), // Front Fridge medication
        MedItem(name: 'Metoprolol Tartrate', dose: '25 mg', form: 'tablet', pickAmount: 2, floor: '7E1'),
        MedItem(name: 'Vancomycin', dose: '1 g', form: 'vial', pickAmount: 1, floor: '6W'), // Front Fridge medication
        MedItem(name: 'Lisinopril', dose: '10 mg', form: 'tablet', pickAmount: 1, floor: '6W'),
        MedItem(name: 'Heparin', dose: '5000 unit / mL', form: 'vial', pickAmount: 1, floor: '8W-1'), // Front Fridge medication
        MedItem(name: 'LEVOTHYROXINE', dose: '50 MCG', form: 'TABLET', pickAmount: 1, floor: '8W-1'),
      ];
    } else {
      // Simulate cart-fill scan with patient and sig data including refrigerated medications and special preparation needs
      return [
        MedItem(name: 'Gabapentin', dose: '100 mg', form: 'capsule', pickAmount: 2, patient: 'Patient A', sig: 'Take 1 tablet by mouth twice daily', floor: '6W', calculatedQty: 2.0),
        MedItem(name: 'Insulin Aspart', dose: '100 unit / mL', form: 'vial', pickAmount: 1, patient: 'Patient B', sig: 'Inject subcutaneously as directed', floor: '7E1', calculatedQty: 1.0),
        MedItem(name: 'Metoprolol Tartrate', dose: '12.5 mg', form: 'half-tablet', pickAmount: 1, patient: 'Patient B', sig: 'Take 0.5 tablet by mouth daily', floor: '7E1', calculatedQty: 0.5),
        MedItem(name: 'Vancomycin', dose: '1 g', form: 'vial', pickAmount: 1, patient: 'Patient A', sig: 'IV infusion as directed', floor: '6W', calculatedQty: 1.0),
        MedItem(name: 'Acetaminophen', dose: '160 mg / 5 mL', form: 'suspension', pickAmount: 1, patient: 'Patient C', sig: 'Take 5mL by mouth every 6 hours', floor: '8W-1', calculatedQty: 1.0),
        MedItem(name: 'Amoxicillin', dose: '125 mg / 5 mL', form: 'suspension', pickAmount: 1, patient: 'Patient A', sig: 'Take 7.5mL by mouth twice daily', floor: '6W', calculatedQty: 1.0),
        MedItem(name: 'predniSONE', dose: '5 mg', form: 'tablet', pickAmount: 1, patient: 'Patient D', sig: 'Take 1.5 tablets by mouth daily', floor: '5W', calculatedQty: 1.5),
        MedItem(name: 'Dextromethorphan', dose: '15 mg / 5 mL', form: 'syrup', pickAmount: 1, patient: 'Patient E', sig: 'Take 10mL by mouth every 4 hours', floor: '4W', calculatedQty: 1.0),
        MedItem(name: 'Acetazolamide', dose: '125 mg', form: 'tablet', pickAmount: 1, patient: 'Patient F', sig: 'Take 0.5 tablet by mouth twice daily', floor: '3W', calculatedQty: 0.5),
        MedItem(name: 'Heparin', dose: '5000 unit / mL', form: 'vial', pickAmount: 1, patient: 'Patient G', sig: 'Inject subcutaneously as directed', floor: '7E1', calculatedQty: 1.0),
        MedItem(name: 'Guaifenesin', dose: '100 mg / 5 mL', form: 'syrup', pickAmount: 1, patient: 'Patient H', sig: 'Take 15mL by mouth every 6 hours', floor: '2W', calculatedQty: 1.0),
        MedItem(name: 'LEVOTHYROXINE', dose: '50 MCG', form: 'TABLET', pickAmount: 1, patient: 'Patient C', sig: 'Take 1 tablet by mouth every morning', floor: '8W-1', calculatedQty: 1.0),
      ];
    }
  }
}
