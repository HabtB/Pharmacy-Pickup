import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'screens/scan_screen.dart';
import 'screens/process_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_service.dart';
import 'services/storage_service.dart';
import 'theme/app_theme.dart';
import 'utils/app_logger.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    AppLogger.error('Flutter error: ${details.exception}', name: 'App');
  };

  // ProviderScope is the root of all Riverpod providers.
  // Everything inside can access providers via ref.
  // This is the only change for Phase 1 — no providers defined yet.
  runApp(const ProviderScope(child: _AppStartup()));
}

class _AppStartup extends ConsumerStatefulWidget {
  const _AppStartup();

  @override
  ConsumerState<_AppStartup> createState() => _AppStartupState();
}

class _AppStartupState extends ConsumerState<_AppStartup> {
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      try {
        await dotenv.load(fileName: ".env");
      } catch (e) {
        AppLogger.info('.env not found', name: 'App');
      }

      try {
        await Permission.camera.request();
        await Permission.photos.request();
      } catch (e) {
        AppLogger.error('Permission error: $e', name: 'App');
      }

      try {
        await ref.read(authProvider.notifier).checkAuthStatus();
      } catch (e) {
        AppLogger.error('Auth check failed: $e', name: 'App');
      }

      if (mounted) {
        setState(() {
          _ready = true;
        });
      }
    } catch (e, stack) {
      AppLogger.error('STARTUP CRASH: $e\n$stack', name: 'App');
      if (mounted) setState(() { _ready = true; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    if (!_ready) {
      return const MaterialApp(
        debugShowCheckedModeBanner: false,
        home: Scaffold(
          backgroundColor: Color(0xFF003DA5),
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                CircularProgressIndicator(color: Colors.white),
                SizedBox(height: 24),
                Text('MOUNT SINAI',
                    style: TextStyle(
                        color: Colors.white, fontSize: 22,
                        fontWeight: FontWeight.w800)),
                SizedBox(height: 4),
                Text('Pharmacy Department',
                    style: TextStyle(
                        color: Colors.white70, fontSize: 14,
                        fontWeight: FontWeight.w300)),
              ],
            ),
          ),
        ),
      );
    }

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Pharmacy Picker',
      theme: buildAppTheme(),
      home: authState.isLoggedIn ? const ModeSelectionScreen() : const LoginScreen(),
    );
  }
}

class ModeSelectionScreen extends ConsumerStatefulWidget {
  const ModeSelectionScreen({super.key});

  @override
  ConsumerState<ModeSelectionScreen> createState() => _ModeSelectionScreenState();
}

class _ModeSelectionScreenState extends ConsumerState<ModeSelectionScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _hasSavedSession = false;
  DateTime? _sessionTimestamp;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _checkSavedSession();
  }

  Future<void> _checkSavedSession() async {
    final hasSession = await StorageService.hasSavedSession();
    final timestamp = await StorageService.getSessionTimestamp();
    if (mounted) {
      setState(() {
        _hasSavedSession = hasSession;
        _sessionTimestamp = timestamp;
      });
    }
  }

  Future<void> _resumeSession() async {
    final medications = await StorageService.loadSession();
    if (medications != null && medications.isNotEmpty && mounted) {
      AppLogger.info('Resuming session with ${medications.length} items', name: 'ModeSelection');
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ProcessScreen(
            mode: 'floor_stock',
            scannedImages: null,
          ),
        ),
      );
    }
  }

  Future<void> _handleLogout() async {
    await ref.read(authProvider.notifier).logout();
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('MOUNT SINAI',
                style: GoogleFonts.inter(
                    fontWeight: FontWeight.w800, fontSize: 16)),
            Text('Pharmacy Department',
                style: GoogleFonts.inter(
                    fontSize: 12, fontWeight: FontWeight.w300)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: _handleLogout,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.inventory_2_outlined), text: 'Floor Stock'),
            Tab(
                icon: Icon(Icons.local_pharmacy_outlined),
                text: 'Cart-Fill'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildModeTab(
            mode: 'floor_stock',
            title: 'Floor Stock Distribution',
            subtitle: 'Bulk picks for floor-level replenishment',
            features: [
              _Feature(Icons.table_chart, 'Scan BD pick lists'),
              _Feature(Icons.merge_type, 'Aggregates by floor'),
              _Feature(Icons.route, 'Optimized pick route'),
            ],
            buttonText: 'Start Floor Stock Scan',
            icon: Icons.inventory_2_rounded,
            gradientColors: [AppColors.msBlue, AppColors.primaryDark],
          ),
          _buildModeTab(
            mode: 'cart_fill',
            title: '24-Hour Cart-Fill',
            subtitle: 'Patient-specific medication preparation',
            features: [
              _Feature(Icons.calculate, 'Auto-calculates 24hr qty'),
              _Feature(Icons.person, 'Aggregates by patient'),
              _Feature(Icons.medication_liquid, 'Sig-based dosing'),
            ],
            buttonText: 'Start Cart-Fill Scan',
            icon: Icons.local_pharmacy_rounded,
            gradientColors: [AppColors.accent, const Color(0xFFA0006A)],
          ),
        ],
      ),
      floatingActionButton: _hasSavedSession
          ? FloatingActionButton.extended(
              onPressed: _resumeSession,
              icon: const Icon(Icons.restore),
              label: Text(
                'Resume Session\n${_sessionTimestamp != null ? _formatDate(_sessionTimestamp!) : ""}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 10),
              ),
              backgroundColor: AppColors.caution,
              foregroundColor: AppColors.textPrimary,
            )
          : null,
    );
  }

  String _formatDate(DateTime date) {
    return "${date.hour}:${date.minute.toString().padLeft(2, '0')} ${date.month}/${date.day}";
  }

  Widget _buildModeTab({
    required String mode,
    required String title,
    required String subtitle,
    required List<_Feature> features,
    required String buttonText,
    required IconData icon,
    required List<Color> gradientColors,
  }) {
    return Container(
      color: AppColors.surface,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 16),

            // Hero icon card with gradient
            Container(
              width: 110,
              height: 110,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: gradientColors,
                ),
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: gradientColors.first.withValues(alpha: 0.35),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Icon(icon, size: 56, color: Colors.white),
            ),
            const SizedBox(height: 28),

            // Title
            Text(
              title,
              style: GoogleFonts.inter(
                fontSize: 26,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                fontSize: 15,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),

            // Features list
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.divider),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                children: features
                    .map((f) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: gradientColors.first
                                      .withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(f.icon,
                                    size: 20, color: gradientColors.first),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Text(
                                  f.label,
                                  style: GoogleFonts.inter(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w500,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),

            const SizedBox(height: 32),

            // CTA Button
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                onPressed: () async {
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => ScanScreen(mode: mode),
                    ),
                  );
                  _checkSavedSession();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: gradientColors.first,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 0,
                ),
                icon: const Icon(Icons.camera_alt_rounded),
                label: Text(
                  buttonText,
                  style: GoogleFonts.inter(
                      fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _Feature {
  final IconData icon;
  final String label;
  const _Feature(this.icon, this.label);
}
