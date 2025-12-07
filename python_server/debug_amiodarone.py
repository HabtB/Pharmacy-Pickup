from medication_location_lookup import MedicationLocationLookup
import logging

# Configure logging to see the loop logic
logging.basicConfig(level=logging.INFO)

lookup = MedicationLocationLookup()
print("\n--- Amiodarone Keys in Index ---")
for key in lookup._sorted_index.keys():
    if "AMIODARONE" in key:
        print(f"Key: '{key}'")

print("\n--- Testing Specific Lookup ---")
lookup.find_location("amiodarone in D5W (NEXTERONE IV)", "360 mg (200 mL)", "bag")
