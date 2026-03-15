class LocationImageService {
  /// Maps a location or zone description to an asset path.
  /// Returns null if no matching image is found.
  static String? getImagePath(String location, String? zone) {
    // Normalize inputs
    final locLower = location.toLowerCase();
    final zoneLower = zone?.toLowerCase() ?? '';

    // 1. Check Zones (Store Room)
    if (zoneLower.contains('zone 1')) return 'assets/images/store_location_z1.jpeg';
    if (zoneLower.contains('zone 2')) return 'assets/images/store_location_z2.jpeg';
    if (zoneLower.contains('zone 3')) return 'assets/images/store_location_z3.jpeg';
    if (zoneLower.contains('zone 4')) return 'assets/images/store_location_z4.jpeg';
    if (zoneLower.contains('zone 5')) return 'assets/images/store_location_z5.jpeg';
    if (zoneLower.contains('zone 6')) return 'assets/images/store_location_z6.jpeg';
    if (zoneLower.contains('zone 7')) return 'assets/images/store_location_z7.jpeg';
    if (zoneLower.contains('zone 8')) return 'assets/images/store_location_z8.jpeg';
    if (zoneLower.contains('zone 9')) return 'assets/images/store_location_z9.jpeg';

    // 2. Check Fridges
    // Simplification: Pointing all generic "Fridge 1" to "I". 
    // Ideally we'd parse "Fridge 1 (II)" if that data existed in the model, 
    // but currently we just say "Fridge".
    // We can show the first one as a representative.
    if (locLower.contains('fridge 1')) return 'assets/images/fridge_1i.jpeg'; 
    if (locLower.contains('fridge 2')) return 'assets/images/fridge_2i.jpeg';
    if (locLower.contains('fridge 3')) return 'assets/images/fridge_3i.jpeg';
    if (locLower.contains('fridge 4')) return 'assets/images/fridge_4i.jpeg';

    // 3. Main Pharmacy
    if (locLower.contains('main pharmacy')) {
      if (locLower.contains('vit')) {
         return 'assets/images/main_pharmacy_vit_section_upper_half.jpeg';
      }
      return 'assets/images/main_pharmacy_zone_x.jpeg'; // General/Default
    }

    return null;
  }
}
