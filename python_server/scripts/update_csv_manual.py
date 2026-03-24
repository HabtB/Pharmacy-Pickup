
import csv
import shutil
import os

def normalize_name(name):
    return name.strip().upper()

def update_csv():
    source_file = 'medication_locations.csv'
    temp_file = 'medication_locations_temp.csv'
    backup_file = 'medication_locations_backup.csv'

    # 1. VISUAL FINDINGS MAPPING
    # Format: "KEYWORD": ("LOCATION_CODE", "LOCATION_DESC", "IMAGE_FILE")
    # Rule: If Med Name contains Keyword, apply this mapping.
    # Order matters: Specific > General.
    
    manual_mappings = [
        # --- FRIDGE ITEMS ---
        ("INSULIN REGULAR", "FRIDGE", "Main Pharmacy - Fridge", "Fridge 1(I)-.jpeg"),
        ("HUMULIN R", "FRIDGE", "Main Pharmacy - Fridge", "Fridge 1(I)-.jpeg"),
        ("INSULIN LISPRO", "FRIDGE", "Main Pharmacy - Fridge", "Fridge 1(I)-.jpeg"),
        ("HUMALOG", "FRIDGE", "Main Pharmacy - Fridge", "Fridge 1(I)-.jpeg"),
        ("PNEUMOCOCCAL", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-2(II).jpeg"),
        ("PREVNAR", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-2(II).jpeg"),
        ("VANCOMYCIN", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-3(II).jpeg"), # IV Bags
        ("CLEVIDIPINE", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(I).jpeg"),
        ("CLEVIPREX", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(I).jpeg"),
        ("PERFLUTREN", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(I).jpeg"),
        ("OPTISON", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(I).jpeg"),
        ("DEFINITY", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(I).jpeg"),
        ("IMMUNE GLOBULIN", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(ii).jpeg"),
        ("VASOPRESSIN", "FRIDGE", "Main Pharmacy - Fridge", "Fridge-4(ii).jpeg"),

        # --- VITAMINS (Orange Bins) ---
        ("VITAMIN A", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"),
        ("VITAMIN B", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"),
        ("KYTRIL", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"), # Mistake? No, stick to vitamins.
        ("THIAMINE", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"), # B1
        ("PYRIDOXINE", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"), # B6
        ("CYANOCOBALAMIN", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"), # B12
        ("VITAMIN C", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"),
        ("ASCORBIC ACID", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (upper half).jpeg"),
        ("CALCIUM CITRATE", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("VITAMIN E", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("FOLIC ACID", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("PRENATAL", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("FERROUS SULFATE", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("IRON", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Vit Section (lower half).jpeg"),
        ("ASPIRIN", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Zone Y-ii.jpeg"),
        ("MAGNESIUM OXIDE", "PHRM", "Main Pharmacy - Vitamins", "Main Pharmacy - Zone Y-ii.jpeg"),

        # --- BLUE BINS (Zone X/Y) ---
        # Zone X (A-B ish?)
        ("AMOXICILLIN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("AUGMENTIN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("APIXABAN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("ELIQUIS", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("APREPITANT", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("ATORVASTATIN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("AZITHROMYCIN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("BACLOFEN", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),
        ("BENZTROPINE", "PHRM", "Main Pharmacy - Zone X", "Main Pharmacy - Zone X.jpeg"),

        # Zone Y (The rest)
        ("BISACODYL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("BUSPIRONE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("BUPROPION", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("CALCIUM ACETATE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("CARBIDOPA", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("CARVEDILOL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("CEFPODOXIME", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("CEPHALEXIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("CHLORPROMAZINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("CIPROFLOXACIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("CLOPIDOGREL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("CLONIDINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("CINACALCET", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("DONEPEZIL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iii.jpeg"),
        ("DOXYCYCLINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iii.jpeg"),
        ("DIVALPROEX ER", "STR", "Store Room - Zone 1 (Tablets A-H)", "Store Location-Z1.jpeg"), # ER is in Store Room
        ("DIVALPROEX DR", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iii.jpeg"),
        ("DULOXETINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("EMPAGLIFLOZIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("ESCITALOPRAM", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("ESOMEPRAZOLE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("EZETIMIBE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("FAMOTIDINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("FINASTERIDE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("FLUCONAZOLE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("FLUCYTOSINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("FUROSEMIDE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("GABAPENTIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("GLIPIZIDE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("GUANFACINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("HALOPERIDOL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("HYDRALAZINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("LEVOTHYROXINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("LISINOPRIL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("LITHIUM", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("LORATADINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("LOSARTAN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("MECLIZINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("MELATONIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("MEMANTINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("METFORMIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("METOPROLOL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("OLANZAPINE VIAL", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"), # User Exception: Back of Zone 9
        ("OLANZAPINE INTRAMUSCULAR", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("OLANZAPINE 10 MG/2 ML", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"), 
        ("OLANZAPINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("ONDANSETRON", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iii.jpeg"),
        ("PANTOPRAZOLE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("POTASSIUM CHLORIDE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-iv.jpeg"),
        ("PRAVASTATIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("PRAZOSIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("PREDNISONE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),
        ("PYRIDOSTIGMINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("QUETIAPINE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("RIFAXIMIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vi.jpeg"),
        ("RISPERIDONE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("ROSUVASTATIN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-vii.jpeg"),
        ("SACUBITRIL", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("ENTRESTO", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("RIVAROXABAN", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        ("TRAZODONE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-v.jpeg"),

        # --- PHASE 17b EXCEPTIONS (User Feedback) ---

        # PYXIS ITEMS (Secure Storage)
        ("BIKTARVY", "PYXIS", "Pyxis Machine", ""), # No image for Pyxis yet
        ("DESCOVY", "PYXIS", "Pyxis Machine", ""),
        ("OSELTAMIVIR", "PYXIS", "Pyxis Machine", ""),
        ("TAMIFLU", "PYXIS", "Pyxis Machine", ""),

        # ZONE 9 EXCEPTIONS (Back of Store)
        ("ALBUTEROL 0.083", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"), # Nebulizer
        ("IPRATROPIUM", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("COMBIVENT", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("MIRALAX", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("POLYETHYLENE GLYCOL", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("ONDANSETRON VIAL", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("ONDANSETRON INJECTION", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("LIDOCAINE 4% PATCH", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        ("HEPARIN", "STR", "Store Room - Zone 9 (Back)", "Store Location-Z9.jpeg"),
        
        # MAIN PHARMACY CORRECTIONS
        # Trimethoprim/Sulfamethoxazole (Bactrim) -> Main Pharm (likely 'S' section or 'T')
        # Mapping to Zone Y (General) or specific image if known. Zone Y-viii is S-Z.
        ("TRIMETHOPRIM", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"), 
        ("SULFAMETHOXAZOLE", "PHRM", "Main Pharmacy - Zone Y", "Main Pharmacy - Zone Y-viii.jpeg"),
        
        # --- PHASE 17 ADDITIONS: IV, HIV, INHALERS (Previous) ---
        
        # IV ROOM / PREMIXED BAGS (Zone 4)
        ("DEXTROSE", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        ("SODIUM CHLORIDE", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        ("RINGER", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        ("LACTATED", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        ("PREMIX", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        ("NITROGLYCERIN", "STR", "Store Room - Zone 4 (Nitroglycerin)", "Store Location-Z4.jpeg"), # Sign mentions this specifically
        ("AMPICILLIN", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"), # 1.5g, 3g bags
        ("UNASYN", "STR", "Store Room - Zone 4 (IV Bags)", "Store Location-Z4.jpeg"),
        
        # HIV PRODUCTS (Zone 5)
        ("BIKTARVY", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("GENVOYA", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("DESCOVY", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("TIVICAY", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("TRUVADA", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("ODEFSEY", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("TRIUMEQ", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("ISENTRESS", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("NORVIR", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),
        ("PREZISTA", "STR", "Store Room - Zone 5 (HIV)", "Store Location-Z5.jpeg"),

        # RESPIRATORY INHALERS (Zone 6 - with Patches/Drops)
        ("ALBUTEROL", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("VENTOLIN", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("PROAIR", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("FLOVENT", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("ADVAIR", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("SYMBICORT", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("SPIRIVA", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("COMBIVENT", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("QVAR", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("PULMICORT", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("BUDESONIDE", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        ("IPRATROPIUM", "STR", "Store Room - Zone 6 (Inhalers)", "Store Location-Z6.jpeg"),
        
        # OTHER OTC/DROPS (Zone 6 confirmed by image)
        ("ARTIFICIAL TEARS", "STR", "Store Room - Zone 6 (Drops)", "Store Location-Z6.jpeg"),
        ("LIDOCAINE PATCH", "STR", "Store Room - Zone 6 (Patches)", "Store Location-Z6.jpeg"), # Patches are on Zone 6 sign
        ("NICOTINE PATCH", "STR", "Store Room - Zone 6 (Patches)", "Store Location-Z6.jpeg"),
    ]

    # Create backup
    if os.path.exists(source_file):
        shutil.copy(source_file, backup_file)

    updated_count = 0
    with open(source_file, 'r', encoding='utf-8') as infile, \
         open(temp_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        headers = next(reader)
        # Ensure Image column exists
        if 'Image' not in headers:
            headers.append('Image')
        
        writer.writerow(headers)
        
        img_col_idx = headers.index('Image')
        loc_code_idx = 1 # 'Location'
        loc_desc_idx = 3 # 'Notes' (using as desc) or 2? 
        # CSV structure usually: Name, Location, Notes, ?, Image
        # Let's check headers: MedName, Location, PickAmount, Notes, Image
        # Based on previous `find_location` logic: row[1] is code, row[3] is desc.
        
        for row in reader:
            med_name = normalize_name(row[0])
            
            # Preserve existing data
            while len(row) < len(headers):
                row.append("")
                
            matched = False
            for keyword, code, desc, img in manual_mappings:
                if keyword in med_name:
                    row[loc_code_idx] = code
                    # Assuming row[3] is Notes/Desc. 
                    # If we want to overwrite 'Notes' with 'Main Pharmacy - Zone Y', we do row[3]
                    row[3] = desc 
                    row[img_col_idx] = img
                    matched = True
                    updated_count += 1
                    break # Stop after first match
            
            writer.writerow(row)

    os.replace(temp_file, source_file)
    print(f"Successfully updated {updated_count} medication records.")

if __name__ == "__main__":
    update_csv()
