import 'dart:io';
import 'package:opencv_4/opencv_4.dart';
import 'package:path_provider/path_provider.dart';
import '../utils/app_logger.dart';

class ImageEnhancementService {
  /// Enhance image for better OCR using OpenCV
  static Future<String> enhanceImageForOCR(String imagePath) async {
    try {
      AppLogger.info('=== IMAGE ENHANCEMENT DEBUG ===', name: 'ImageEnhance');
      AppLogger.info('Original image path: $imagePath', name: 'ImageEnhance');
      
      // Load image
      var img = await Cv2.imread(imagePath);
      AppLogger.info('Image loaded successfully', name: 'ImageEnhance');
      
      // Convert to grayscale for better OCR
      img = await Cv2.cvtColor(img, Cv2.COLOR_BGR2GRAY);
      AppLogger.info('Converted to grayscale', name: 'ImageEnhance');
      
      // Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
      img = await Cv2.clahe(img, clipLimit: 2.0, tileGridSize: [8, 8]);
      AppLogger.info('Applied CLAHE contrast enhancement', name: 'ImageEnhance');
      
      // Apply Gaussian blur to reduce noise
      img = await Cv2.gaussianBlur(img, [3, 3], 0);
      AppLogger.info('Applied Gaussian blur', name: 'ImageEnhance');
      
      // Apply threshold to get binary image
      img = await Cv2.threshold(img, 0, 255, Cv2.THRESH_BINARY + Cv2.THRESH_OTSU);
      AppLogger.info('Applied binary threshold', name: 'ImageEnhance');
      
      // Get temporary directory for enhanced image
      final tempDir = await getTemporaryDirectory();
      final fileName = imagePath.split('/').last.replaceAll('.jpg', '_enhanced.jpg');
      final enhancedPath = '${tempDir.path}/$fileName';
      
      // Save enhanced image
      await Cv2.imwrite(enhancedPath, img);
      AppLogger.info('Enhanced image saved to: $enhancedPath', name: 'ImageEnhance');
      
      return enhancedPath;
    } catch (e) {
      AppLogger.error('Image enhancement failed: $e', name: 'ImageEnhance');
      AppLogger.info('Falling back to original image', name: 'ImageEnhance');
      return imagePath; // Fallback to original if enhancement fails
    }
  }
  
  /// Get rotation angle for deskewing (simplified version)
  static Future<double> getRotationAngle(dynamic img) async {
    try {
      // This is a simplified approach - in practice you'd use more sophisticated methods
      // For now, return 0 (no rotation correction)
      return 0.0;
    } catch (e) {
      AppLogger.error('Rotation angle detection failed: $e', name: 'ImageEnhance');
      return 0.0;
    }
  }
  
  /// Apply rotation correction if needed
  static Future<dynamic> correctRotation(dynamic img, double angle) async {
    try {
      if (angle.abs() > 1.0) { // Only rotate if angle is significant
        final center = await Cv2.getImageCenter(img);
        final rotationMatrix = await Cv2.getRotationMatrix2D(center, angle, 1.0);
        img = await Cv2.warpAffine(img, rotationMatrix, await Cv2.getImageSize(img));
        AppLogger.info('Applied rotation correction: ${angle.toStringAsFixed(1)} degrees', name: 'ImageEnhance');
      }
      return img;
    } catch (e) {
      AppLogger.error('Rotation correction failed: $e', name: 'ImageEnhance');
      return img;
    }
  }
}
