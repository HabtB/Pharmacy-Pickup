from medication_location_lookup import MedicationLocationLookup

# 1. Read the file
with open('medication_locations.csv', 'r') as f:
    content = f.read()

# 2. Fix the specific corruption string
# Pattern: "ZONISAMIDE 25 MG CAPSULE,PHRM,,DEXTROMETHORPHAN..."
# Replace with newline
fixed_content = content.replace(
    'ZONISAMIDE 25 MG CAPSULE,PHRM,,DEXTROMETHORPHAN', 
    'ZONISAMIDE 25 MG CAPSULE,PHRM,,\nDEXTROMETHORPHAN'
)

# 3. Write back
with open('medication_locations.csv', 'w') as f:
    f.write(fixed_content)

print("Fixed CSV corruption.")
