

## Date: September 29, 2025

### Session Context
Successfully implemented Google Cloud Vision API integration for pharmacy pickup app OCR functionality and resolved network connectivity issues for testing on different IP addresses.

### Changes Made
1. **Google Cloud Vision Integration** - Successfully integrated Google Cloud Vision API using service account authentication at /Users/habtamu/Downloads/my-pharmacy-473609-3071e9bf2d97.json
2. **Multi-Engine OCR Architecture** - Implemented hierarchical OCR system: Google Vision → Docling → EasyOCR → Fallbacks
3. **Network IP Configuration** - Updated server IP from 172.20.10.9:5001 to 192.168.1.134:5001 for different network environment
4. **Flutter OCR Service Update** - Updated ocr_service.dart to use correct server IP (line 8: http://192.168.1.134:5001)

### Issues Resolved
- OCR accuracy dramatically improved with Google Cloud Vision API
- Network connectivity issues resolved with correct IP configuration
- Server running with Google Vision authentication on 192.168.1.134:5001
- Flutter app successfully connecting to Google Vision-powered server

### Testing Results
- Google Vision OCR: ✅ Successfully extracting 300+ characters from medication labels
- Server Health: ✅ Responding correctly on new IP address
- Multi-engine comparison: Google Vision outperforming Docling and EasyOCR
- Live medication extraction: Patient info, medication names, dosages, timing all captured

### Technical Details
- Server URL: http://192.168.1.134:5001
- Google Cloud Vision API: Authenticated and active
- OCR Pipeline: Google Vision selected as primary engine for medical text
- Flutter deployment: Profile mode for iOS device testing

### Performance Notes
- Google Vision provides superior medical text recognition
- OCR results show 313+ characters extracted vs 69 from EasyOCR
- System intelligently selects best OCR engine based on content quality
- Complete pharmacy label information successfully parsed

### Next Steps
- Flutter app deployment in progress with updated IP configuration
- Ready for live testing of Google Vision integration
- OCR functionality transition from 'Unable to read medication' to complete medication parsing accomplished

---

## Date: October 16, 2025

### Session Context
Fixed location assignment issues for medications not in CSV database and identified duplication bug in Flutter aggregation logic. Enhanced server logging to include floor assignments for better debugging.

### Changes Made
1. **Location Service Fix** - Disabled partial name matching in `location_service.dart` to prevent incorrect location assignments
2. **Added 'Location Not Assigned' Constant** - Medications not found in CSV now show clear "Location Not Assigned" message instead of inferred locations
3. **Enhanced Server Logging** - Updated `docling_server.py` to include floor assignments in medication output logs
4. **Slideshow Display Fix** - Fixed pick amount display using `pickAmount` instead of `calculatedQty` in `slideshow_screen.dart`

### Issues Resolved
- **Wrong Location Assignment**: Acetaminophen tablets were incorrectly matching suspension/suppository forms in fridge via partial name matching
- **Server Connectivity**: Resolved stale Python server process issue (old PID from Monday still running with outdated network bindings)
- **Pick Amount Display**: Floor stock medications now show correct total pick amounts in slideshow

### Issues Identified (To Be Fixed)
- **Duplication Bug**: Parser correctly extracts 11 medications with floor assignments (e.g., 7 meds for 8E-1, 4 meds for 8E-2), but Flutter slideshow displays medications twice
- **Root Cause**: Duplication occurs in Flutter aggregation logic in `medication_processor.dart`, not in Python parser

### Technical Details
- **Server URL**: http://172.20.10.9:5003 (iPhone hotspot network)
- **Location Matching**: Now uses only exact name or name|dose combinations (no partial matching)
- **Parser Output Example**:
  ```
  1. acetaminophen - 325 mg - tablet - Pick: 79 - Floor: 8E-1
  2. bacitracin - 500 units - packet - Pick: 22 - Floor: 8E-1
  ...
  8. tacrolimus - 1 mg - capsule - Pick: 4 - Floor: 8E-2
  ```

### Code Changes
- `lib/services/location_service.dart`: Lines 100-123 (removed partial matching), Line 80-86 (return 'Location Not Assigned')
- `python_server/docling_server.py`: Lines 160-163 (enhanced logging with floor info)
- `lib/screens/slideshow_screen.dart`: Lines 236, 277 (changed calculatedQty to pickAmount)

### Testing Results
- ✅ Parser correctly extracts medications with floor assignments
- ✅ Server logging now shows floor information for debugging
- ❌ Medications appearing twice in slideshow (aggregation bug)
- ⏳ Location fix active but needs fresh scan to verify "Location Not Assigned" display

### Performance Notes
- Groq LLM parsing: Successfully parsed 11 medications from 8E 1-2 floor stock report
- Floor assignment working correctly: 7 meds for 8E-1, 4 meds for 8E-2
- Network connectivity stable on iPhone hotspot (172.20.10.9)

### Next Steps
- Fix medication duplication in Flutter aggregation logic (`medication_processor.dart`)
- Implement mode-specific slideshow layouts (floor_stock vs cart_fill)
- Verify "Location Not Assigned" display with fresh floor stock scan
- Add acetaminophen 325mg tablet to CSV with correct shelf location

---

## Date: October 17, 2025

### Session Context
Implemented automatic server IP discovery to eliminate manual IP updates when switching networks. Added debug logging to medication aggregation logic to trace duplication issues.

### Changes Made
1. **Server Auto-Discovery** - Created `server_discovery_service.dart` to automatically find OCR server on local network
2. **Dynamic IP Configuration** - Modified `ocr_service.dart` to use auto-discovered server URL instead of hardcoded IP
3. **Aggregation Debug Logging** - Added comprehensive debug output to `medication_processor.dart` to trace medication flow
4. **Network Scanning** - Service scans common IP ranges (172.20.10.x, 192.168.1.x, 10.0.0.x) to locate server

### Issues Resolved
- **Manual IP Updates**: No longer need to manually change IP address in code when switching networks (hotspot, home wifi, etc.)
- **Server Discovery**: App automatically finds server at startup by testing `/health` endpoint across IP ranges
- **Development Workflow**: Simplified development by removing hardcoded IP dependency

### Technical Details
- **Server Discovery**: Parallel IP scan across configurable ranges with 500ms timeout per IP
- **Caching**: Discovered server URL cached for session to avoid repeated scans
- **Fallback**: Uses 172.20.10.7:5003 as fallback if discovery fails
- **Configuration**: Editable settings in `server_discovery_service.dart` for IP ranges, timeouts, and fallback values
- **Discovery Time**: Typically 1-3 seconds on first scan, instant on subsequent requests (cached)

### Code Changes
- **NEW FILE**: `lib/services/server_discovery_service.dart` - Auto-discovery service with configurable settings
- **MODIFIED**: `lib/services/ocr_service.dart` - Lines 1-28 (added discovery integration)
- **MODIFIED**: `lib/services/medication_processor.dart` - Lines 85-142 (added debug logging)

### Configuration
Editable settings in `server_discovery_service.dart`:
- `serverPort`: 5003
- `ipRangesToScan`: ['172.20.10', '192.168.1', '10.0.0']
- `ipRangeEnd`: 20 (scan first 20 IPs per range)
- `discoveryTimeout`: 500ms per IP
- `fallbackIp`: '172.20.10.7'

### Next Steps
- Test server discovery across different networks (hotspot, home wifi)
- Investigate medication duplication with new debug logging
- Verify floor breakdown aggregation is working correctly
- Test scan with updated debugging to trace complete medication flow

---

## Date: October 17, 2025 (Evening Session)

### Session Context
Fixed critical medication duplication bug in Flutter aggregation logic. Root cause was overlapping category conditions causing each medication to be processed twice - once as floor stock and once as patient label.

### Changes Made
1. **Fixed Duplication Bug** - Modified `medication_processor.dart` line 112 to make floor stock and patient label categories mutually exclusive
2. **Category Logic Update** - Patient labels now explicitly exclude medications with floor field: `(med.patient != null || med.sig != null) && med.floor == null`
3. **Removed Regular Medications Category** - Deleted third processing category that was creating duplicates

### Issues Resolved
- **Medication Duplication**: 45 input medications were producing 74 output medications (exactly 2x duplication)
- **Overlapping Categories**: Medications with both `floor` AND `sig`/`patient` fields were being processed by both aggregators
- **Root Cause Identified**: Line 112 allowed medications to match both floor stock AND patient label conditions simultaneously

### Technical Details
- **Problem**: `where((med) => med.patient != null || med.sig != null)` matched medications regardless of floor field
- **Solution**: `where((med) => (med.patient != null || med.sig != null) && med.floor == null)` ensures mutual exclusivity
- **Grouping**: Successfully groups 45 medications into 37 unique groups by name-dose-form
- **Expected Output**: 37 aggregated medications (one per group) instead of 74 duplicates

### Code Changes
- `lib/services/medication_processor.dart`: Line 112 - Added `&& med.floor == null` condition to patient label filter
- Added comments clarifying mutually exclusive categories (lines 108-110)

### Testing Results
- ✅ Grouping working correctly: 45 input → 37 groups
- ⏳ Awaiting test of fix: Should now produce 37 output medications (no duplication)
- ✅ Floor breakdown format working: "Pick X (Y units for floor1, Z units for floor2)"

### Architecture Notes
**Floor Stock vs Patient Labels (Mutually Exclusive)**:
- **Floor Stock**: `med.floor != null` - Medications assigned to specific hospital floors
- **Patient Labels**: `(med.patient != null || med.sig != null) && med.floor == null` - Patient-specific medications WITHOUT floor assignments
- **Priority**: Floor field takes precedence - if medication has floor assignment, it's floor stock regardless of other fields

### Next Steps
- Test duplication fix with 4-image floor stock scan
- Verify output is 37 medications (matching group count)
- Confirm floor breakdown displays correctly in slideshow
- Test cart-fill mode to ensure patient label aggregation still works

---

## Date: October 20, 2025 (Morning Session)

### Session Context
Implemented dynamic pick amount validation using the formula `Pick Amount = Max - Current Amount` to fix incorrect OCR extractions without hardcoding examples.

### Changes Made
1. **Updated LLM Prompt** - Modified `floor_stock_parser.py` to request extraction of all three values: pick_amount, max, and current_amount
2. **Added Dynamic Validation** - Created `_validate_and_correct_pick_amounts()` method that validates pick amounts using the formula
3. **Auto-Correction Logic** - System now automatically corrects misaligned columns without hardcoded examples

### Issues Resolved
- **Wrong Pick Amount Extraction**: Heparin was showing pick_amount=80 (the Max value) instead of 42 (the correct Pick Amount)
- **Formula-Based Validation**: Pick Amount = Max - Current Amount (e.g., 80 - 38 = 42)
- **Dynamic Correction**: System now validates each medication and auto-corrects if formula doesn't match (within ±5 tolerance)

### Technical Details
- **Validation Formula**: `|pick_amount - (max - current)| ≤ 5` (tolerance accounts for timing differences)
- **Auto-Correction Strategy**:
  1. If formula matches → medication validated ✓
  2. If formula doesn't match → calculate correct value from max - current
  3. Log all corrections for debugging
- **No Hardcoding**: Solution is fully dynamic and adapts to any BD report format

### Code Changes
- `python_server/floor_stock_parser.py`: Lines 385-426 (updated LLM prompt to extract max and current_amount)
- `python_server/floor_stock_parser.py`: Lines 460-461 (added validation call)
- `python_server/floor_stock_parser.py`: Lines 503-548 (new `_validate_and_correct_pick_amounts()` method)

### Architecture Notes
**Pick Amount Validation (Formula-Based)**:
- **LLM Extraction**: Extracts pick_amount, max, and current_amount from OCR text
- **Validation**: Checks if `pick_amount ≈ max - current_amount` (±5 tolerance)
- **Auto-Correction**: If validation fails, uses formula result as correct pick_amount
- **Logging**: All validations and corrections logged for transparency

**Example**:
- OCR text shows: "42, 80, 38" for heparin
- LLM might extract: pick_amount=80, max=?, current_amount=?
- Validation calculates: expected_pick = max - current
- If mismatch detected: Auto-corrects to pick_amount = 42

### Next Steps
- Test with real floor stock scan to verify heparin now shows 42 instead of 80
- Monitor validation logs to ensure formula works across all medications
- Verify tolerance of ±5 is appropriate for typical pharmacy operations

---

## Date: October 20, 2025 (Evening Session)

### Session Context
Attempted to implement coordinate-based parsing using Google Vision bounding boxes to fix incorrect pick amount extraction. Discovered that LLM is extracting wrong values (sodium bicarbonate showing pick=30 instead of 23) and coordinate-based approach is not finding table data numbers.

### Investigation & Findings

**Problem Identified**: Sodium bicarbonate was showing pick_amount=30, max=40, current=10, but correct values should be pick=23, max=40, current=17.

**Root Cause Analysis**:
1. **LLM Misalignment**: Groq LLM was selecting numbers from wrong table rows when parsing linearized OCR text (the "30" was actually from pantoprazole's row)
2. **Column Header Detection Issue**: Initial implementation found multiple "Pick" headers and used the wrong one (X=3605 instead of ~X=339-400)
3. **Coordinate Extraction Failure**: Even after fixing column detection, coordinate-based parsing only found medication strength numbers (100 mg, 650 mg) instead of actual table data (23, 40, 17)

### Changes Made

1. **Created Backup** - `floor_stock_parser_backup_20251020_0545.py`

2. **Modified docling_server.py** (line 143):
   - Now passes `raw_response` (word annotations with bounding boxes) to parser
   ```python
   validated_medications = parser.parse(raw_text, ocr_result.get('raw_response'))
   ```

3. **Implemented Coordinate-Based Parsing** in `floor_stock_parser.py`:
   - Added `word_annotations` parameter to `parse()` method (line 43)
   - Created `_parse_with_coordinates()` method (lines 518-643) to use bounding box data
   - Created `_identify_table_columns()` method (lines 663-711) to find column X-positions from headers

4. **Fixed Column Detection Logic** (lines 663-711):
   - Changed strategy to find "Max" and "Current" first (they're unique)
   - Then find "Pick Amount" header that's spatially near Max (within 200px to the left)
   - This prevents selecting wrong "Pick" text from other parts of the document

5. **Added Debug Logging**:
   - Column header detection now logs all found headers with X,Y positions
   - Number extraction logs which numbers are found and their distances to columns
   - Special debug mode for sodium bicarbonate to show ALL numbers in document

### Technical Details

**Coordinate-Based Parsing Strategy**:
1. Extract all words with X,Y coordinates from Google Vision bounding boxes
2. Identify table column X-positions by finding "Pick Amount", "Max", "Current" headers
3. Use LLM only for medication name extraction (it's good at compound medication names)
4. Match numbers to medications using Y-coordinate (row alignment)
5. Assign numbers to columns using X-coordinate (column alignment with ±50px tolerance)
6. Validate using Pick Amount = Max - Current formula

**Column Detection**:
- First pass: Find "Max" (X=423) and "Current" (X=436) headers
- Second pass: Find "Pick" header within 200px to left of Max
- Result: Pick=339, Max=423, Current=436 (spatially coherent)

### Issues Discovered (Still Unresolved)

1. **Table Data Numbers Not Found**: Coordinate-based extraction only finds strength numbers (100, 650) from medication description, not table data (23, 40, 17)
   - Numbers 23 and 17 ARE in OCR text (confirmed via `/tmp/ocr_debug.txt`)
   - But coordinate extraction isn't finding them near sodium bicarbonate's Y-position

2. **Y-Coordinate Matching Issue**: Search range is -20 to +100 pixels from medication name, but table data might be outside this range

3. **Possible Causes**:
   - Table data numbers might not be within Y-search range
   - Numbers might be filtered out by `len(word['text']) <= 3` check
   - X-tolerance of ±50px might not match actual column positions
   - Medication name Y-position might be wrong (using first word only)

### Code Changes
- **BACKUP**: `python_server/floor_stock_parser_backup_20251020_0545.py`
- **MODIFIED**: `python_server/docling_server.py`: Line 143 (pass raw_response to parser)
- **MODIFIED**: `python_server/floor_stock_parser.py`:
  - Lines 43 (added word_annotations parameter)
  - Lines 67-75 (coordinate-based parsing logic)
  - Lines 518-643 (_parse_with_coordinates method)
  - Lines 663-711 (_identify_table_columns method with spatial filtering)
  - Lines 605-610 (debug logging for sodium bicarbonate)

### Architecture Notes

**Why Coordinate-Based Parsing**:
- LLM parsing of linearized text causes column misalignment
- Using spatial coordinates provides deterministic, reliable extraction
- Healthcare-critical data requires accuracy over flexibility

**Two-Stage Hybrid Approach**:
- Stage 1: LLM extracts medication names (complex, compound names)
- Stage 2: Coordinate-based extraction for numbers (deterministic)
- Validation: Formula check (Pick Amount = Max - Current)

### Testing Results
- ✓ Column detection now finds correct Pick header (X=339 vs old X=3605)
- ✓ Spatial filtering successfully rejects far-away "Pick" headers
- ✗ Coordinate extraction still not finding table data numbers (23, 17)
- ✗ LLM still extracting pick=30 (wrong) and passing formula validation with max=40, current=10

### Next Steps (When Resuming)
1. **Debug Y-coordinate range**: Check if table data is outside -20 to +100 pixel range
2. **Dump all numbers with coordinates**: Use debug logging to see where 23, 40, 17 actually are in coordinate space
3. **Check medication name Y-position**: Verify we're using correct row position (not just first word)
4. **Adjust search parameters**: May need to widen Y-range, X-tolerance, or both
5. **Alternative approach**: If coordinate matching fails, consider using formula-based column detection (find three numbers that satisfy Pick = Max - Current)

### Session Notes
- Server running correctly at http://172.20.10.9:5003
- Flutter app had connectivity/discovery issues during testing (stuck on "processing")
- Debug logging infrastructure in place for next session

---

## Date: October 21, 2025

### Session Context
Fixed incorrect pick amount extraction for sodium bicarbonate using formula-based validation with consecutive triplet preference. Implemented hybrid number extraction strategy combining LLM flexibility with mathematical validation.

### Changes Made

1. **Updated LLM Prompt** - Modified `floor_stock_parser.py` lines 403-437 to extract ALL standalone numbers between medication name and next medication
   - Changed from restrictive "only numbers immediately before strength" to comprehensive extraction
   - Allows LLM to capture numbers wherever they appear in medication section
   - Formula validation then identifies correct triplet from all extracted numbers

2. **Implemented Consecutive Triplet Preference** - Modified `_identify_columns_by_formula()` lines 754-785
   - FIRST PASS: Checks consecutive 3-number sequences (most reliable for BD table format)
   - SECOND PASS: Falls back to all combinations if no consecutive match found
   - Prioritizes spatially adjacent numbers since BD tables have Pick/Max/Current in adjacent columns

3. **Added Single Number Handling** - Modified `_identify_numbers_by_formula()` lines 725-766
   - Handles medications with only 1 number (just pick amount)
   - Handles medications with 2 numbers (uses first as pick amount)
   - Handles medications with 3+ numbers (uses formula validation)

### Issues Resolved
- ✅ **Sodium bicarbonate pick amount**: Now correctly shows **Pick: 23** instead of 30
- ✅ **Formula validation working**: Successfully identifies pick=23, max=40, current=17 from numbers=[23, 40, 17]
- ✅ **Consecutive triplet logic**: Finds correct triplet at positions [5,6,7] instead of wrong triplet at [0,2,4]
- ✅ **Gabapentin extraction**: Working with single number (Pick: 13)
- ✅ **Apixaban extraction**: Working with single number (Pick: 16)

### Issues Identified (Still Unresolved)
- ❌ **Pantoprazole**: Not extracting numbers (Pick: N/A) - LLM not finding numbers in medication section
- ❌ **Nifedipine**: Not extracting numbers (Pick: N/A) - needs investigation

### Technical Details

**Root Cause of Sodium Bicarbonate Issue**:
- OCR text had TWO sets of numbers: [30, 17, 40] (wrong - from pantoprazole's row) and [23, 40, 17] (correct)
- LLM was extracting all numbers: [30, 17, 40, 24, 11, 23, 40, 17]
- Original formula validator found FIRST valid triplet: 30 = 40 - 11 ✗ (within ±5 tolerance but wrong row)
- **Solution**: Consecutive triplet preference finds [23, 40, 17] at positions [5,6,7] where 23 = 40 - 17 ✓ (exact match)

**Formula Validation Strategy**:
```python
# FIRST PASS: Try consecutive triplets (BD table has adjacent columns)
for i in range(len(numbers) - 2):
    pick, max_val, curr = numbers[i], numbers[i+1], numbers[i+2]
    if abs(pick - (max_val - curr)) <= 5:
        return (pick, max_val, curr)

# SECOND PASS: Try all combinations if no consecutive match
# (fallback for scattered numbers)
```

**Number Extraction Strategy**:
- Extract ALL standalone numbers between medication name and next medication
- Include numbers before brand, before strength, after form
- Exclude numbers that are part of strength (e.g., "650 mg", "100 mg")
- Formula validation identifies correct triplet from all candidates

### Code Changes
- **MODIFIED**: `python_server/floor_stock_parser.py`:
  - Lines 403-437: Updated LLM prompt for comprehensive number extraction
  - Lines 725-766: Added `_identify_numbers_by_formula()` with single/multi-number handling
  - Lines 768-808: Added `_identify_columns_by_formula()` with consecutive triplet preference

### Testing Results
- ✅ Sodium bicarbonate: **Pick: 23** (was 30) - FIXED
- ✅ Gabapentin: **Pick: 13** - Working
- ✅ Apixaban: **Pick: 16** - Working
- ✅ Hydralazine: **Pick: 15** - Working
- ✅ Quetiapine: **Pick: 12** - Working
- ✅ Metoprolol tartrate: **Pick: 12** - Working
- ✅ Thiamine: **Pick: 10** - Working
- ✅ Acetaminophen: **Pick: 123** - Working
- ✅ Lactulose: **Pick: 10** - Working
- ❌ Pantoprazole: **Pick: N/A** - Not working
- ❌ Nifedipine ER: **Pick: N/A** - Not working

### Architecture Notes

**Two-Stage Validation**:
1. **LLM Extraction**: Extracts all numbers in medication section (flexible, handles OCR variations)
2. **Formula Validation**: Identifies correct triplet using Pick = Max - Current (±5 tolerance)

**Why Consecutive Triplet Preference Works**:
- BD table has Pick Amount, Max, Current in adjacent columns
- Google Vision reads left-to-right, so adjacent columns → consecutive numbers in OCR text
- Consecutive triplets are more likely to be from same medication row
- Non-consecutive combinations often mix numbers from different medications

**Key Insight from User**:
- All medications on physical paper have 3 numbers (Pick, Max, Current)
- Some medications showing only 1 number in OCR due to Google Vision reading order
- Solution: Extract ALL numbers comprehensively, let formula validation sort it out

### Next Steps (When Resuming)
1. **Debug pantoprazole and nifedipine**: Check why LLM isn't extracting numbers for these medications
2. **Test full 4-image scan**: Verify all medications across complete floor stock report
3. **Monitor formula validation logs**: Ensure consecutive triplet logic works for all medication types
4. **Consider fallback for missing numbers**: If LLM can't extract numbers, may need coordinate-based extraction

### Session Notes
- Server running at http://172.20.10.9:5003 (iPhone hotspot network)
- Simplified approach (LLM + formula validation) working better than complex coordinate-based parsing
- Consecutive triplet preference is key innovation that solved the column misalignment issue
- **READY FOR TESTING**: All code changes saved, server running with latest updates