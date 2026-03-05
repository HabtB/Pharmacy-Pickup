import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:go_router/go_router.dart';

import '../models/med_item.dart';
import '../controllers/process_controller.dart';
import '../widgets/medication_list.dart';
import '../widgets/process/process_header.dart';
import '../widgets/process/ocr_progress_dialog.dart';
import '../widgets/process/process_action_buttons.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import '../utils/app_logger.dart';
import '../theme/app_theme.dart';

class ProcessScreen extends StatefulWidget {
  final String mode;
  final List<XFile>? scannedImages;
  final String? mockText;
  final List<MedItem>? initialMedications;

  const ProcessScreen({
    super.key,
    required this.mode,
    this.scannedImages,
    this.mockText,
    this.initialMedications,
  });

  @override
  State<ProcessScreen> createState() => _ProcessScreenState();
}

class _ProcessScreenState extends State<ProcessScreen> {
  late final ProcessController _controller;
  bool _groupByFloor = false;

  @override
  void initState() {
    super.initState();
    WakelockPlus.enable();

    _controller = ProcessController(mode: widget.mode);

    if (widget.initialMedications != null &&
        widget.initialMedications!.isNotEmpty) {
      AppLogger.info(
          'Restoring ${widget.initialMedications!.length} medications',
          name: 'ProcessScreen');
      _controller.restoreSession(widget.initialMedications!);
    } else if (widget.mockText != null) {
      AppLogger.info('Processing mock text', name: 'ProcessScreen');
      _runMockText();
    } else if (widget.scannedImages != null &&
        widget.scannedImages!.isNotEmpty) {
      AppLogger.info(
          'Processing ${widget.scannedImages!.length} scanned images',
          name: 'ProcessScreen');
      _runOcr();
    } else {
      AppLogger.info('No images — using simulation', name: 'ProcessScreen');
      _controller.restoreSession(
          _controller.scannedMedications.isEmpty
              ? []
              : _controller.scannedMedications);
    }
  }

  // ── OCR / parsing triggers ─────────────────────────────────────────────────

  Future<void> _runOcr() async {
    // Reset the processing controller first so the dialog and the OCR
    // service share the exact same instance.
    _controller.resetProcessingController();

    if (mounted) {
      OcrProgressDialog.show(
        context,
        imageCount: widget.scannedImages!.length,
        controller: _controller.processingController,
      );
    }

    try {
      await _controller.processScannedImages(widget.scannedImages!);
    } catch (_) {
      // On error the controller falls back to simulation — just show snackbar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('OCR failed — showing demo data'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 4),
          ),
        );
      }
    } finally {
      // Close progress dialog
      if (mounted) Navigator.of(context).pop();
    }

    // Post-OCR: check if processing was stopped and offer recovery options
    final wasStopped = _controller.processingController.isStopped;
    final count = _controller.scannedMedications.length;

    if (wasStopped && count == 0 && mounted) {
      _showStopRecoveryDialog();
      return;
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(wasStopped
              ? 'Stopped early — found $count medications so far'
              : 'Found $count medications from ${widget.scannedImages!.length} scanned pages'),
          backgroundColor: count > 0
              ? (wasStopped ? Colors.orange : Colors.green)
              : Colors.orange,
        ),
      );
    }
  }

  Future<void> _runMockText() async {
    try {
      await _controller.processMockText(widget.mockText!);
    } catch (e) {
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

  Future<void> _showStopRecoveryDialog() async {
    final result = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text('Processing Stopped'),
        content: const Text(
          'No medications were found before processing was stopped. '
          'What would you like to do?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop('home'),
            child: const Text('Go Home'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop('review'),
            child: const Text('Review Scans'),
          ),
          ElevatedButton.icon(
            onPressed: () => Navigator.of(context).pop('retry'),
            icon: const Icon(Icons.refresh),
            label: const Text('Try Again'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.msBlue,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );

    if (!mounted) return;
    if (result == 'retry') {
      _runOcr();
    } else if (result == 'review') {
      context.go('/review/${widget.mode}', extra: widget.scannedImages);
    } else if (result == 'home') {
      context.go('/home');
    }
  }

  Future<void> _startPicking() async {
    try {
      final processed = await _controller.processMedications();
      if (mounted) {
        context.push('/slideshow', extra: processed);
      }
    } catch (e) {
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
  void dispose() {
    WakelockPlus.disable();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _controller,
      builder: (context, _) {
        final meds = _controller.scannedMedications;
        return PopScope(
          canPop: meds.isEmpty,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop) return;
            final shouldPop = await showDialog<bool>(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('Exit Process?'),
                content: const Text(
                    'You have scanned items. Going back will clear the current list. Are you sure?'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(true),
                    child: const Text('Exit',
                        style: TextStyle(color: Colors.red)),
                  ),
                ],
              ),
            );
            if (shouldPop == true && mounted) {
              _controller.clearAll();
              WidgetsBinding.instance.addPostFrameCallback((_) {
                if (mounted) Navigator.of(context).pop();
              });
            }
          },
          child: Scaffold(
            appBar: AppBar(
              title: const Text('Medication Processing'),
              backgroundColor: AppColors.msBlue,
              foregroundColor: Colors.white,
            ),
            body: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Mode header card
                  ProcessHeader(mode: widget.mode),

                  const SizedBox(height: 24),

                  // List header + floor/location toggle
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Scanned Medications:',
                              style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold)),
                          if (meds.isNotEmpty)
                            Text('${meds.length} items',
                                style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.grey.shade600)),
                        ],
                      ),
                      if (meds.isNotEmpty)
                        Row(
                          children: [
                            Text(
                              _groupByFloor ? 'Floor' : 'Location',
                              style: TextStyle(
                                fontSize: 12,
                                color: _groupByFloor
                                    ? Colors.purple.shade700
                                    : AppColors.msBlue,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Switch(
                              value: _groupByFloor,
                              onChanged: (v) =>
                                  setState(() => _groupByFloor = v),
                              activeColor: Colors.purple.shade700,
                              inactiveThumbColor: AppColors.msBlue,
                            ),
                          ],
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Medication list
                  Card(
                    elevation: 2,
                    child: SizedBox(
                      height: 400,
                      child: meds.isEmpty
                          ? const Center(
                              child: Text('No medications scanned yet',
                                  style: TextStyle(
                                      fontSize: 16, color: Colors.grey)))
                          : MedicationList(
                              medications: meds,
                              groupByFloor: _groupByFloor,
                            ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Action buttons
                  ProcessActionButtons(
                    isProcessing: _controller.isProcessing,
                    isEmpty: meds.isEmpty,
                    onStartPicking: _startPicking,
                    onClearAll: _controller.clearAll,
                    onAddMore: _controller.addMedications,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
