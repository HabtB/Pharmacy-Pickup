import 'package:flutter/foundation.dart';

/// Controller to manage the state of long-running processing tasks
class ProcessingController extends ChangeNotifier {
  bool _isPaused = false;
  bool _isStopped = false;
  bool _isCancelled = false;

  bool get isPaused => _isPaused;
  bool get isStopped => _isStopped;
  bool get isCancelled => _isCancelled;

  /// Pause the processing
  /// The current operation will finish, but next operations will wait
  void pause() {
    if (!_isStopped) {
      _isPaused = true;
      notifyListeners();
    }
  }

  /// Resume processing
  void resume() {
    if (_isPaused) {
      _isPaused = false;
      notifyListeners();
    }
  }

  /// Stop processing strictly but keep results so far
  /// effectively synonymous with finishing early
  void stop() {
    _isStopped = true;
    _isPaused = false; // Unpause to let loop exit
    notifyListeners();
  }

  /// Cancel processing entirely (discard results)
  void cancel() {
    _isCancelled = true;
    _isStopped = true;
    _isPaused = false;
    notifyListeners();
  }
  
  /// Reset controller state
  void reset() {
    _isPaused = false;
    _isStopped = false;
    _isCancelled = false;
    notifyListeners();
  }
}
