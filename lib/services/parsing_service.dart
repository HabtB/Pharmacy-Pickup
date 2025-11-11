import 'dart:convert';
import 'package:http/http.dart' as http;

/// Enhanced parsing with hybrid/// Parse text using LLM (Grok API)
Future<List<Map<String, dynamic>>> parseWithLLM(String text, String apiKey) async {
  // Allow LLM to process any text, even short text like numbers
  
  final response = await http.post(
    Uri.parse('https://api.x.ai/v1/chat/completions'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $apiKey',
    },
    body: jsonEncode({
      'model': 'grok-4',
      'messages': [
        {'role': 'system', 'content': 'You are a pharmacy document parser. Extract medication details and return ONLY valid JSON. No explanations, no markdown, just JSON.'},
        {'role': 'user', 'content': 'Extract medication name (e.g., oxybutynin), brand (e.g., DITROPAN XL), strength (e.g., 5 mg), type/form (e.g., extended release tablet), dose/sig (e.g., BEDTIME), patient (e.g., Polanco, Milena), floor if present, MRN, prescription, order from: $text. JSON: {"name":, "brand":, "strength":, "type":, "dose":, "patient":, "floor":, "mrn":, "rx_number":, "order_number":}\n\nPharmacy Text:\n$text\n\nJSON:'},
      ],
    }),
  );

  print('HTTP Status Code: ${response.statusCode}');
  print('Response Headers: ${response.headers}');
  print('Response Body: ${response.body}');

  if (response.statusCode == 200) {
    try {
      var responseBody = jsonDecode(response.body);
      print('Parsed response body: $responseBody');
      
      if (responseBody['choices'] != null && responseBody['choices'].isNotEmpty) {
        var content = responseBody['choices'][0]['message']['content'];
        print('Raw LLM content: "$content"');
        
        // Clean the content - remove markdown code blocks if present
        var cleanContent = content.toString().trim();
        if (cleanContent.startsWith('```json')) {
          cleanContent = cleanContent.replaceFirst('```json', '').replaceFirst('```', '').trim();
        } else if (cleanContent.startsWith('```')) {
          cleanContent = cleanContent.replaceFirst('```', '').replaceFirst('```', '').trim();
        }
        
        print('Cleaned content: "$cleanContent"');
        
        if (cleanContent.isNotEmpty && cleanContent != 'null') {
          var result = jsonDecode(cleanContent);
          print('Final parsed result: $result');
          
          // Validate that we have at least some meaningful data (not all null/empty)
          if (result is Map) {
            var hasData = result.values.any((value) => 
              value != null && 
              value.toString().trim().isNotEmpty && 
              value.toString().trim().toLowerCase() != 'null'
            );
            if (hasData) {
              print('LLM extraction successful with data: $result');
              return [Map<String, dynamic>.from(result)];
            } else {
              print('LLM returned all null/empty fields, treating as no result: $result');
              return [];
            }
          } else {
            print('LLM result is not a Map: $result');
            return [];
          }
        } else {
          print('LLM returned empty or null content');
          return [];
        }
      } else {
        print('No choices in LLM response');
        return [];
      }
    } catch (e) {
      print('Error parsing LLM response: $e');
      return [];
    }
  } else {
    print('LLM API call failed with status ${response.statusCode}');
    return [];
  }
}

