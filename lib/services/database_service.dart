
import 'package:flutter/services.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/med_item.dart';
import 'package:fuzzywuzzy/fuzzywuzzy.dart';
import 'package:collection/collection.dart';

class DatabaseService {
  static Database? _database;
  static const String _tableName = 'meds';

  static Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  static Future<Database> _initDatabase() async {
    String path = join(await getDatabasesPath(), 'med_locations.db');
    
    // Only delete database in debug mode for fresh starts
    const bool debugMode = true; // Set to false for production
    if (debugMode) {
      await deleteDatabase(path);
      print('DB path: $path');
      print('Database deleted for fresh start (debug mode)');
    } else {
      print('DB path: $path');
      print('Using existing database (production mode)');
    }

    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  static Future<void> _onCreate(Database db, int version) async {
    print('Creating database table...');
    await db.execute('''
      CREATE TABLE $_tableName (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        dose TEXT NOT NULL,
        form TEXT NOT NULL,
        location TEXT NOT NULL,
        notes TEXT
      )
    ''');
    print('Table created successfully');

    // Load CSV data
    await _loadCsvData(db);
  }

  static Future<void> _loadCsvData(Database db) async {
    try {
      print('Loading CSV asset...');
      final String csvData = await rootBundle.loadString('assets/med_locations.csv');
      print('CSV loaded, length: ${csvData.length} characters');
      
      // Custom CSV parsing to handle location fields with commas
      final List<String> lines = csvData.split('\n');
      print('CSV parsed, ${lines.length} lines found');
      
      if (lines.isEmpty) {
        print('ERROR: CSV file is empty!');
        return;
      }
      
      print('CSV header: ${lines[0]}');
      
      // Use transaction for better performance and reliability
      await db.transaction((txn) async {
        int insertCount = 0;
        // Skip header row (index 0)
        for (int i = 1; i < lines.length; i++) {
          final line = lines[i].trim();
          if (line.isEmpty) continue;
          
          // Custom parsing: split by comma but handle location field properly
          final parts = line.split(',');
          if (parts.length >= 4) {
            final name = parts[0].trim();
            final dose = parts[1].trim();
            final form = parts[2].trim();
            
            // Location is everything from index 3 to the second-to-last part (if notes exist)
            // or to the end if no notes
            String location;
            String notes = '';
            
            if (parts.length > 4 && parts[parts.length - 1].trim().isNotEmpty) {
              // Has notes - location is everything except first 3 and last part
              location = parts.sublist(3, parts.length - 1).join(',').trim();
              notes = parts[parts.length - 1].trim();
            } else {
              // No notes - location is everything after first 3 parts
              location = parts.sublist(3).join(',').trim();
            }
            
            await txn.insert(_tableName, {
              'name': name,
              'dose': dose,
              'form': form,
              'location': location,
              'notes': notes,
            });
            insertCount++;
            
            // Debug first few entries
            if (insertCount <= 3) {
              print('Inserted: $name | $dose | $form | $location | $notes');
            }
          } else {
            print('Skipping invalid line $i: $line');
          }
        }
        print('Inserted $insertCount medication records');
      });
      
      // Verify insertion
      final count = Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM $_tableName')) ?? 0;
      print('DB verification: $count entries in database');
      
      if (count == 0) {
        print('ERROR: Database is still empty after insertion!');
      } else {
        // Show first few entries for verification
        final sample = await db.query(_tableName, limit: 3);
        print('Sample entries: $sample');
      }
      
    } catch (e, stackTrace) {
      print('Error loading CSV data: $e');
      print('Stack trace: $stackTrace');
    }
  }

  /// Batch process multiple medications at once (much faster than individual queries)
  static Future<Map<MedItem, Map<String, String>?>> batchGetLocationsForMeds(List<MedItem> medications) async {
    final db = await database;
    final results = <MedItem, Map<String, String>?>{};

    if (medications.isEmpty) return results;

    print('Batch processing ${medications.length} medications...');
    final startTime = DateTime.now();

    // Load entire database into memory once (255 entries is small enough)
    final allDbMeds = await db.query(_tableName);
    print('Loaded ${allDbMeds.length} database entries in memory');

    // Process each medication against in-memory database
    for (var med in medications) {
      String medNameLower = med.name.toLowerCase().trim();
      String medDoseLower = med.dose.toLowerCase().replaceAll(' ', '');
      String medFormLower = med.form.toLowerCase().trim();

      // Try exact match first
      final exactMatch = allDbMeds.where((row) {
        return (row['name'] as String).toLowerCase().trim() == medNameLower &&
               (row['dose'] as String).toLowerCase().replaceAll(' ', '') == medDoseLower &&
               (row['form'] as String).toLowerCase().trim() == medFormLower;
      }).firstOrNull;

      if (exactMatch != null) {
        results[med] = {
          'location': exactMatch['location'] as String? ?? '',
          'notes': exactMatch['notes'] as String? ?? '',
        };
        continue;
      }

      // Filter by prefix for fuzzy matching
      String namePrefix = medNameLower.length >= 3 ? medNameLower.substring(0, 3) : medNameLower;
      final candidateRows = allDbMeds.where((row) {
        final name = (row['name'] as String).toLowerCase();
        return name.length >= 3 && name.substring(0, 3) == namePrefix;
      }).toList();

      // Fuzzy match on filtered candidates
      Map<String, String>? bestMatch;
      double bestScore = 0.0;

      for (var row in candidateRows) {
        double nameScore = ratio(medNameLower, (row['name'] as String).toLowerCase()) / 100.0;
        if (nameScore < 0.6) continue;

        double doseScore = ratio(medDoseLower, (row['dose'] as String).replaceAll(' ', '').toLowerCase()) / 100.0;
        double formScore = ratio(medFormLower, (row['form'] as String).toLowerCase()) / 100.0;
        double overallScore = (nameScore * 0.6) + (doseScore * 0.3) + (formScore * 0.1);

        if (overallScore > bestScore && overallScore >= 0.75) {
          bestScore = overallScore;
          bestMatch = {
            'location': row['location'] as String? ?? '',
            'notes': row['notes'] as String? ?? '',
          };
          if (bestScore >= 0.95) break;
        }
      }

      results[med] = bestMatch;
    }

    final elapsed = DateTime.now().difference(startTime);
    print('Batch processed ${medications.length} medications in ${elapsed.inMilliseconds}ms');

    return results;
  }

  static Future<Map<String, String>?> getLocationAndNotesForMed(MedItem med) async {
    final db = await database;

    print('Looking for: ${med.name}, ${med.dose}, ${med.form}');

    // OPTIMIZATION 1: Try exact match first (fastest)
    String medNameLower = med.name.toLowerCase().trim();
    String medDoseLower = med.dose.toLowerCase().replaceAll(' ', '');
    String medFormLower = med.form.toLowerCase().trim();

    var exactMatch = await db.query(
      _tableName,
      where: 'LOWER(TRIM(name)) = ? AND LOWER(REPLACE(dose, " ", "")) = ? AND LOWER(TRIM(form)) = ?',
      whereArgs: [medNameLower, medDoseLower, medFormLower],
      limit: 1,
    );

    if (exactMatch.isNotEmpty) {
      print('✓ Exact match found: ${exactMatch[0]['name']}');
      return {
        'location': exactMatch[0]['location'] as String? ?? '',
        'notes': exactMatch[0]['notes'] as String? ?? '',
      };
    }

    // OPTIMIZATION 2: Filter by medication name prefix (much smaller result set)
    // Get first 3 characters of medication name for filtering
    String namePrefix = medNameLower.length >= 3 ? medNameLower.substring(0, 3) : medNameLower;

    var candidateRows = await db.query(
      _tableName,
      where: 'LOWER(SUBSTR(name, 1, 3)) = ?',
      whereArgs: [namePrefix],
    );

    print('Filtered to ${candidateRows.length} candidates (from 255 total)');

    // OPTIMIZATION 3: Only do fuzzy matching on the filtered subset
    Map<String, String>? bestMatch;
    double bestScore = 0.0;

    for (var row in candidateRows) {
      // Compute similarity scores using fuzzywuzzy
      double nameScore = ratio(medNameLower, (row['name'] as String).toLowerCase()) / 100.0;

      // Early exit if name doesn't match well enough
      if (nameScore < 0.6) continue;

      double doseScore = ratio(medDoseLower, (row['dose'] as String).replaceAll(' ', '').toLowerCase()) / 100.0;
      double formScore = ratio(medFormLower, (row['form'] as String).toLowerCase()) / 100.0;

      // Weighted average (name most important)
      double overallScore = (nameScore * 0.6) + (doseScore * 0.3) + (formScore * 0.1);

      if (overallScore > bestScore && overallScore >= 0.75) {
        bestScore = overallScore;
        bestMatch = {
          'location': row['location'] as String? ?? '',
          'notes': row['notes'] as String? ?? '',
        };
        print('New best match: ${row['name']} -> ${row['location']} (Score: ${bestScore.toStringAsFixed(2)})');

        // If we found a very good match (>95%), stop searching
        if (bestScore >= 0.95) break;
      }
    }

    if (bestMatch != null) {
      print('✓ Fuzzy match found with score: ${bestScore.toStringAsFixed(2)}');
      return bestMatch;
    }

    print('✗ No match found for: ${med.name}');
    return null;
  }
  
  static bool _isMedicationNameMatch(String input, String db) {
    // Handle specific medication name patterns
    Map<String, List<String>> medicationAliases = {
      'gabapentin': ['gabapentin'],
      'metoprolol': ['metoprolol', 'metoprololtartrate', 'metoprololsuccinate'],
      'lisinopril': ['lisinopril'],
      'levothyroxine': ['levothyroxine'],
      'furosemide': ['furosemide'],
      'pantoprazole': ['pantoprazole'],
    };
    
    for (String key in medicationAliases.keys) {
      if (medicationAliases[key]!.any((alias) => 
          input.contains(alias) || db.contains(key))) {
        return true;
      }
    }
    
    return false;
  }

  static Future<List<MedItem>> getAllMedications() async {
    final db = await database;
    final results = await db.query(_tableName);
    
    return results.map((row) => MedItem(
      name: row['name'] as String,
      dose: row['dose'] as String,
      form: row['form'] as String,
      pickAmount: 0, // Default, will be set from scanned data
      location: row['location'] as String?,
      notes: row['notes'] as String?,
    )).toList();
  }

  static Future<void> clearDatabase() async {
    final db = await database;
    await db.delete(_tableName);
    await _loadCsvData(db);
  }
}
