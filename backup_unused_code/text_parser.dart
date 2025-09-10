

enum ScanType { floorStock, patientLabel, unknown }

class TextParser {
  // Hardcoded floor list as specified
  static const List<String> validFloors = [
    '10E', '9E', '8E', '8W-1', '8W2', '7W1', '7W2', '6W', 
    '7E1', '7E2', '6W1', '6W2', '6E1', '6E2', 'SICU', 'MICU'
  ];

  static List<Map<String, dynamic>> parseExtractedText(String text) {
    List<Map<String, dynamic>> medications = [];
    
    // Auto-detect scan type
    ScanType scanType = _detectScanType(text);
    print('Detected scan type: $scanType');
    
    // Split text into lines and process each line
    List<String> lines = text.split('\n');
    
    for (String line in lines) {
      line = line.trim();
      if (line.isEmpty) continue;
      
      // Parse based on detected type
      Map<String, dynamic>? medInfo;
      if (scanType == ScanType.floorStock) {
        medInfo = _parseFloorStockLine(line);
      } else if (scanType == ScanType.patientLabel) {
        medInfo = _parsePatientLabelLine(line);
      } else {
        // Try both patterns for unknown type
        medInfo = _parseFloorStockLine(line) ?? _parsePatientLabelLine(line);
      }
      
      if (medInfo != null) {
        medications.add(medInfo);
      }
    }
    
    return medications;
  }
  
  static ScanType _detectScanType(String text) {
    String lowerText = text.toLowerCase();
    
    // Floor stock indicators
    if (lowerText.contains('pick amount') || 
        lowerText.contains('floor') ||
        lowerText.contains('bulk') ||
        _containsFloorReference(text)) {
      return ScanType.floorStock;
    }
    
    // Patient label indicators
    if (lowerText.contains('bid') || 
        lowerText.contains('tid') ||
        lowerText.contains('qid') ||
        lowerText.contains('daily') ||
        lowerText.contains('patient') ||
        lowerText.contains('sig:') ||
        lowerText.contains('take ')) {
      return ScanType.patientLabel;
    }
    
    return ScanType.unknown;
  }
  
  static bool _containsFloorReference(String text) {
    for (String floor in validFloors) {
      if (text.contains(floor)) return true;
    }
    return false;
  }
  
  static Map<String, dynamic>? _parseFloorStockLine(String line) {
    // Remove extra whitespace and normalize
    line = line.replaceAll(RegExp(r'\s+'), ' ').trim();
    
    // Extract floor information
    String? floor = _extractFloor(line);
    
    // Try different parsing patterns for floor stock
    Map<String, dynamic>? result;
    
    // Pattern 1: Name Dose Form - Pick Amount for Floor
    result = _tryFloorPattern1(line, floor);
    if (result != null) return result;
    
    // Pattern 2: Tabular format with commas
    result = _tryFloorPattern2(line, floor);
    if (result != null) return result;
    
    // Pattern 3: Simple format
    result = _tryFloorPattern3(line, floor);
    if (result != null) return result;
    
    return null;
  }
  
  static Map<String, dynamic>? _parsePatientLabelLine(String line) {
    // Remove extra whitespace and normalize
    line = line.replaceAll(RegExp(r'\s+'), ' ').trim();
    
    // Extract patient and sig information
    String? patient = _extractPatient(line);
    String? sig = _extractSig(line);
    
    // Try different parsing patterns for patient labels
    Map<String, dynamic>? result;
    
    // Pattern 1: Med Dose Form, sig
    result = _tryLabelPattern1(line, patient, sig);
    if (result != null) return result;
    
    // Pattern 2: Med Dose Form sig
    result = _tryLabelPattern2(line, patient, sig);
    if (result != null) return result;
    
    return null;
  }
  
  static String? _extractFloor(String line) {
    // Look for floor patterns like "6W", "7E1", "SICU", etc.
    for (String floor in validFloors) {
      if (line.contains(floor)) {
        return floor;
      }
    }
    
    // Also try regex patterns for floors
    RegExp floorPattern = RegExp(r'\b(\d+[EW]\d*)\b');
    Match? match = floorPattern.firstMatch(line);
    if (match != null) {
      return match.group(1);
    }
    
    return null;
  }
  
  static String? _extractPatient(String line) {
    // Look for patient patterns
    RegExp patientPattern = RegExp(r'(?:for\s+)?(?:patient\s+)?([A-Z]\w*)', caseSensitive: false);
    Match? match = patientPattern.firstMatch(line);
    if (match != null) {
      return 'Patient ${match.group(1)}';
    }
    
    return null;
  }
  
  static String? _extractSig(String line) {
    String lowerLine = line.toLowerCase();
    
    // Common sig patterns
    List<String> sigPatterns = [
      'bid', 'tid', 'qid', 'qd', 'qhs', 'daily', 'twice daily', 'three times daily',
      'four times daily', 'once daily', 'at bedtime', 'bedtime', 'prn', 'as needed',
      'q6h', 'q8h', 'q12h', 'every 6 hours', 'every 8 hours', 'every 12 hours'
    ];
    
    for (String pattern in sigPatterns) {
      if (lowerLine.contains(pattern)) {
        return pattern;
      }
    }
    
    // Look for "take X" patterns
    RegExp takePattern = RegExp(r'take\s+\d+.*?(?:daily|times|tablet|capsule)', caseSensitive: false);
    Match? match = takePattern.firstMatch(line);
    if (match != null) {
      return match.group(0);
    }
    
    return null;
  }
  
