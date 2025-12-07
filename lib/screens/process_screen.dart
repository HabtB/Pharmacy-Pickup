import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../models/med_item.dart';
import '../services/medication_processor.dart';
import '../services/ocr_service.dart';
import '../services/parsing_service.dart';
import '../config/api_config.dart';
import 'slideshow_screen.dart';
import '../widgets/medication_list.dart';

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

    // Show progress dialog
    if (mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return AlertDialog(
            title: Text('Processing Documents'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Processing ${widget.scannedImages!.length} images with OCR and AI...',
                  style: TextStyle(fontSize: 16),
                ),
                SizedBox(height: 16),
                Text(
                  'This may take 10-20 seconds',
                  style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                ),
                SizedBox(height: 16),
                // Progress bar with percentage
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    minHeight: 20,
                    backgroundColor: Colors.grey.shade300,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.blue.shade700),
                  ),
                ),
                SizedBox(height: 8),
                Center(
                  child: Text(
                    'Processing...',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.blue.shade700,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      );
    }

    setState(() {
      isProcessing = true;
    });

    try {
      print('=== PROCESS SCREEN: Starting OCR extraction for ${widget.scannedImages!.length} images ===');

      print('=== PROCESS SCREEN: Starting intelligent OCR processing for ${widget.scannedImages!.length} images ===');

      // Parse medications directly using Docling server (handles OCR + parsing in one step)
      List<MedItem> medications = await OCRService.parseImagesDirectly(
        widget.scannedImages!,
        widget.mode,
      );
      
      if (medications.isEmpty) {
        print('WARNING: No medications found in scanned images');
      }

      print('=== PROCESS SCREEN DEBUG: Received ${medications.length} medications from OCR service ===');

      setState(() {
        scannedMedications = medications;
        isProcessing = false;
      });

      print('=== PROCESS SCREEN DEBUG: scannedMedications now has ${scannedMedications.length} items ===');

      // Close progress dialog
      if (mounted) {
        Navigator.of(context).pop();
      }

      // Show feedback to user
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Found ${medications.length} medications from ${widget.scannedImages!.length} scanned pages'),
            backgroundColor: medications.isNotEmpty ? Colors.green : Colors.orange,
          ),
        );
      }
    } catch (e, stackTrace) {
      print('ERROR in _processScannedImages: $e');
      print('Stack trace: $stackTrace');

      setState(() {
        isProcessing = false;
        // Fallback to simulation if OCR fails
        scannedMedications = MedicationProcessor.simulateScannedMedications(mode: widget.mode);
      });

      // Close progress dialog
      if (mounted) {
        Navigator.of(context).pop();
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('OCR processing failed, using demo data: $e'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 5),
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
      
      // For mock text, we'll use the old parsing service temporarily
      List<MedItem> medications = await parseExtractedText(
        widget.mockText!, 
        widget.mode,
        ApiConfig.grokApiKey,
      ).then((parsed) => parsed.map((data) => MedItem(
        name: data['name'] ?? '',
        dose: data['dose'] ?? data['strength'] ?? '',
        form: data['form'] ?? data['type'] ?? 'tablet',
        pickAmount: data['pick_amount'] ?? 1,
        location: '',
        notes: data['brand'] != null ? 'Brand: ${data['brand']}' : null,
        patient: data['patient'],
        floor: data['floor'],
        sig: data['dose'] ?? data['sig'],
        calculatedQty: (data['calculated_qty'] ?? 1.0).toDouble(),
      )).toList());
      
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
    print('=== PROCESS MEDICATIONS DEBUG: Starting with ${scannedMedications.length} scanned medications ===');

    setState(() {
      isProcessing = true;
    });

    try {
      // TEMPORARY: Disable aggregation to test if that's causing the count reduction
      final processed = await MedicationProcessor.processAndOrganizeMedications(scannedMedications, disableAggregation: true);
      print('=== PROCESS MEDICATIONS DEBUG: Processed ${processed.length} medications ===');

      setState(() {
        processedMedications = processed;
        isProcessing = false;
      });

      // Navigate to slideshow
      print('=== NAVIGATION DEBUG: Passing ${processedMedications.length} medications to slideshow screen ===');

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

            // Scanned medications list with count
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Scanned Medications:',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (scannedMedications.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.blue.shade100,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${scannedMedications.length} found',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.blue.shade700,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            
            Card(
              elevation: 2,
              child: Container(
                height: 300, // Fixed height instead of Expanded
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
                    : MedicationList(medications: scannedMedications),
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
