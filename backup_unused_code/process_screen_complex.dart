import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../models/med_item.dart';
import '../services/medication_processor.dart';
import '../services/ocr_service.dart';
import '../services/parsing_service.dart';
import '../config/api_config.dart';
import 'slideshow_screen.dart';

class ProcessScreen extends StatefulWidget {
  final String mode;
  final List<XFile>? scannedImages;
  final String? mockText;

  const ProcessScreen({
    super.key,
    required this.mode,
    this.scannedImages,
    this.mockText,
  });

  @override
  State<ProcessScreen> createState() => _ProcessScreenState();
}

class _ProcessScreenState extends State<ProcessScreen> {
  bool isProcessing = false;
  List<MedItem> scannedMedications = [];
  List<MedItem> processedMedications = [];

  @override
  void initState() {
    super.initState();
    print('=== PROCESS SCREEN DEBUG: InitState called ===');
    
    // Check if we have mock text data
    if (widget.mockText != null) {
      print('=== PROCESS SCREEN DEBUG: Processing mock text data ===');
      _processMockText();
    } else if (widget.scannedImages != null && widget.scannedImages!.isNotEmpty) {
      print('=== PROCESS SCREEN DEBUG: Processing ${widget.scannedImages!.length} scanned images ===');
      _processScannedImages();
    } else {
      print('=== PROCESS SCREEN DEBUG: No scanned images, using simulation ===');
      // Fallback to simulated data for demo purposes
      scannedMedications = MedicationProcessor.simulateScannedMedications(mode: widget.mode);
    }
  }

