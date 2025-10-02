import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'process_screen.dart';
import 'document_review_screen.dart';

class ScanScreen extends StatefulWidget {
  final String mode;
  
  const ScanScreen({super.key, required this.mode});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  CameraController? _mobileController;
  List<CameraDescription>? _cameras;
  List<XFile> scannedImages = [];
  bool _isInitialized = false;
  String? _error;
  final ImagePicker _picker = ImagePicker();
  bool _isDesktop = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      _isDesktop = kIsWeb || (!Platform.isAndroid && !Platform.isIOS);
      
      // Try to initialize camera for all platforms
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _mobileController = CameraController(
          _cameras![0],
          ResolutionPreset.high,
          enableAudio: false,
        );
        
        await _mobileController!.initialize();
        
        if (mounted) {
          setState(() {
            _isInitialized = true;
          });
        }
      } else {
        setState(() {
          _error = _isDesktop ? 'No cameras available. Using file picker instead.' : 'No cameras available';
          _isInitialized = true;
        });
      }
    } catch (e) {
      setState(() {
        _error = _isDesktop ? 'Camera unavailable. Using file picker instead.' : 'Failed to initialize camera: $e';
        _isInitialized = true;
      });
    }
  }

  Future<void> _captureImage() async {
    print('=== CAMERA DEBUG: _captureImage called ===');
    try {
      XFile? image;
      
      if (_mobileController != null && _mobileController!.value.isInitialized) {
        print('=== CAMERA DEBUG: Using mobile camera controller ===');
        // Use camera controller for both mobile and desktop if available
        image = await _mobileController!.takePicture();
        print('=== CAMERA DEBUG: takePicture completed, image: ${image?.path} ===');
      } else if (_isDesktop) {
        print('=== CAMERA DEBUG: Using desktop fallback ===');
        // Fallback for desktop when camera controller unavailable
        try {
          image = await _picker.pickImage(
            source: ImageSource.camera,
            preferredCameraDevice: CameraDevice.rear,
          );
        } catch (e) {
          // If camera fails, use file picker
          final result = await FilePicker.platform.pickFiles(
            type: FileType.image,
            allowMultiple: false,
          );
          
          if (result != null && result.files.single.bytes != null) {
            final bytes = result.files.single.bytes!;
            final fileName = result.files.single.name;
            image = XFile.fromData(bytes, name: fileName);
          }
        }
      }

      if (image != null) {
        print('=== CAMERA DEBUG: Image captured successfully, adding to list ===');
        setState(() {
          scannedImages.add(image!);
        });
        print('=== CAMERA DEBUG: Total scanned images: ${scannedImages.length} ===');
        
        // Show success feedback
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Page ${scannedImages.length} captured successfully!'),
              duration: const Duration(seconds: 1),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        print('=== CAMERA DEBUG: No image captured (image is null) ===');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to capture image: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _pickFromGallery() async {
    print('=== GALLERY DEBUG: _pickFromGallery called ===');
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
      );
      
      print('=== GALLERY DEBUG: Image picker returned: ${image?.path} ===');
      
      if (image != null) {
        print('=== GALLERY DEBUG: Adding image to scannedImages list ===');
        setState(() {
          scannedImages.add(image);
        });
        print('=== GALLERY DEBUG: Total scanned images: ${scannedImages.length} ===');
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Image ${scannedImages.length} added from gallery!'),
              duration: const Duration(seconds: 1),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        print('=== GALLERY DEBUG: No image selected (image is null) ===');
      }
    } catch (e) {
      print('=== GALLERY DEBUG: Error picking image: $e ===');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to pick image: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _processScannedImages() {
    if (scannedImages.isNotEmpty) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => DocumentReviewScreen(
            mode: widget.mode,
            scannedImages: scannedImages,
          ),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please scan at least one page before processing'),
          backgroundColor: Colors.orange,
        ),
      );
    }
  }

  void _testOCRWithMockData() {
    print('=== MOCK TEST: Creating mock prescription data ===');
    
    // Navigate directly to ProcessScreen with mock text data
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ProcessScreen(
          mode: widget.mode,
          mockText: '''
Metoprolol Tartrate 25 mg tablet
Take 1 tablet twice daily

Lisinopril 10 mg tablet  
Take 1 tablet once daily

Atorvastatin 20 mg tablet
Take 1 tablet at bedtime
          ''',
        ),
      ),
    );
  }

  Widget _buildCameraPreview() {
    if (!_isInitialized) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Initializing camera...'),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.camera_alt_outlined,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              _error!,
              style: const TextStyle(color: Colors.red),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            const Text(
              'You can still use the gallery option below',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    // Show camera preview if available, otherwise show appropriate message
    if (_mobileController != null && _mobileController!.value.isInitialized) {
      return CameraPreview(_mobileController!);
    }

    if (_isDesktop && _error != null) {
      // For desktop when camera unavailable, show file picker option
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.orange.shade200, width: 2),
              ),
              child: Column(
                children: [
                  Icon(
                    Icons.photo_camera_back,
                    size: 64,
                    color: Colors.orange.shade600,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Camera Unavailable',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.orange.shade700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Use "Scan Page" to access camera\nor "Gallery" to select files',
                    style: TextStyle(color: Colors.grey),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    return const Center(
      child: Text('Camera not available'),
    );
  }

  @override
  Widget build(BuildContext context) {
    String modeTitle = widget.mode == 'floor_stock' ? 'Floor Stock' : 'Cart-Fill';
    
    return Scaffold(
      appBar: AppBar(
        title: Text('$modeTitle Scan'),
        backgroundColor: widget.mode == 'floor_stock' ? Colors.blue.shade700 : Colors.green.shade700,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Camera preview area
          Expanded(
            flex: 3,
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300, width: 2),
                borderRadius: BorderRadius.circular(8),
              ),
              margin: const EdgeInsets.all(16),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: _buildCameraPreview(),
              ),
            ),
          ),
          
          // Status and controls area
          Expanded(
            flex: 1,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  // Scan count
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.document_scanner,
                          color: Colors.blue.shade600,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Pages Scanned: ${scannedImages.length}',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(height: 16),
                  
                  // Action buttons
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _captureImage,
                          icon: const Icon(Icons.camera_alt),
                          label: const Text('Scan Page'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.blue.shade600,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _pickFromGallery,
                          icon: const Icon(Icons.photo_library),
                          label: const Text('Gallery'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.grey.shade600,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    ],
                  ),
                  
                  const SizedBox(height: 8),
                  
                  // Test OCR button (for simulator)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _testOCRWithMockData,
                      icon: const Icon(Icons.science),
                      label: const Text('Test OCR (Mock Data)'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange.shade600,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  // Process button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: scannedImages.isNotEmpty ? () {
                        print('=== PROCESS BUTTON DEBUG: Processing ${scannedImages.length} images ===');
                        _processScannedImages();
                      } : null,
                      icon: const Icon(Icons.play_arrow),
                      label: Text(
                        scannedImages.isEmpty 
                          ? 'Scan pages to process'
                          : 'Process ${scannedImages.length} page${scannedImages.length == 1 ? '' : 's'}',
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: widget.mode == 'floor_stock' ? Colors.blue.shade700 : Colors.green.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _mobileController?.dispose();
    super.dispose();
  }
}
