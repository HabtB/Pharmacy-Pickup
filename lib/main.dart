import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:permission_handler/permission_handler.dart';
import 'screens/scan_screen.dart';
import 'services/test_ocr_service.dart';
import 'services/database_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");
  
  // Request camera and photo permissions
  await Permission.camera.request();
  await Permission.photos.request();
  
  // Debug: Print loaded environment variables (API key hidden for security)
  print('=== ENV DEBUG ===');
  print('API Key loaded: ${dotenv.env['GROK_API_KEY'] != null && dotenv.env['GROK_API_KEY']!.isNotEmpty}');
  print('API Key length: ${dotenv.env['GROK_API_KEY']?.length ?? 0}');
  // Database initializes automatically on first access
  
  // Run OCR parsing test with user-provided medication label
  await TestOCRService.testMedicationLabelParsing();
  await TestOCRService.testExpectedOCRText();
  
  runApp(const PharmacyPickerApp());
}

class PharmacyPickerApp extends StatelessWidget {
  const PharmacyPickerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pharmacy Picker',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const ModeSelectionScreen(),
    );
  }
}

class ModeSelectionScreen extends StatefulWidget {
  const ModeSelectionScreen({super.key});

  @override
  State<ModeSelectionScreen> createState() => _ModeSelectionScreenState();
}

class _ModeSelectionScreenState extends State<ModeSelectionScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
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
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Pharmacy Picker'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(Icons.inventory),
              text: 'Floor Stock',
            ),
            Tab(
              icon: Icon(Icons.local_pharmacy),
              text: 'Cart-Fill',
            ),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Floor Stock Tab
          _buildModeTab(
            mode: 'floor_stock',
            title: 'Floor Stock Distribution',
            description: 'Bulk medication picks for floor-level distribution. Scan tabular lists (like BD pick lists) to aggregate medications by floor.',
            examples: [
              '• Bulk picks for 6W, 7E1 (SICU), etc.',
              '• Aggregates same meds across floors',
              '• Optimized for floor stock replenishment',
            ],
            buttonText: 'Start Floor Stock Scan',
            icon: Icons.inventory,
            color: Colors.blue,
          ),
          // Cart-Fill Tab
          _buildModeTab(
            mode: 'cart_fill',
            title: '24-Hour Cart-Fill',
            description: 'Patient-specific medication preparation for 24-hour cart distribution. Scan patient labels with sig instructions.',
            examples: [
              '• Calculates 24hr quantities from sig (bid=2, tid=3)',
              '• Aggregates by patient and floor',
              '• Optimized for cart-fill workflows',
            ],
            buttonText: 'Start Cart-Fill Scan',
            icon: Icons.local_pharmacy,
            color: Colors.green,
          ),
        ],
      ),
    );
  }

  Widget _buildModeTab({
    required String mode,
    required String title,
    required String description,
    required List<String> examples,
    required String buttonText,
    required IconData icon,
    required Color color,
  }) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Mode icon and title
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  icon,
                  size: 32,
                  color: color,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          // Description
          Text(
            description,
            style: const TextStyle(
              fontSize: 16,
              height: 1.5,
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Examples
          const Text(
            'Key Features:',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          
          ...examples.map((example) => Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: Text(
              example,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey.shade700,
                height: 1.4,
              ),
            ),
          )),
          
          const SizedBox(height: 32),
          
          // Start button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ScanScreen(mode: mode),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: color,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: const TextStyle(fontSize: 18),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: Text(buttonText),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Info card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 20,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'How it works',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey.shade700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  mode == 'floor_stock' 
                    ? 'Scan tabular medication lists. The app will detect floors (6W, 7E1, etc.) and aggregate quantities by location for efficient bulk picking.'
                    : 'Scan patient medication labels with sig instructions. The app will calculate 24-hour quantities and organize by patient and floor for cart preparation.',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey.shade600,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
