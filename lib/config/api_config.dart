import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../utils/app_logger.dart';

class ApiConfig {
  // Grok API configuration
  static const String grokApiUrl = 'https://api.x.ai/v1/chat/completions';
  
  // Temporary hardcoded API key for testing
  static String? get grokApiKey {
    // Try .env first, fallback to hardcoded
    String? envKey = dotenv.env['GROK_API_KEY'];
    AppLogger.info('=== API KEY DEBUG ===', name: 'ApiConfig');
    AppLogger.info('Env key loaded: ${envKey != null && envKey.isNotEmpty}', name: 'ApiConfig');
    AppLogger.info('Env key length: ${envKey?.length ?? 0}', name: 'ApiConfig');
    
    if (envKey != null && envKey.isNotEmpty && !envKey.contains('your-api-key-here')) {
      return envKey;
    }
    
    // No fallback - require .env file
    return null;
  }
  
  static bool get isGrokApiEnabled => grokApiKey != null && grokApiKey!.isNotEmpty;
}
