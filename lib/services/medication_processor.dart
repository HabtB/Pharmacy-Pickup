import 'package:collection/collection.dart';
import '../models/med_item.dart';
import 'database_service.dart';

class MedicationProcessor {
  static Future<List<MedItem>> processAndOrganizeMedications(List<MedItem> scannedMeds) async {
    List<MedItem> processedMeds = [];
    
    // Step 1: Clean and match medications with database locations
    for (MedItem med in scannedMeds) {
      // Use the medication directly for matching
      MedItem cleanedMed = med;
      
      final locationData = await DatabaseService.getLocationAndNotesForMed(cleanedMed);
      
      MedItem updatedMed = cleanedMed.withLocationAndNotes(
        locationData?['location'],
        locationData?['notes'],
      );
      
      processedMeds.add(updatedMed);
    }
    
    // Step 2: Aggregate medications by type (floor stock vs patient labels)
    List<MedItem> aggregated = _aggregateByType(processedMeds);
    
    // Step 3: Sort by location for efficient picking
    aggregated.sort((a, b) {
      // Sort by location if available, otherwise by name
      if (a.location != null && b.location != null) {
        return _compareLocations(a.location!, b.location!);
      } else if (a.location != null) {
        return -1; // Items with location come first
      } else if (b.location != null) {
        return 1;
      } else {
        return a.name.compareTo(b.name); // Fallback to name sorting
      }
    });
    
    return aggregated;
  }
  
  static List<MedItem> _aggregateByType(List<MedItem> medications) {
    // Group by medication + location for aggregation
    Map<String, List<MedItem>> grouped = groupBy(
      medications,
      (med) => '${med.name.toLowerCase()}-${med.dose.toLowerCase()}-${med.form.toLowerCase()}-${med.location ?? 'no-location'}',
    );
    
    List<MedItem> aggregated = [];
    for (var entry in grouped.entries) {
      List<MedItem> sameMeds = entry.value;
      
      // Separate floor stock and patient label meds
      List<MedItem> floorStockMeds = sameMeds.where((med) => med.floor != null).toList();
      List<MedItem> patientLabelMeds = sameMeds.where((med) => med.patient != null || med.sig != null).toList();
      List<MedItem> regularMeds = sameMeds.where((med) => med.floor == null && med.patient == null && med.sig == null).toList();
      
      // Process floor stock medications
      if (floorStockMeds.isNotEmpty) {
        MedItem floorStockAggregated = _aggregateFloorStock(floorStockMeds);
        aggregated.add(floorStockAggregated);
      }
      
      // Process patient label medications
      if (patientLabelMeds.isNotEmpty) {
        MedItem patientLabelAggregated = _aggregatePatientLabels(patientLabelMeds);
        aggregated.add(patientLabelAggregated);
      }
      
      // Process regular medications (legacy support)
      if (regularMeds.isNotEmpty) {
        int totalAmount = regularMeds.fold(0, (sum, med) => sum + med.pickAmount);
        MedItem representative = regularMeds.first.copyWith(pickAmount: totalAmount);
        aggregated.add(representative);
      }
    }
    
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
    
    // Create breakdown string
    String breakdown = floorBreakdown.entries
        .map((e) => '${e.value} for ${e.key}')
        .join(', ');
    
    // Use first med as template
    MedItem representative = floorStockMeds.first;
    String enhancedNotes = '${representative.notes ?? ''} Breakdown: $breakdown'.trim();
    
    return representative.copyWith(
      pickAmount: totalQty,
      notes: enhancedNotes,
    );
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