  static Map<String, dynamic>? _tryFloorPattern1(String line, String? floor) {
    // Pattern: "Gabapentin 100mg capsule - Pick 5 for 6W"
    RegExp pattern = RegExp(r'^(.+?)\s+(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+([a-zA-Z]+)\s*-?\s*(?:Pick\s+)?(\d+)');
    Match? match = pattern.firstMatch(line);
    
    if (match != null) {
      return {
        'name': match.group(1)?.trim() ?? '',
        'dose': '${match.group(2)} ${match.group(3)}',
        'form': match.group(4) ?? '',
        'pick_amount': int.tryParse(match.group(5) ?? '0') ?? 0,
        'floor': floor,
      };
    }
    
    return null;
  }
  
  static Map<String, dynamic>? _tryFloorPattern2(String line, String? floor) {
    // Pattern: "Medication, 25mg, tablet, 3, 6W"
    List<String> parts = line.split(',');
    if (parts.length >= 4) {
      String name = parts[0].trim();
      String dose = parts[1].trim();
      String form = parts[2].trim();
      int amount = int.tryParse(parts[3].trim()) ?? 0;
      
      if (name.isNotEmpty && dose.isNotEmpty && form.isNotEmpty && amount > 0) {
        return {
          'name': name,
          'dose': dose,
          'form': form,
          'pick_amount': amount,
          'floor': floor,
        };
      }
    }
    
    return null;
  }
  
  static Map<String, dynamic>? _tryFloorPattern3(String line, String? floor) {
    // Pattern: "Medication 25mg tablet 3"
    RegExp pattern = RegExp(r'^(.+?)\s+(\d+(?:\.\d+)?[a-zA-Z]+)\s+([a-zA-Z]+)\s+(\d+)');
    Match? match = pattern.firstMatch(line);
    
    if (match != null) {
      return {
        'name': match.group(1)?.trim() ?? '',
        'dose': match.group(2) ?? '',
        'form': match.group(3) ?? '',
        'pick_amount': int.tryParse(match.group(4) ?? '0') ?? 0,
        'floor': floor,
      };
    }
    
    return null;
  }
  
  static Map<String, dynamic>? _tryLabelPattern1(String line, String? patient, String? sig) {
    // Pattern: "Gabapentin 100mg capsule, bid"
    RegExp pattern = RegExp(r'^(.+?)\s+(\d+(?:\.\d+)?[a-zA-Z]+)\s+([a-zA-Z]+)(?:,\s*(.+))?');
    Match? match = pattern.firstMatch(line);
    
    if (match != null) {
      String extractedSig = sig ?? match.group(4) ?? '';
      int calculatedQty = _calculateFromSig(extractedSig);
      
      return {
        'name': match.group(1)?.trim() ?? '',
        'dose': match.group(2) ?? '',
        'form': match.group(3) ?? '',
        'pick_amount': calculatedQty,
        'patient': patient,
        'sig': extractedSig,
        'calculated_qty': calculatedQty,
      };
    }
    
    return null;
  }
  
  static Map<String, dynamic>? _tryLabelPattern2(String line, String? patient, String? sig) {
    // Pattern: "Gabapentin 100mg capsule bid"
    RegExp pattern = RegExp(r'^(.+?)\s+(\d+(?:\.\d+)?[a-zA-Z]+)\s+([a-zA-Z]+)\s+(.+)');
    Match? match = pattern.firstMatch(line);
    
    if (match != null) {
      String extractedSig = sig ?? match.group(4) ?? '';
      int calculatedQty = _calculateFromSig(extractedSig);
      
      return {
        'name': match.group(1)?.trim() ?? '',
        'dose': match.group(2) ?? '',
        'form': match.group(3) ?? '',
        'pick_amount': calculatedQty,
        'patient': patient,
        'sig': extractedSig,
        'calculated_qty': calculatedQty,
      };
    }
    
    return null;
  }

  static int _calculateFromSig(String? sig) {
    if (sig == null || sig.isEmpty) return 1;
    
    String sigLower = sig.toLowerCase();
    
    // Common dosing frequency patterns
    if (sigLower.contains('bid') || sigLower.contains('twice daily') || sigLower.contains('twice a day')) return 2;
    if (sigLower.contains('tid') || sigLower.contains('three times daily') || sigLower.contains('three times a day')) return 3;
    if (sigLower.contains('qid') || sigLower.contains('four times daily') || sigLower.contains('four times a day')) return 4;
    if (sigLower.contains('q6h') || sigLower.contains('every 6 hours')) return 4;
    if (sigLower.contains('q8h') || sigLower.contains('every 8 hours')) return 3;
    if (sigLower.contains('q12h') || sigLower.contains('every 12 hours')) return 2;
    if (sigLower.contains('qd') || sigLower.contains('daily') || sigLower.contains('once daily') || sigLower.contains('once a day')) return 1;
    if (sigLower.contains('qhs') || sigLower.contains('bedtime') || sigLower.contains('at bedtime')) return 1;
    if (sigLower.contains('prn') || sigLower.contains('as needed')) return 1;
    
    // Default to 1 if no pattern matches
    return 1;
  }
}
