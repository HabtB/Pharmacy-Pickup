
import 'package:flutter/services.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/med_item.dart';
import 'package:fuzzywuzzy/fuzzywuzzy.dart';

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
    
    // Force delete for testing (remove later if needed)
    await deleteDatabase(path);
    print('DB path: $path');
    print('Database deleted for fresh start');

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

  static Future<Map<String, String>?> getLocationAndNotesForMed(MedItem med) async {
    final db = await database;
    
    // Use the medication directly for matching
    MedItem cleanedMed = med;
    
    List<Map<String, Object?>> allRows = await db.query(_tableName);
    
    Map<String, String>? bestMatch;
    double bestScore = 0.0;
    
    print('Looking for: ${cleanedMed.name}, ${cleanedMed.dose}, ${cleanedMed.form}');
    print('Database has ${allRows.length} entries');

    for (var row in allRows) {
      // Compute similarity scores using fuzzywuzzy
      double nameScore = ratio(cleanedMed.name.toLowerCase(), (row['name'] as String).toLowerCase()) / 100.0;
      double doseScore = ratio(cleanedMed.dose.replaceAll(' ', '').toLowerCase(), (row['dose'] as String).replaceAll(' ', '').toLowerCase()) / 100.0;
      double formScore = ratio(cleanedMed.form.toLowerCase(), (row['form'] as String).toLowerCase()) / 100.0;

      // Weighted average (name most important)
      double overallScore = (nameScore * 0.6) + (doseScore * 0.3) + (formScore * 0.1);

      // Debug: Print promising matches
      if (overallScore > 0.5) {
        print('Candidate: ${row['name']} (${row['dose']} ${row['form']}) - Score: ${overallScore.toStringAsFixed(2)}');
      }

      if (overallScore > bestScore && overallScore >= 0.75) { // Threshold 0.75 (75% similarity)
        bestScore = overallScore;
        bestMatch = {
          'location': row['location'] as String? ?? '',
          'notes': row['notes'] as String? ?? '',
        };
        print('New best match: ${row['name']} -> ${row['location']} (Score: ${bestScore.toStringAsFixed(2)})');
      }
    }

    if (bestMatch != null) {
      print('Final match found with score: ${bestScore.toStringAsFixed(2)}');
    } else {
      print('No match found for: ${med.name} (best score was ${bestScore.toStringAsFixed(2)})');
    }
    
    return bestMatch;
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
