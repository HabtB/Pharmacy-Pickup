import 'package:flutter/services.dart' show rootBundle;
import 'package:csv/csv.dart';
import '../models/med_item.dart';

/// Service for determining medication storage locations in the pharmacy
/// Uses hierarchical location system: General Location + Specific Location
class LocationService {
  // General location constants (for picking route organization)
  static const String frontTop = 'Front Top';
  static const String frontBottom = 'Front Bottom';
  static const String backTop = 'Back Top';
  static const String backBottom = 'Back Bottom';
  static const String frontFridge = 'Front Fridge';
  static const String ivSection = 'IV Section';
  static const String vitaminSection = 'Vitamin & Others Section';
  static const String storeAToParSection = 'Store A-Par Section';
  static const String storePhToZSection = 'Store Ph-Z Section';
  static const String storeVialsSection = 'Store-Vials Section';
  static const String storeNonFormularySection = 'Store-NonFormulary Section';
  static const String storeAntineoplasticsSection = 'Store-Antineoplastics Section';
  static const String storeOintmentsPatchesEyeSection = 'Store-Ointments/Patches/Eye';
  static const String storeOralsSection = 'Store-Orals Section';
  static const String unknownLocation = 'Unknown Location - Check Manually';
  static const String locationNotAssigned = 'Location Not Assigned';

  // Cache for loaded medication locations
  static Map<String, Map<String, dynamic>>? _locationCache;

  /// Load medication locations from CSV file
  static Future<void> loadLocations() async {
    if (_locationCache != null) return; // Already loaded

    try {
      final csvString = await rootBundle.loadString('assets/med_locations.csv');
      final List<List<dynamic>> csvTable = const CsvToListConverter().convert(csvString);

      _locationCache = {};

      // Skip header row (index 0)
      for (int i = 1; i < csvTable.length; i++) {
        final row = csvTable[i];
        if (row.length >= 5) {
          final name = row[0].toString().toLowerCase().trim();
          final dose = row[1].toString().trim();
          final form = row[2].toString().toLowerCase().trim();
          final generalLocation = row[3].toString().trim();
          final specificLocation = row[4].toString().trim();
          final notes = row.length > 5 ? row[5].toString().trim() : '';

          // Create keys for lookup: name|dose (specific) and name (general)
          final specificKey = '$name|$dose';

          _locationCache![specificKey] = {
            'general_location': generalLocation,
            'specific_location': specificLocation,
            'form': form,
            'notes': notes,
          };

          // Also store with just name for fallback lookup
          if (!_locationCache!.containsKey(name)) {
            _locationCache![name] = {
              'general_location': generalLocation,
              'specific_location': specificLocation,
              'form': form,
              'notes': notes,
            };
          }
        }
      }

      print('✓ Loaded ${_locationCache!.length} medication locations from CSV');
    } catch (e) {
      print('Error loading medication locations: $e');
      _locationCache = {}; // Empty cache on error
    }
  }

  /// Look up general location from CSV (for picking route)
  static Future<String> getGeneralLocation(MedItem medication) async {
    await loadLocations();

    final location = _lookupFromCache(medication.name, medication.dose);
    // If no exact match found in CSV, return "Location Not Assigned" instead of inferring
    // This prevents incorrect location assignments from partial matches
    return location?['general_location'] ?? locationNotAssigned;
  }

  /// Look up specific location from CSV (exact bin location)
  static Future<String> getSpecificLocation(MedItem medication) async {
    await loadLocations();

    final location = _lookupFromCache(medication.name, medication.dose);
    return location?['specific_location'] ?? unknownLocation;
  }

  /// Main method to determine medication location (returns general location)
  static Future<String> determineLocation(MedItem medication) async {
    return await getGeneralLocation(medication);
  }

  /// Internal lookup from cache
  static Map<String, dynamic>? _lookupFromCache(String medicationName, String? dose) {
    if (_locationCache == null) return null;

    final nameLower = medicationName.toLowerCase().trim();

    // Try exact match with name|dose first
    if (dose != null && dose.isNotEmpty) {
      final keyWithDose = '$nameLower|$dose';
      if (_locationCache!.containsKey(keyWithDose)) {
        return _locationCache![keyWithDose];
      }
    }

    // Try name only
    if (_locationCache!.containsKey(nameLower)) {
      return _locationCache![nameLower];
    }

    // REMOVED: Partial match logic - it was causing incorrect location assignments
    // (e.g., acetaminophen tablet matching acetaminophen suspension in fridge)
    // If no exact match found, return null to show "Location Not Assigned"

    return null;
  }

