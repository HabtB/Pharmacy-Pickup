import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import '../models/med_item.dart';
import '../services/medication_processor.dart';
import '../services/ocr_service.dart';
import '../services/parsing_service.dart';
import '../services/processing_controller.dart';
import '../config/api_config.dart';
import 'slideshow_screen.dart';
import '../widgets/medication_list.dart';
import '../utils/app_logger.dart';

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
  final ProcessingController _processingController = ProcessingController();

  @override
  void dispose() {
    WakelockPlus.disable();
    _processingController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    AppLogger.info('InitState called', name: 'ProcessScreen');

    // Check if we have mock text data
    if (widget.mockText != null) {
      AppLogger.info('Processing mock text data', name: 'ProcessScreen');
      WidgetsBinding.instance.addPostFrameCallback((_) => _processMockText());
    } else if (widget.scannedImages != null && widget.scannedImages!.isNotEmpty) {
      AppLogger.info('Processing ${widget.scannedImages!.length} scanned images', name: 'ProcessScreen');
      WidgetsBinding.instance.addPostFrameCallback((_) => _processScannedImages());
    } else {
      AppLogger.info('No scanned images, using simulation', name: 'ProcessScreen');
      // Fallback to simulated data for demo purposes
      scannedMedications = MedicationProcessor.simulateScannedMedications(mode: widget.mode);
    }
  }

  Future<void> _processScannedImages() async {
    if (widget.scannedImages == null || widget.scannedImages!.isEmpty) return;

    // Keep screen on during OCR processing
    WakelockPlus.enable();
    _processingController.reset();

    // Show progress dialog with pause/stop controls
    if (mounted) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return ListenableBuilder(
            listenable: _processingController,
            builder: (context, _) {
              final isPaused = _processingController.isPaused;
              final isStopped = _processingController.isStopped;
              return AlertDialog(
                title: Text(isPaused ? 'Paused' : 'Processing Documents'),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isPaused
                          ? 'Processing is paused. Tap Resume to continue.'
                          : 'Processing ${widget.scannedImages!.length} images with OCR and AI...',
                      style: TextStyle(fontSize: 16),
                    ),
                    SizedBox(height: 16),
                    if (!isPaused && !isStopped) ...[
                      Text(
                        'This may take 10-20 seconds per page',
                        style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                      ),
                      SizedBox(height: 16),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: LinearProgressIndicator(
                          minHeight: 20,
                          backgroundColor: Colors.grey.shade300,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.blue.shade700),
                        ),
                      ),
                    ],
                  ],
                ),
                actions: isStopped
                    ? null
                    : [
                        TextButton(
                          onPressed: () {
                            _processingController.stop();
                          },
                          child: Text('Stop', style: TextStyle(color: Colors.red)),
                        ),
                        ElevatedButton.icon(
                          onPressed: () {
                            if (isPaused) {
                              _processingController.resume();
                            } else {
                              _processingController.pause();
                            }
                          },
                          icon: Icon(isPaused ? Icons.play_arrow : Icons.pause),
                          label: Text(isPaused ? 'Resume' : 'Pause'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: isPaused ? Colors.green : Colors.orange,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ],
              );
            },
          );
        },
      );
    }

    if (!mounted) return;
    setState(() {
      isProcessing = true;
    });

    try {
      AppLogger.info('Starting OCR extraction for ${widget.scannedImages!.length} images', name: 'ProcessScreen');

      AppLogger.info('Starting intelligent OCR processing for ${widget.scannedImages!.length} images', name: 'ProcessScreen');

      // Parse medications directly using Docling server (handles OCR + parsing in one step)
      List<MedItem> medications = await OCRService.parseImagesDirectly(
        widget.scannedImages!,
        widget.mode,
        controller: _processingController,
      );

      if (medications.isEmpty) {
        AppLogger.error('WARNING: No medications found in scanned images', name: 'ProcessScreen');
      }

      AppLogger.info('Received ${medications.length} medications from OCR service', name: 'ProcessScreen');

      if (!mounted) return;
      setState(() {
        scannedMedications = medications;
        isProcessing = false;
      });

      AppLogger.info('scannedMedications now has ${scannedMedications.length} items', name: 'ProcessScreen');

      // Close progress dialog
      if (mounted) {
        Navigator.of(context).pop();
      }

      // Show feedback to user
      if (mounted) {
        final wasStopped = _processingController.isStopped;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(wasStopped
                ? 'Stopped early — found ${medications.length} medications so far'
                : 'Found ${medications.length} medications from ${widget.scannedImages!.length} scanned pages'),
            backgroundColor: medications.isNotEmpty
                ? (wasStopped ? Colors.orange : Colors.green)
                : Colors.orange,
          ),
        );
      }
    } catch (e, stackTrace) {
      AppLogger.error('ERROR in _processScannedImages: $e', name: 'ProcessScreen');
      AppLogger.error('Stack trace: $stackTrace', name: 'ProcessScreen');

      if (!mounted) return;
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
    } finally {
      // Allow screen to sleep again
      WakelockPlus.disable();
    }
  }

  Future<void> _processMockText() async {
    if (!mounted) return;
    setState(() {
      isProcessing = true;
    });

    try {
      AppLogger.info('Processing mock text', name: 'ProcessScreen');
      AppLogger.info('Mock text: ${widget.mockText}', name: 'ProcessScreen');

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

      AppLogger.info('Parsed ${medications.length} medications', name: 'ProcessScreen');

      if (!mounted) return;
      setState(() {
        scannedMedications = medications;
        isProcessing = false;
      });
    } catch (e) {
      AppLogger.error('Error processing mock text: $e', name: 'ProcessScreen');
      if (!mounted) return;
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
    AppLogger.info('Starting with ${scannedMedications.length} scanned medications', name: 'ProcessScreen');

    if (!mounted) return;
    setState(() {
      isProcessing = true;
    });

    try {
      final processed = await MedicationProcessor.processAndOrganizeMedications(scannedMedications);
      AppLogger.info('Processed ${processed.length} medications', name: 'ProcessScreen');

      if (!mounted) return;
      setState(() {
        processedMedications = processed;
        isProcessing = false;
      });

      // Navigate to slideshow
      AppLogger.info('Passing ${processedMedications.length} medications to slideshow screen', name: 'ProcessScreen');

      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => SlideshowScreen(medications: processedMedications),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        isProcessing = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error processing medications: $e'),
          backgroundColor: Colors.red,
        ),
      );
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
