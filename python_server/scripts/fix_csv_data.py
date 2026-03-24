import csv
import os
import shutil

CSV_PATH = 'medication_locations.csv'
BACKUP_PATH = 'medication_locations_backup_v2.csv'

def fix_csv():
    # 1. Create Backup
    shutil.copyfile(CSV_PATH, BACKUP_PATH)
    print(f"Backed up CSV to {BACKUP_PATH}")

    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    print(f"Loaded {len(rows)} entries.")

    updated_count = 0
    
    # Keyword Lists
    HIV_KEYWORDS = [
        'ABACAVIR', 'BIKTARVY', 'GENVOYA', 'TRUVADA', 'DESCOVY', 'ODEFSEY', 
        'DOLUTEGRAVIR', 'LAMIVUDINE', 'TENOFOVIR', 'EMTRICITABINE', 
        'EFAVIRENZ', 'RITONAVIR', 'DARUNAVIR', 'ATAZANAVIR', 'RILPIVIRINE',
        'MARAVIROC', 'RALTEGRAVIR', 'ISENTRESS', 'TIVICAY', 'JULUCA', 
        'DOVATO', 'TRIUMEQ', 'COMPLERA', 'STRIBILD', 'SYMFI', 'CIMDUO',
        'BICTEGRAVIR', 'COBICISTAT'
    ]
    
    VITAMIN_KEYWORDS = [
        'VITAMIN', 'CALCIUM', 'CHOLECALCIFEROL', 'ERGOCALCIFEROL', 'NIACIN', 
        'MULTIVITAMIN', 'ASCORBIC', 'THIAMINE', 'FOLIC ACID', 'MAGNESIUM OXIDE',
        'CYANOCOBALAMIN', 'FERROUS', 'ZINC', 'BIOTIN', 'MELATONIN'
    ]
    
    # Specific Fixes
    for row in rows:
        if len(row) < 2: continue
        
        name = row[0].upper()
        code = row[1]
        
        original_code = code
        new_code = code

        # 1. Separate HIV from VIT
        # Strategy: If it contains HIV keywords, mark HIV. 
        # CAUTION: Some might be currently PHRM or VIT.
        is_hiv = any(k in name for k in HIV_KEYWORDS)
        if is_hiv:
            new_code = 'HIV'
        
        # 2. Fix Vitamins
        # If it contains Vitamin keywords -> VIT
        # (Unless it's an IV multivitamin? Usually MVI is in fridge/IV, but for now we group as requested)
        # Exception: Magnesium Sulfate IV is IV, Magnesium Oxide is VIT.
        is_vit = any(k in name for k in VITAMIN_KEYWORDS)
        if is_vit and 'IV' not in name and 'INJECTION' not in name and 'SULFATE' not in name:
            new_code = 'VIT'
            
        # 3. Clean up existing 'VIT' category
        # If it was VIT but is NOT HIV and NOT Vitamin -> reset to PHRM
        if code == 'VIT' and not is_hiv and not is_vit:
            # Check strictly if it's really not a vitamin
            # e.g. Aripiprazole, Ibuprofen, etc.
            new_code = 'PHRM'
            
        # 4. Specific Issues
        if 'HYDRALAZINE' in name and '20 MG' in name:
             new_code = 'STR'
             
        if 'EPLERENONE' in name:
            new_code = 'STR' # As per user request/CSV check earlier (it was STR, make sure it stays STR)

        # Apply Updates
        if new_code != original_code:
            row[1] = new_code
            updated_count += 1
            # print(f"Updated {name}: {original_code} -> {new_code}")

    # 5. Add Dextrose 50% if missing or fix existing
    # Check if correct entry exists
    dextrose_found = False
    for row in rows:
        if 'DEXTROSE 50' in row[0] and 'SYRINGE' in row[0]:
            print(f"Found existing Dextrose Syringe: {row[0]}")
            row[1] = 'STR'
            dextrose_found = True
    
    if not dextrose_found:
        print("Adding Dextrose 50% Syringe entry...")
        rows.append(['DEXTROSE 50 % 25 GM (50 ML) SYRINGE', 'STR', '', 'Store Room - Zone 7 (Syringes)', 'store_location_z7.jpeg'])
        updated_count += 1

    # Write back
    with open(CSV_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Done. Updated {updated_count} entries.")

if __name__ == "__main__":
    fix_csv()