  /// Infer general location based on medication properties (fallback)
  static String _inferGeneralLocation(MedItem medication) {
    final name = medication.name.toLowerCase();
    final form = medication.form.toLowerCase();
    final dose = medication.dose.toLowerCase();

    // 1. Refrigerated items
    if (form.contains('vial') || form.contains('susp') || form.contains('neb')) {
      return frontFridge;
    }

    // 2. IV Section - IV bags and infusions
    if (_isIVMedication(form, dose)) {
      return ivSection;
    }

    // 3. Vials Section
    if (_isVial(form)) {
      return storeVialsSection;
    }

    // 4. Ointments/Patches/Eye Section
    if (_isTopicalMedication(form)) {
      return storeOintmentsPatchesEyeSection;
    }

    // 5. Antineoplastics Section (chemotherapy drugs)
    if (_isAntineoplastic(name)) {
      return storeAntineoplasticsSection;
    }

    // 6. Vitamin & Others Section
    if (_isVitamin(name)) {
      return vitaminSection;
    }

    // 7. Non-Formulary Section
    if (_isNonFormulary(name)) {
      return storeNonFormularySection;
    }

    // 8. Oral liquids
    if (_isOralLiquid(form)) {
      return storeOralsSection;
    }

    // 9. Tablets/Capsules - try to determine Front vs Back vs Store
    if (_isTabletOrCapsule(form)) {
      return _inferTabletLocation(name);
    }

    // Default: Unknown location
    return unknownLocation;
  }

  /// Infer tablet location alphabetically (fallback when not in CSV)
  static String _inferTabletLocation(String name) {
    final firstLetter = name.trim().toLowerCase()[0];

    // Rough estimation: A-M typically in Front, N-Z in Back
    if (firstLetter.codeUnitAt(0) >= 'a'.codeUnitAt(0) &&
        firstLetter.codeUnitAt(0) <= 'm'.codeUnitAt(0)) {
      return frontTop;
    } else {
      return backTop;
    }
  }

  /// Check if medication is IV
  static bool _isIVMedication(String form, String dose) {
    // Check form
    if (form.contains('bag') ||
        form.contains('iv') ||
        form.contains('infusion') ||
        form.contains('ivpb') ||
        form.contains('piggyback')) {
      return true;
    }

    // Check dose description
    if (dose.contains('bag') || dose.contains('ivpb') || dose.contains('infusion')) {
      return true;
    }

    return false;
  }

  /// Check if medication is a vial
  static bool _isVial(String form) {
    return form.contains('vial') || form.contains('injection');
  }

  /// Check if vial should be in back bottom shelf (exceptions)
  static bool _isBackBottomVial(String name) {
    // Add specific medications that are vials but stored in back-bottom
    // We'll populate this as you specify
    final backBottomVials = <String>[
      // Examples (to be updated):
      // 'heparin',
      // 'insulin',
    ];

    return backBottomVials.any((med) => name.contains(med));
  }

  /// Check if medication is topical (ointment, patch, eye drops, etc.)
  static bool _isTopicalMedication(String form) {
    return form.contains('ointment') ||
        form.contains('cream') ||
        form.contains('gel') ||
        form.contains('patch') ||
        form.contains('eye') ||
        form.contains('ophthalmic') ||
        form.contains('drops') ||
        form.contains('topical');
  }

  /// Check if medication is antineoplastic (chemotherapy)
  static bool _isAntineoplastic(String name) {
    final antineoplastics = <String>[
      'methotrexate',
      'cyclophosphamide',
      'fluorouracil',
      '5-fu',
      'doxorubicin',
      'cisplatin',
      'carboplatin',
      'paclitaxel',
      'docetaxel',
      'vincristine',
      'vinblastine',
      'irinotecan',
      'oxaliplatin',
      'gemcitabine',
      'capecitabine',
      'temozolomide',
      'imatinib',
      'erlotinib',
      'rituximab',
      'trastuzumab',
      'bevacizumab',
    ];

    return antineoplastics.any((drug) => name.contains(drug));
  }

