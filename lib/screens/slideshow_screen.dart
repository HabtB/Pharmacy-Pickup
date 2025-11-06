import 'package:carousel_slider/carousel_slider.dart';
import 'package:flutter/material.dart';
import '../models/med_item.dart';

class SlideshowScreen extends StatefulWidget {
  final List<MedItem> medications;

  const SlideshowScreen({super.key, required this.medications});

  @override
  State<SlideshowScreen> createState() => _SlideshowScreenState();
}

class _SlideshowScreenState extends State<SlideshowScreen> {
  int currentIndex = 0;
  List<bool> completedItems = [];
  CarouselSliderController carouselController = CarouselSliderController();
  int _currentTab = 0;
  Map<String, List<int>> locationGroups =
      {}; // location -> list of medication indices
  List<String> locationOrder = []; // ordered list of locations

  @override
  void initState() {
    super.initState();
    completedItems = List.filled(widget.medications.length, false);
    _buildLocationGroups();
  }

  // Build location groups from medications list
  void _buildLocationGroups() {
    locationGroups.clear();
    locationOrder.clear();

    for (int i = 0; i < widget.medications.length; i++) {
      String location = widget.medications[i].location ?? 'Unknown Location';

      if (!locationGroups.containsKey(location)) {
        locationGroups[location] = [];
        locationOrder.add(location);
      }
      locationGroups[location]!.add(i);
    }
  }

  // Get current location info
  String _getCurrentLocation() {
    if (widget.medications.isEmpty) return 'Unknown Location';
    return widget.medications[currentIndex].location ?? 'Unknown Location';
  }

  // Get current location group stats
  Map<String, dynamic> _getCurrentLocationStats() {
    String currentLocation = _getCurrentLocation();
    List<int> groupIndices = locationGroups[currentLocation] ?? [];
    int currentPositionInGroup = groupIndices.indexOf(currentIndex) + 1;
    int totalInGroup = groupIndices.length;
    int completedInGroup = groupIndices
        .where((idx) => completedItems[idx])
        .length;
    int locationNumber = locationOrder.indexOf(currentLocation) + 1;
    int totalLocations = locationOrder.length;

    return {
      'location': currentLocation,
      'currentPositionInGroup': currentPositionInGroup,
      'totalInGroup': totalInGroup,
      'completedInGroup': completedInGroup,
      'locationNumber': locationNumber,
      'totalLocations': totalLocations,
    };
  }

