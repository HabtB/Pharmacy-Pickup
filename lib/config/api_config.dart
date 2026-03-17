import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../utils/app_logger.dart';

class ApiConfig {
  static const String grokApiUrl = 'https://api.x.ai/v1/chat/completions';

  static String? get grokApiKey {
    String? envKey = dotenv.env['GROK_API_KEY'];
    if (kDebugMode) {
      AppLogger.info('Env key loaded: ${envKey != null && envKey.isNotEmpty}', name: 'ApiConfig');
    }

    if (envKey != null && envKey.isNotEmpty && !envKey.contains('your-api-key-here')) {
      return envKey;
    }

    return null;
  }

  static bool get isGrokApiEnabled => grokApiKey != null && grokApiKey!.isNotEmpty;
}