/// Hybrid parsing function with regex first, LLM fallback
Future<List<Map<String, dynamic>>> parseExtractedText(String text, String mode, String? apiKey) async {
  try {
    print('=== PARSING SERVICE: Starting parsing ===');
    print('Input text length: ${text.length}');
    print('Mode: $mode');
    print('API Key available: ${apiKey != null && apiKey.isNotEmpty}');
    print('First 300 chars of text: ${text.substring(0, text.length > 300 ? 300 : text.length)}');
    
    // First try regex parsing
    List<Map<String, dynamic>> regexResults = _parseWithRegex(text, mode);
    
    if (regexResults.isNotEmpty) {
      print('SUCCESS: Regex parsing found ${regexResults.length} medications');
      for (var med in regexResults) {
        print('  - ${med['name']} | ${med['strength']} | ${med['form']}');
      }
      return regexResults;
    }
    
    print('WARNING: Regex parsing found 0 medications');
    
    // If regex fails and API key is available, try LLM parsing
    if (apiKey != null && apiKey.isNotEmpty) {
      print('Attempting LLM parsing with Grok API...');
      var llmResults = await parseWithLLM(text, apiKey);
      if (llmResults.isNotEmpty) {
        print('SUCCESS: LLM parsing found ${llmResults.length} medications');
      } else {
        print('ERROR: LLM parsing also returned 0 medications');
      }
      return llmResults;
    }
    
    print('ERROR: No API key available for LLM fallback');
    return [];
  } catch (e, stackTrace) {
    print('ERROR in parseExtractedText: $e');
    print('Stack trace: $stackTrace');
    return [];
  }
}

List<Map<String, dynamic>> _parseWithRegex(String text, String mode) {
  print('=== REGEX PARSING: Mode $mode ===');
  List<Map<String, dynamic>> medications = [];
  
  // Split text into lines and process each
  List<String> lines = text.split('\n');
  print('Processing ${lines.length} lines...');
  
  int lineNum = 0;
  for (String line in lines) {
    lineNum++;
    line = line.trim();
    if (line.isEmpty) continue;
    
    print('Line $lineNum: "$line"');
    
    // Try to parse medication from line
    Map<String, dynamic>? parsed = _parseMedicationLine(line, mode);
    if (parsed != null && parsed['name'] != null) {
      medications.add(parsed);
      print('  ✓ Parsed: ${parsed['name']} | ${parsed['strength']} | ${parsed['form']}');
    } else {
      print('  ✗ No medication found in this line');
    }
  }
  
  print('Regex parsing complete: ${medications.length} medications found');
  return medications;
}

/// Parse a single medication line
Map<String, dynamic>? _parseMedicationLine(String line, String mode) {
  // Exclude common non-medication terms
  final List<String> excludeTerms = [
    'dose', 'admin', 'medication', 'patient', 'pharmacy', 'mount', 'sinai',
    'morningside', 'hospital', 'lot', 'expiration', 'take', 'bedtime',
    'direction', 'sig', 'quantity', 'refill', 'doctor', 'prescriber',
    'prescription', 'label', 'room', 'bed', 'floor', 'unit', 'daily',
    'description', 'name', 'number', 'amount'
  ];
  
  // Enhanced regex patterns for medication parsing
  List<RegExp> patterns = [
    // Pattern 1: Name (BRAND) strength form [extended release 24hr] - like "Oxybutynin (DITROPAN XL) 5 mg tablet extended release 24hr"
    RegExp(r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\(([A-Z\s]+)\)\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(tablet|capsule|solution|suspension|injection|cream|ointment|gel|syrup|extended|release)', caseSensitive: false),
    // Pattern 2: Name strength form - like "Lisinopril 10 mg tablet"
    RegExp(r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))\s*(tablet|capsule|solution|suspension|injection|cream|ointment|gel|syrup)', caseSensitive: false),
    // Pattern 3: Name form strength - like "Lisinopril tablet 10 mg"
    RegExp(r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(tablet|capsule|solution|suspension|injection|cream|ointment|gel|syrup)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))', caseSensitive: false),
    // Pattern 4: Just name and strength - like "Lisinopril 10 mg"
    RegExp(r'^([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|unit))', caseSensitive: false),
    // Pattern 5: Just medication name - like "Lisinopril"
    RegExp(r'^([A-Za-z]{3,}(?:\s+[A-Za-z]+)*)', caseSensitive: false),
  ];
  
  for (int i = 0; i < patterns.length; i++) {
    var pattern = patterns[i];
    var match = pattern.firstMatch(line);
    if (match != null) {
      Map<String, dynamic> result = {};

      // Extract based on pattern index
      if (i == 0) {
        // Pattern 1: Name (BRAND) strength form
        result['name'] = match.group(1)?.trim();
        result['brand'] = match.group(2)?.trim();
        result['strength'] = match.group(3)?.trim();
        result['form'] = match.group(4)?.trim() ?? 'tablet';
      } else if (i == 1) {
        // Pattern 2: Name strength form
        result['name'] = match.group(1)?.trim();
        result['strength'] = match.group(2)?.trim();
        result['form'] = match.group(3)?.trim() ?? 'tablet';
      } else if (i == 2) {
        // Pattern 3: Name form strength
        result['name'] = match.group(1)?.trim();
        result['form'] = match.group(2)?.trim();
        result['strength'] = match.group(3)?.trim();
      } else if (i == 3) {
        // Pattern 4: Name strength
        result['name'] = match.group(1)?.trim();
        result['strength'] = match.group(2)?.trim();
        result['form'] = 'tablet';
      } else if (i == 4) {
        // Pattern 5: Name only - with validation
        String? name = match.group(1)?.trim();
        
        // Skip if in exclude list or all caps (location)
        if (name != null && 
            (excludeTerms.contains(name.toLowerCase()) || 
             name.toUpperCase() == name || 
             name.length > 25)) {
          continue;
        }
        
        result['name'] = name;
        result['form'] = 'tablet';
      }

      // Validate before returning
      if (result['name'] != null && result['name'].toString().length >= 3) {
        // Final exclude check
        if (excludeTerms.contains(result['name'].toString().toLowerCase())) {
          continue;
        }
        
        print('  ✓ Pattern ${i+1} matched: ${result['name']} | ${result['strength']} | ${result['form']}');
        return result;
      }
    }
  }
  
  return null;
}