  Future<void> _processScannedImages() async {
    if (widget.scannedImages == null || widget.scannedImages!.isEmpty) return;
    setState(() {
      isProcessing = true;
    });

    try {
      // Extract text from images using OCR
      String extractedText = await OCRService.extractTextFromImages(widget.scannedImages!);
      
      // Parse extracted text into medications (disable LLM for now)
      List<MedItem> medications = await OCRService.parseTextToMedications(
        extractedText, 
        widget.mode,
        apiKey: null, // Disable LLM parsing
      );
      
      
      setState(() {
        scannedMedications = medications;
        isProcessing = false;
      });
      
      // Show feedback to user
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Found ${medications.length} medications from ${widget.scannedImages!.length} scanned pages'),
            backgroundColor: medications.isNotEmpty ? Colors.green : Colors.orange,
          ),
        );
      }
    } catch (e) {
      setState(() {
        isProcessing = false;
        // Fallback to simulation if OCR fails
        scannedMedications = MedicationProcessor.simulateScannedMedications(mode: widget.mode);
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('OCR processing failed, using demo data: $e'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    }
  }

  Future<void> _processMockText() async {
    setState(() {
      isProcessing = true;
    });

    try {
      print('=== MOCK TEXT DEBUG: Processing mock text ===');
      print('Mock text: ${widget.mockText}');
      
      // Parse mock text directly into medications (disable LLM for now)
      List<MedItem> medications = await OCRService.parseTextToMedications(
        widget.mockText!, 
        widget.mode,
        apiKey: null, // Disable LLM parsing
      );
      
      print('=== MOCK TEXT DEBUG: Parsed ${medications.length} medications ===');
      
      setState(() {
        scannedMedications = medications;
        isProcessing = false;
      });
    } catch (e) {
      print('=== MOCK TEXT DEBUG: Error processing mock text: $e ===');
      setState(() {
        isProcessing = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error processing mock text: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _processMedications() async {
    setState(() {
      isProcessing = true;
    });

    try {
      final processed = await MedicationProcessor.processAndOrganizeMedications(scannedMedications);
      setState(() {
        processedMedications = processed;
        isProcessing = false;
      });

      // Navigate to slideshow
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => SlideshowScreen(medications: processedMedications),
          ),
        );
      }
    } catch (e) {
      setState(() {
        isProcessing = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error processing medications: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Hybrid parsing function with regex first, LLM fallback
  Future<List<Map<String, dynamic>>> _parseExtractedText(String text, String mode) async {
    return await parseExtractedText(text, mode, ApiConfig.grokApiKey);
  }

  /// Convert parsed data to MedItem objects
  List<MedItem> _convertToMedItems(List<Map<String, dynamic>> parsedData, String mode) {
    List<MedItem> medications = [];
    
    for (var data in parsedData) {
      if (data['name'] != null && data['name'].toString().isNotEmpty) {
        // Calculate pick amount from dose/sig
        int pickAmount = _calculatePickAmountFromDose(data['dose']?.toString());
        double calculatedQty = _extractStrengthValue(data['strength']?.toString() ?? '1');
        
        // Build dose string from strength
        String dose = data['strength']?.toString() ?? '1 mg';
        if (!dose.contains(RegExp(r'(mg|mcg|g|mL|unit)'))) {
          dose += ' mg';
        }
        
        medications.add(MedItem(
          name: data['name'].toString(),
          dose: dose,
          form: data['type']?.toString() ?? 'tablet',
          pickAmount: pickAmount,
          calculatedQty: calculatedQty,
          patient: data['patient']?.toString(),
          sig: data['dose']?.toString(),
          floor: data['floor']?.toString(),
          notes: _buildNotesFromData(data),
        ));
      }
    }
    
    return medications;
  }

  /// Calculate pick amount from dose/sig information
  int _calculatePickAmountFromDose(String? dose) {
    if (dose == null) return 1;
    
    String doseUpper = dose.toUpperCase();
    if (doseUpper.contains('BID') || doseUpper.contains('TWICE')) return 2;
    if (doseUpper.contains('TID') || doseUpper.contains('THREE')) return 3;
    if (doseUpper.contains('QID') || doseUpper.contains('FOUR')) return 4;
    if (doseUpper.contains('Q6H')) return 4;
    if (doseUpper.contains('Q8H')) return 3;
    if (doseUpper.contains('Q12H')) return 2;
    if (doseUpper.contains('BEDTIME') || doseUpper.contains('DAILY') || doseUpper.contains('QD')) return 1;
    
    return 1;
  }

  /// Extract numeric strength value
  double _extractStrengthValue(String strength) {
    RegExp numberPattern = RegExp(r'(\d+(?:\.\d+)?)');
    var match = numberPattern.firstMatch(strength);
    return double.tryParse(match?.group(1) ?? '1') ?? 1.0;
  }

  /// Build notes from parsed data
  String _buildNotesFromData(Map<String, dynamic> data) {
    List<String> notes = [];
    
    if (data['mrn'] != null && data['mrn'].toString().isNotEmpty) {
      notes.add('MRN: ${data['mrn']}');
    }
    if (data['rx_number'] != null && data['rx_number'].toString().isNotEmpty) {
      notes.add('Rx: ${data['rx_number']}');
    }
    if (data['order_number'] != null && data['order_number'].toString().isNotEmpty) {
      notes.add('Order: ${data['order_number']}');
    }
    
    return notes.join(' | ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Medication Processing'),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Card(
              elevation: 4,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Icon(
                      Icons.medication,
                      size: 48,
                      color: Colors.blue.shade700,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.mode == 'floor_stock' ? 'Floor Stock Distribution' : '24-Hour Cart-Fill',
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.mode == 'floor_stock' 
                        ? 'Process bulk medication picks for floor-level distribution'
                        : 'Process patient-specific medications for 24-hour cart preparation',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Scanned medications list
            const Text(
              'Scanned Medications:',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            
            Expanded(
              child: Card(
                elevation: 2,
                child: scannedMedications.isEmpty
                    ? const Center(
                        child: Text(
                          'No medications scanned yet',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.grey,
                          ),
                        ),
                      )
                    : ListView.builder(
                        itemCount: scannedMedications.length,
                        itemBuilder: (context, index) {
                          final med = scannedMedications[index];
                          return ListTile(
                            leading: CircleAvatar(
                              backgroundColor: Colors.blue.shade100,
                              child: Text(
                                '${med.pickAmount}',
                                style: TextStyle(
                                  color: Colors.blue.shade700,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            title: Text(
                              med.name,
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text('${med.dose} ${med.form}'),
                            trailing: med.location != null
                                ? Icon(Icons.location_on, color: Colors.green.shade600)
                                : Icon(Icons.location_off, color: Colors.grey.shade400),
                          );
                        },
                      ),
              ),
            ),

            const SizedBox(height: 16),

            // Action buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      // Simulate adding more medications
                      setState(() {
                        scannedMedications.addAll([
                          MedItem(name: 'Furosemide', dose: '40 mg', form: 'tablet', pickAmount: 1),
                          MedItem(name: 'Pantoprazole DR', dose: '40 mg', form: 'tablet', pickAmount: 2),
                        ]);
                      });
                    },
                    icon: const Icon(Icons.add),
                    label: const Text('Add More'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey.shade600,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: ElevatedButton.icon(
                    onPressed: scannedMedications.isEmpty || isProcessing ? null : _processMedications,
                    icon: isProcessing
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : const Icon(Icons.play_arrow),
                    label: Text(isProcessing ? 'Processing...' : 'Start Picking'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue.shade700,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Clear button
            TextButton.icon(
              onPressed: scannedMedications.isEmpty
                  ? null
                  : () {
                      setState(() {
                        scannedMedications.clear();
                        processedMedications.clear();
                      });
                    },
              icon: const Icon(Icons.clear),
              label: const Text('Clear All'),
              style: TextButton.styleFrom(
                foregroundColor: Colors.red.shade600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