  // Check if we're starting a new location group
  bool _isNewLocationGroup(int index) {
    if (index == 0) return true;
    if (index >= widget.medications.length) return false;

    String currentLocation =
        widget.medications[index].location ?? 'Unknown Location';
    String previousLocation =
        widget.medications[index - 1].location ?? 'Unknown Location';

    return currentLocation != previousLocation;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.medications.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Pick Slideshow'),
          backgroundColor: Colors.blue.shade700,
          foregroundColor: Colors.white,
        ),
        body: const Center(
          child: Text(
            'No medications to pick',
            style: TextStyle(fontSize: 18, color: Colors.grey),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Pick Slideshow (${currentIndex + 1}/${widget.medications.length})',
        ),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() {
                completedItems = List.filled(widget.medications.length, false);
                currentIndex = 0;
              });
            },
          ),
        ],
      ),
      body: _currentTab == 0
          ? _buildSlideshowTab()
          : PreparationTab(medications: widget.medications),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentTab,
        onTap: (index) => setState(() => _currentTab = index),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.slideshow), label: 'Slides'),
          BottomNavigationBarItem(
            icon: Icon(Icons.build),
            label: 'Preparation',
          ),
        ],
      ),
    );
  }

  Widget _buildSlideshowTab() {
    Map<String, dynamic> locationStats = _getCurrentLocationStats();

    return Column(
      children: [
        // Location Progress Banner
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.green.shade700, Colors.green.shade900],
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.green.withOpacity(0.3),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            children: [
              Icon(Icons.location_on, color: Colors.white, size: 24),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Location ${locationStats['locationNumber']} of ${locationStats['totalLocations']}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.white70,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Text(
                      locationStats['location'],
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Text(
                  '${locationStats['completedInGroup']}/${locationStats['totalInGroup']} picked',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),

        // Progress indicator
        Container(
          padding: const EdgeInsets.all(16),
          child: LinearProgressIndicator(
            value: (currentIndex + 1) / widget.medications.length,
            backgroundColor: Colors.grey.shade300,
            valueColor: AlwaysStoppedAnimation<Color>(Colors.blue.shade700),
          ),
        ),

        // Slideshow
        Expanded(
          child: CarouselSlider.builder(
            carouselController: carouselController,
            itemCount: widget.medications.length,
            options: CarouselOptions(
              height: double.infinity,
              enlargeCenterPage: true,
              enableInfiniteScroll: false,
              viewportFraction: 0.9,
              onPageChanged: (index, reason) {
                setState(() {
                  currentIndex = index;
                });
              },
            ),
            itemBuilder: (context, index, realIndex) {
              final med = widget.medications[index];
              final isCompleted = completedItems[index];
              final bool isNewLocation = _isNewLocationGroup(index);

              // Check for special medication types
              bool isDecimal =
                  med.calculatedQty % 1 != 0 || med.calculatedQty < 1;
              bool isSyrupSusp =
                  med.form.toLowerCase().contains('syrup') ||
                  med.form.toLowerCase().contains('susp') ||
                  med.form.toLowerCase().contains('suspension');
              bool isFridge = med.location?.startsWith('Front Fridge') ?? false;

              // Parse floor breakdown from notes
              Map<String, int>? floorBreakdown = _parseFloorBreakdown(
                med.notes,
              );
              String? originalNotes = _extractOriginalNotes(med.notes);

              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 16),
                child: Card(
                  elevation: 8,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: BorderSide(
                      color: isCompleted ? Colors.green : Colors.blue.shade700,
                      width: 2,
                    ),
                  ),
                  child: Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: isCompleted
                            ? [Colors.green.shade50, Colors.green.shade100]
                            : (isDecimal || isSyrupSusp || isFridge)
                            ? [Colors.yellow.shade50, Colors.yellow.shade100]
                            : [Colors.blue.shade50, Colors.blue.shade100],
                      ),
                    ),
                    child: CustomScrollView(
                      shrinkWrap: true,
                      slivers: [
                        SliverFillRemaining(
                          hasScrollBody: false,
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.center,
                            children: [
                              // Location
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 8,
                                ),
                                decoration: BoxDecoration(
                                  color: med.location != null
                                      ? Colors.blue.shade700
                                      : Colors.red.shade600,
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Text(
                                  med.location ??
                                      'Unknown Location - Check Manually',
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ),

                              const SizedBox(height: 24),

                              // Medication details with emphasis for special types
                              Text(
                                '${med.name} ${med.dose} ${med.form}',
                                style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: (isDecimal || isSyrupSusp)
                                      ? Colors.red.shade700
                                      : Colors.black,
                                ),
                                textAlign: TextAlign.center,
                              ),

                              // Special badges for emphasis
                              if (isDecimal) ...[
                                const SizedBox(height: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.red.shade600,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Text(
                                    'DECIMAL DOSE - Use Cup',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                              if (isSyrupSusp) ...[
                                const SizedBox(height: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.orange.shade600,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Text(
                                    'LIQUID - Use Syringe',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                              if (isFridge) ...[
                                const SizedBox(height: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.shade600,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Text(
                                    'REFRIGERATE',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                              const SizedBox(height: 8),
                              Text(
                                'Pick ${med.pickAmount} total',
                                style: TextStyle(
                                  fontSize: 20,
                                  color: (isDecimal || isSyrupSusp)
                                      ? Colors.red.shade600
                                      : Colors.grey,
                                  fontWeight: (isDecimal || isSyrupSusp)
                                      ? FontWeight.bold
                                      : FontWeight.normal,
                                ),
                                textAlign: TextAlign.center,
                              ),

                              // Floor Breakdown Section (NEW DEDICATED UI)
                              if (floorBreakdown != null &&
                                  floorBreakdown.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                      colors: [
                                        Colors.blue.shade700,
                                        Colors.blue.shade900,
                                      ],
                                    ),
                                    borderRadius: BorderRadius.circular(12),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.blue.withOpacity(0.3),
                                        blurRadius: 8,
                                        offset: const Offset(0, 4),
                                      ),
                                    ],
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.business,
                                            color: Colors.white,
                                            size: 18,
                                          ),
                                          const SizedBox(width: 8),
                                          Text(
                                            'Floor Distribution',
                                            style: TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.bold,
                                              color: Colors.white,
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Wrap(
                                        spacing: 8,
                                        runSpacing: 8,
                                        children: floorBreakdown.entries.map((
                                          entry,
                                        ) {
                                          return Container(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 12,
                                              vertical: 6,
                                            ),
                                            decoration: BoxDecoration(
                                              color: Colors.white,
                                              borderRadius:
                                                  BorderRadius.circular(20),
                                              border: Border.all(
                                                color: Colors.blue.shade300,
                                                width: 2,
                                              ),
                                            ),
                                            child: Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Container(
                                                  padding:
                                                      const EdgeInsets.symmetric(
                                                        horizontal: 8,
                                                        vertical: 2,
                                                      ),
                                                  decoration: BoxDecoration(
                                                    color: Colors.blue.shade700,
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                          12,
                                                        ),
                                                  ),
                                                  child: Text(
                                                    entry.key,
                                                    style: const TextStyle(
                                                      fontSize: 12,
                                                      fontWeight:
                                                          FontWeight.bold,
                                                      color: Colors.white,
                                                    ),
                                                  ),
                                                ),
                                                const SizedBox(width: 8),
                                                Icon(
                                                  Icons.arrow_forward,
                                                  size: 14,
                                                  color: Colors.blue.shade700,
                                                ),
                                                const SizedBox(width: 4),
                                                Text(
                                                  '${entry.value} ${_getPluralForm(entry.value, med.form)}',
                                                  style: TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: FontWeight.bold,
                                                    color: Colors.blue.shade900,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          );
                                        }).toList(),
                                      ),
                                    ],
                                  ),
                                ),
                              ],

                              // Patient Breakdown Section (for cart-fill mode)
                              if (med.notes != null &&
                                  med.notes!.contains('Breakdown:'))
                                Padding(
                                  padding: const EdgeInsets.only(top: 12.0),
                                  child: Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.purple.shade50,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: Colors.purple.shade200,
                                        width: 2,
                                      ),
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Icon(
                                              Icons.person,
                                              color: Colors.purple.shade700,
                                              size: 16,
                                            ),
                                            const SizedBox(width: 6),
                                            Text(
                                              'Patient Distribution',
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: FontWeight.bold,
                                                color: Colors.purple.shade700,
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          med.notes!.split('Breakdown: ').last,
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: Colors.purple.shade900,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),

                              const SizedBox(height: 20),

                              Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: Colors.orange.shade100,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: Colors.orange.shade300,
                                  ),
                                ),
                                child: Text(
                                  'Pick: ${med.pickAmount}',
                                  style: TextStyle(
                                    fontSize: 24,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.orange.shade800,
                                  ),
                                ),
                              ),

                              // Warning message for formula mismatch
                              if (med.warning != null && med.warning!.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                GestureDetector(
                                  onTap: () async {
                                    // Show dialog to manually enter correct amount
                                    final TextEditingController controller = TextEditingController(text: med.pickAmount.toString());
                                    final newAmount = await showDialog<int>(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        title: const Text('Enter Correct Amount'),
                                        content: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(med.warning!),
                                            const SizedBox(height: 16),
                                            TextField(
                                              controller: controller,
                                              keyboardType: TextInputType.number,
                                              autofocus: true,
                                              decoration: const InputDecoration(
                                                labelText: 'Pick Amount',
                                                border: OutlineInputBorder(),
                                              ),
                                            ),
                                          ],
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.pop(context),
                                            child: const Text('Cancel'),
                                          ),
                                          ElevatedButton(
                                            onPressed: () {
                                              final amount = int.tryParse(controller.text);
                                              Navigator.pop(context, amount);
                                            },
                                            child: const Text('Save'),
                                          ),
                                        ],
                                      ),
                                    );

                                    if (newAmount != null && newAmount != med.pickAmount) {
                                      setState(() {
                                        widget.medications[index] = med.copyWith(
                                          pickAmount: newAmount,
                                          warning: null, // Clear warning after manual correction
                                        );
                                      });
                                    }
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.amber.shade50,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: Colors.amber.shade700,
                                        width: 2,
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.error_outline,
                                          color: Colors.amber.shade900,
                                          size: 24,
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Text(
                                            med.warning!,
                                            style: TextStyle(
                                              fontSize: 14,
                                              fontWeight: FontWeight.bold,
                                              color: Colors.amber.shade900,
                                            ),
                                          ),
                                        ),
                                        Icon(
                                          Icons.edit,
                                          color: Colors.amber.shade900,
                                          size: 20,
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],

                              // Safety notes (only show original notes, not floor breakdown data)
                              if (originalNotes != null &&
                                  originalNotes.isNotEmpty) ...[
                                const SizedBox(height: 20),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.red.shade50,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                      color: Colors.red.shade300,
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                        Icons.warning,
                                        color: Colors.red.shade600,
                                        size: 20,
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'CAUTION: $originalNotes',
                                          style: TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.red.shade700,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],

                              const SizedBox(height: 24),

                              // Completion checkbox
                              ElevatedButton.icon(
                                onPressed: () {
                                  setState(() {
                                    completedItems[index] =
                                        !completedItems[index];
                                  });

                                  // Auto-advance to next card when marked complete
                                  if (completedItems[index] &&
                                      index < widget.medications.length - 1) {
                                    Future.delayed(
                                      const Duration(milliseconds: 500),
                                      () {
                                        carouselController.nextPage();
                                      },
                                    );
                                  }
                                },
                                icon: Icon(
                                  isCompleted
                                      ? Icons.check_circle
                                      : Icons.radio_button_unchecked,
                                  color: Colors.white,
                                ),
                                label: Text(
                                  isCompleted ? 'Completed' : 'Mark Complete',
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: isCompleted
                                      ? Colors.green
                                      : Colors.blue.shade700,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 24,
                                    vertical: 12,
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(25),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),

        // Summary
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            border: Border(top: BorderSide(color: Colors.grey.shade300)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildSummaryItem(
                'Total Items',
                widget.medications.length.toString(),
                Colors.blue.shade700,
              ),
              _buildSummaryItem(
                'Completed',
                completedItems
                    .where((completed) => completed)
                    .length
                    .toString(),
                Colors.green.shade700,
              ),
              _buildSummaryItem(
                'Remaining',
                completedItems
                    .where((completed) => !completed)
                    .length
                    .toString(),
                Colors.orange.shade700,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryItem(String label, String value, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
      ],
    );
  }

  // Parse floor breakdown from notes
  // Format: "FLOOR_BREAKDOWN: 8E-1=7, 8E-2=4"
  Map<String, int>? _parseFloorBreakdown(String? notes) {
    if (notes == null || !notes.contains('FLOOR_BREAKDOWN:')) return null;

    try {
      // Extract the floor breakdown section
      String breakdownSection = notes.split('FLOOR_BREAKDOWN:').last.trim();
      if (breakdownSection.contains('|||')) {
        breakdownSection = breakdownSection
            .split('|||')
            .last
            .split('FLOOR_BREAKDOWN:')
            .last
            .trim();
      }

      Map<String, int> breakdown = {};
      List<String> pairs = breakdownSection.split(',');

      for (String pair in pairs) {
        pair = pair.trim();
        if (pair.contains('=')) {
          List<String> parts = pair.split('=');
          if (parts.length == 2) {
            String floor = parts[0].trim();
            int quantity = int.tryParse(parts[1].trim()) ?? 0;
            breakdown[floor] = quantity;
          }
        }
      }

      return breakdown.isNotEmpty ? breakdown : null;
    } catch (e) {
      print('Error parsing floor breakdown: $e');
      return null;
    }
  }

  // Extract original notes (before the floor breakdown data)
  String? _extractOriginalNotes(String? notes) {
    if (notes == null || notes.isEmpty) return null;

    // If notes contain the separator, extract only the part before it
    if (notes.contains('|||')) {
      String originalPart = notes.split('|||').first.trim();
      return originalPart.isNotEmpty ? originalPart : null;
    }

    // If notes contain floor breakdown but no separator, return null (it's only breakdown data)
    if (notes.contains('FLOOR_BREAKDOWN:')) {
      return null;
    }

    // Otherwise, return the notes as-is
    return notes;
  }

  // Get plural form of medication form
  String _getPluralForm(int amount, String form) {
    if (amount == 1) return form;

    if (form.toLowerCase() == 'tablet') return 'tablets';
    if (form.toLowerCase() == 'capsule') return 'capsules';
    if (form.toLowerCase() == 'bag') return 'bags';
    if (form.toLowerCase() == 'vial') return 'vials';
    if (form.toLowerCase() == 'drop') return 'drops';
    if (form.toLowerCase() == 'solution') return 'solution';
    if (form.toLowerCase() == 'liquid') return 'liquid';
    if (form.toLowerCase() == 'packet') return 'packets';

    return '${form}s';
  }
}

class PreparationTab extends StatelessWidget {
  final List<MedItem> medications;

  const PreparationTab({super.key, required this.medications});

  @override
  Widget build(BuildContext context) {
    Map<String, List<String>> cupNeeds =
        {}; // e.g., 'cups': ['Acetazolamide (0.5)', 'Nicotine (1.5)']
    Map<String, List<String>> syringeNeeds =
        {}; // e.g., '3mL syringes': ['Suspension A', 'Suspension B']
    List<String> fridgeItems = [];

    int cupCount = 0;
    int syringe3mlCount = 0;
    int syringe2mlCount = 0;

    for (var med in medications) {
      bool isDecimal = med.calculatedQty % 1 != 0 || med.calculatedQty < 1;
      bool isSuspension =
          med.form.toLowerCase().contains('suspension') ||
          med.form.toLowerCase().contains('susp');
      bool isSyrup = med.form.toLowerCase().contains('syrup');
      bool isFridge = med.location?.startsWith('Front Fridge') ?? false;

      if (isDecimal) {
        cupCount += med.calculatedQty.ceil(); // e.g., 0.5 → 1 cup
        cupNeeds
            .putIfAbsent('cups', () => [])
            .add('${med.name} (${med.calculatedQty})');
      }
      if (isSuspension) {
        syringe3mlCount += 1;
        syringeNeeds.putIfAbsent('3mL syringes', () => []).add(med.name);
      }
      if (isSyrup) {
        syringe2mlCount += 1;
        syringeNeeds.putIfAbsent('2mL syringes', () => []).add(med.name);
      }
      if (isFridge) {
        fridgeItems.add('${med.name} ${med.dose}');
      }
    }

    List<Widget> alerts = [];

    if (cupCount > 0) {
      alerts.add(
        _buildAlertCard(
          icon: Icons.local_cafe,
          title: 'Dosage Cups Required',
          message: '$cupCount cups for ${cupNeeds['cups']!.join(', ')}',
          color: Colors.orange,
        ),
      );
    }

    if (syringe3mlCount > 0) {
      alerts.add(
        _buildAlertCard(
          icon: Icons.medical_services,
          title: '3mL Syringes Required',
          message:
              '$syringe3mlCount three mL syringes for ${syringeNeeds['3mL syringes']!.join(', ')}',
          color: Colors.purple,
        ),
      );
    }

    if (syringe2mlCount > 0) {
      alerts.add(
        _buildAlertCard(
          icon: Icons.medical_services,
          title: '2mL Syringes Required',
          message:
              '$syringe2mlCount two mL syringes for ${syringeNeeds['2mL syringes']!.join(', ')}',
          color: Colors.deepPurple,
        ),
      );
    }

    if (fridgeItems.isNotEmpty) {
      alerts.add(
        _buildAlertCard(
          icon: Icons.ac_unit,
          title: 'Refrigeration Required',
          message: 'REFRIGERATE: ${fridgeItems.join(', ')}',
          color: Colors.blue,
          isUrgent: true,
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Preparation Requirements',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.blue.shade700,
            ),
          ),
          const SizedBox(height: 16),

          if (alerts.isEmpty)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.check_circle,
                    size: 64,
                    color: Colors.green.shade600,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No special preparation needed',
                    style: TextStyle(
                      fontSize: 18,
                      color: Colors.green.shade600,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'All medications are standard tablets/capsules',
                    style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                  ),
                ],
              ),
            )
          else
            Expanded(
              child: ListView.separated(
                itemCount: alerts.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: 12),
                itemBuilder: (context, index) => alerts[index],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAlertCard({
    required IconData icon,
    required String title,
    required String message,
    required Color color,
    bool isUrgent = false,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isUrgent ? Colors.red : color,
          width: isUrgent ? 2 : 1,
        ),
      ),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              isUrgent ? Colors.red.shade50 : (color as MaterialColor).shade50,
              isUrgent
                  ? Colors.red.shade100
                  : (color as MaterialColor).shade100,
            ],
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isUrgent
                    ? Colors.red.shade600
                    : (color as MaterialColor).shade600,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: isUrgent
                          ? Colors.red.shade800
                          : (color as MaterialColor).shade800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    message,
                    style: TextStyle(
                      fontSize: 14,
                      color: isUrgent
                          ? Colors.red.shade700
                          : (color as MaterialColor).shade700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