  /// Check if medication is a vitamin
  static bool _isVitamin(String name) {
    final vitamins = <String>[
      'vitamin',
      'multivitamin',
      'thiamine',
      'riboflavin',
      'niacin',
      'pyridoxine',
      'cyanocobalamin',
      'folic acid',
      'folate',
      'ascorbic acid',
      'vitamin a',
      'vitamin b',
      'vitamin c',
      'vitamin d',
      'vitamin e',
      'vitamin k',
      'b12',
      'b6',
      'b1',
      'calcium',
      'magnesium',
      'zinc',
      'iron',
      'ferrous',
    ];

    return vitamins.any((vit) => name.contains(vit));
  }

  /// Check if medication is non-formulary (uncommon/specialty)
  static bool _isNonFormulary(String name) {
    // This will be populated with specific non-formulary medications
    // For now, return false - we'll add as you specify
    final nonFormulary = <String>[
      // Add specific non-formulary medications here
    ];

    return nonFormulary.any((med) => name.contains(med));
  }

  /// Check if medication is oral liquid
  static bool _isOralLiquid(String form) {
    return form.contains('suspension') ||
        form.contains('syrup') ||
        form.contains('solution') ||
        form.contains('liquid') ||
        form.contains('elixir') ||
        form.contains('oral') && (form.contains('susp') || form.contains('soln'));
  }

  /// Check if medication is tablet or capsule
  static bool _isTabletOrCapsule(String form) {
    return form.contains('tablet') ||
        form.contains('capsule') ||
        form.contains('tab') ||
        form.contains('cap');
  }

  /// Batch process medications to assign locations (async)
  static Future<List<MedItem>> assignLocations(List<MedItem> medications) async {
    final List<MedItem> result = [];

    for (var med in medications) {
      if (med.location == null || med.location!.isEmpty) {
        final location = await determineLocation(med);
        result.add(MedItem(
          name: med.name,
          dose: med.dose,
          form: med.form,
          pickAmount: med.pickAmount,
          location: location,
          notes: med.notes,
          patient: med.patient,
          floor: med.floor,
          sig: med.sig,
          calculatedQty: med.calculatedQty,
          admin: med.admin,
        ));
      } else {
        result.add(med);
      }
    }

    return result;
  }

  /// Get all available storage sections
  static List<String> getAllSections() {
    return [
      frontTop,
      frontBottom,
      backTop,
      backBottom,
      ivSection,
      vitaminSection,
      storeAToParSection,
      storePhToZSection,
      storeVialsSection,
      storeNonFormularySection,
      storeAntineoplasticsSection,
      storeOintmentsPatchesEyeSection,
      storeOralsSection,
    ];
  }

  /// Group medications by location for efficient picking
  static Map<String, List<MedItem>> groupByLocation(List<MedItem> medications) {
    final Map<String, List<MedItem>> grouped = {};

    for (var med in medications) {
      final location = med.location ?? unknownLocation;
      grouped.putIfAbsent(location, () => []).add(med);
    }

    return grouped;
  }

  /// Get pick order for locations (optimized path through pharmacy)
  static List<String> getOptimizedPickOrder() {
    return [
      frontTop,
      frontBottom,
      backTop,
      backBottom,
      ivSection,
      storeAToParSection,
      storePhToZSection,
      storeVialsSection,
      storeOralsSection,
      vitaminSection,
      storeOintmentsPatchesEyeSection,
      storeAntineoplasticsSection,
      storeNonFormularySection,
      unknownLocation,
    ];
  }

  /// Sort medications by optimized pick order
  static List<MedItem> sortByPickOrder(List<MedItem> medications) {
    final pickOrder = getOptimizedPickOrder();

    medications.sort((a, b) {
      final aLocation = a.location ?? unknownLocation;
      final bLocation = b.location ?? unknownLocation;

      final aIndex = pickOrder.indexOf(aLocation);
      final bIndex = pickOrder.indexOf(bLocation);

      // If location not in pick order, put at end
      final aOrder = aIndex == -1 ? 999 : aIndex;
      final bOrder = bIndex == -1 ? 999 : bIndex;

      return aOrder.compareTo(bOrder);
    });

    return medications;
  }
}