/// Parse floor stock format (tabular, floor-centric)
List<Map<String, dynamic>> _parseFloorStockFormat(String text) {
  List<Map<String, dynamic>> parsed = [];
  
  // Enhanced patterns for various pharmacy formats
  List<RegExp> patterns = [
    // Standard: medication dose floor quantity
    RegExp(r'([A-Za-z\s]+)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))\s+(\d+[EW]\d*)\s+(\d+)', caseSensitive: false),
    // Simple: medication dose
    RegExp(r'([A-Za-z]{3,}[A-Za-z\s]*)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))', caseSensitive: false),
    // With form: medication dose form
    RegExp(r'([A-Za-z]{3,}[A-Za-z\s]*)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))\s+(tablet|capsule|vial|susp|syrup)', caseSensitive: false),
  ];
  
  RegExp numberRegex = RegExp(r'\b(MRN|Med Rec|Patient ID|Rx|Prescription|Order #|BABCOCK #)?\s*([A-Za-z0-9-]{6,15})\b', caseSensitive: false);

  for (var pattern in patterns) {
    var matches = pattern.allMatches(text);
    for (var match in matches) {
      var medMap = {
        'name': match.group(1)?.trim(),
        'strength': match.group(2)?.trim(),
        'floor': match.group(3)?.trim(),
        'quantity': match.group(4)?.trim() ?? '1',
        'type': match.group(3)?.contains(RegExp(r'tablet|capsule|vial|susp|syrup', caseSensitive: false)) == true 
            ? match.group(3) : 'tablet',
      };
      
      // Extract numbers
      _extractNumbers(text, medMap, numberRegex);
      parsed.add(medMap);
    }
    if (parsed.isNotEmpty) break; // Use first successful pattern
  }
  
  return parsed;
}

