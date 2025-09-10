import 'dart:io';
import 'dart:convert';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import '../models/med_item.dart';

class OCRService {
  static const String _doclingServerUrl = 'http://172.20.10.9:5001';

  /// Extract text from images using Docling server
  static Future<String> extractTextFromImages(List<XFile> images) async {
    try {
      // For now, process only the first image
      if (images.isEmpty) return '';
      
      final image = images.first;
      final imageBytes = await File(image.path).readAsBytes();
      final base64Image = base64Encode(imageBytes);
      
      print('Sending image to Docling server...');
      
      final response = await http.post(
        Uri.parse('$_doclingServerUrl/parse-document'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_base64': base64Image,
          'mode': 'cart_fill'
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['raw_text'] ?? '';
      } else {
        print('Docling server error: ${response.statusCode}');
        return '';
      }
    } catch (e) {
      print('Error communicating with Docling server: $e');
      return '';
    }
  }


  /// Parse images directly using Docling server
  static Future<List<MedItem>> parseTextToMedications(String extractedText, String mode, {String? apiKey}) async {
    // This method is kept for compatibility but will be replaced by parseImagesDirectly
    return [];
  }
  
  /// Parse images directly using Docling server (new method)
  static Future<List<MedItem>> parseImagesDirectly(List<XFile> images, String mode) async {
    try {
      if (images.isEmpty) return [];
      
      final image = images.first;
      final imageBytes = await File(image.path).readAsBytes();
      final base64Image = base64Encode(imageBytes);
      
      print('Parsing medications directly with Docling...');
      
      final response = await http.post(
        Uri.parse('$_doclingServerUrl/parse-document'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_base64': base64Image,
          'mode': mode
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final medications = <MedItem>[];
        
        if (data['success'] == true && data['medications'] != null) {
          for (var medData in data['medications']) {
            medications.add(_convertMapToMedItem(medData, mode));
          }
        }
        
        print('Docling parsed ${medications.length} medications');
        return medications;
      } else {
        print('Docling server error: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('Error parsing with Docling: $e');
      return [];
    }
  }


  /// Convert parsed medication map to MedItem object
  static MedItem _convertMapToMedItem(Map<String, dynamic> data, String mode) {
    return MedItem(
      name: data['name'] ?? '',
      dose: data['dose'] ?? data['strength'] ?? '',
      form: data['form'] ?? data['type'] ?? 'tablet',
      pickAmount: data['pick_amount'] ?? data['quantity'] != null ? int.tryParse(data['quantity'].toString()) ?? 1 : 1,
      location: '', // Will be filled by database lookup
      notes: data['brand'] != null ? 'Brand: ${data['brand']}' : null,
      patient: data['patient'],
      floor: data['floor'],
      sig: data['dose'] ?? data['sig'],
      calculatedQty: (data['calculated_qty'] ?? 1.0).toDouble(),
    );
  }

  /// Check if Docling server is available
  static Future<bool> isDoclingServerAvailable() async {
    try {
      final response = await http.get(Uri.parse('$_doclingServerUrl/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