/// Parse cart fill format (patient and sig-centric)
List<Map<String, dynamic>> _parseCartFillFormat(String text) {
  List<Map<String, dynamic>> parsed = [];
  
  // Enhanced patterns for cart fill documents
  List<RegExp> patterns = [
    // Full format: medication dose form sig patient
    RegExp(r'([A-Za-z\s]+)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))\s+(tablet|capsule|vial|susp|syrup|neb|IV|oral)\s+(q\d+h|bid|tid|qd|qhs|prn|daily|BEDTIME)\s+(?:for\s+)?(?:patient\s+)?(\w+)', caseSensitive: false),
    // Medication + dose + sig
    RegExp(r'([A-Za-z]{3,}[A-Za-z\s]*)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))\s+(bid|tid|qd|qhs|prn|daily|BEDTIME)', caseSensitive: false),
    // Simple medication + dose
    RegExp(r'([A-Za-z]{3,}[A-Za-z\s]*)\s+(\d+[\s.]*(?:mg|mcg|g|mL|unit))', caseSensitive: false),
    // Any medication name (3+ letters)
    RegExp(r'([A-Za-z]{3,}[A-Za-z\s]*)', caseSensitive: false),
  ];
  
  RegExp numberRegex = RegExp(r'\b(MRN|Med Rec|Patient ID|Rx|Prescription|Order #|BABCOCK #)?\s*([A-Za-z0-9-]{6,15})\b', caseSensitive: false);

  for (var pattern in patterns) {
    var matches = pattern.allMatches(text);
    for (var match in matches) {
      String? name = match.group(1)?.trim();
      if (name != null && name.length >= 3) {
        var medMap = {
          'name': name,
          'strength': match.group(2)?.trim() ?? '1 mg',
          'type': match.group(3)?.trim() ?? 'tablet',
          'dose': match.group(4)?.trim() ?? match.group(3)?.trim() ?? 'daily',
          'patient': match.group(5)?.trim(),
        };
        
        // Extract numbers
        _extractNumbers(text, medMap, numberRegex);
        parsed.add(medMap);
      }
    }
    if (parsed.isNotEmpty) break; // Use first successful pattern
  }
  
  return parsed;
}

/// Extract numbers (MRN, Rx, Order) from text
void _extractNumbers(String text, Map<String, dynamic> medMap, RegExp numberRegex) {
  var numMatches = numberRegex.allMatches(text);
  for (var nMatch in numMatches) {
    var label = nMatch.group(1)?.toLowerCase() ?? '';
    var value = nMatch.group(2)?.trim();
    if (label.contains('mrn')) medMap['mrn'] = value;
    if (label.contains('rx') || label.contains('prescription')) medMap['rx_number'] = value;
    if (label.contains('order') || label.contains('babcock')) medMap['order_number'] = value;
  }
}

/// Clean parsed medications to fix OCR errors
List<Map<String, dynamic>> cleanParsedMeds(List<Map<String, dynamic>> parsed) {
  return parsed.map((med) {
    // Fix common OCR errors
    if (med['strength'] != null) {
      med['strength'] = med['strength'].toString()
          .replaceAll('\$', '5')  // $ to 5
          .replaceAll('§', '5')   // § to 5
          .replaceAll('S', '5')   // S to 5 in numeric context
          .replaceAll('O', '0')   // O to 0 in numeric context
          .replaceAll('l', '1')   // l to 1 in numeric context
          .trim();
    }
    
    // Standardize forms
    if (med['type'] != null) {
      String type = med['type'].toString().toLowerCase();
      if (type.contains('tab')) med['type'] = 'tablet';
      if (type.contains('cap')) med['type'] = 'capsule';
      if (type.contains('susp')) med['type'] = 'suspension';
      if (type.contains('syr')) med['type'] = 'syrup';
      if (type.contains('inj')) med['type'] = 'injection';
    }
    
    // Clean medication names
    if (med['name'] != null) {
      med['name'] = med['name'].toString()
          .replaceAll(RegExp(r'[^\w\s]'), '')
          .trim();
    }
    
    return med;
  }).toList();
}

/// Legacy function for backward compatibility
Future<Map<String, String?>> parseNumbersWithLLM(String ocrText, String apiKey) async {
  var results = await parseWithLLM(ocrText, apiKey);
  if (results.isNotEmpty) {
    var result = results.first;
    return {
      'mrn': result['mrn']?.toString(),
      'rx_number': result['rx_number']?.toString(),
      'order_number': result['order_number']?.toString(),
    };
  }
  return {'mrn': null, 'rx_number': null, 'order_number': null};
}
