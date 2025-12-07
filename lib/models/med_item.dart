class MedItem {
  final String name;
  final String dose;
  final String form;
  final int pickAmount;
  final String? location;
  final String? notes;
  final String? warning; // Warning message if numbers don't match formula
  final String? floor; // e.g., "6W", "7E1 (SICU)"
  final String? patient; // e.g., "Patient A"
  final String? sig; // e.g., "bid", "tid", "qhs"
  final String? admin; // e.g., "0.5 tablet", "1 tablet"
  final double calculatedQty; // Derived from sig for patient labels, supports decimals
  final String? pickLocation; // e.g., "PHRM", "STR", "VIT", "IV", "UNKNOWN"
  final String? pickLocationDesc; // e.g., "Main Pharmacy", "Store Room"
  final List<dynamic>? floorBreakdown; // List of {floor, amount}

  const MedItem({
    required this.name,
    required this.dose,
    required this.form,
    required this.pickAmount,
    this.location,
    this.notes,
    this.warning,
    this.floor,
    this.patient,
    this.sig,
    this.admin,
    double? calculatedQty,
    this.pickLocation,
    this.pickLocationDesc,
    this.floorBreakdown,
  }) : calculatedQty = calculatedQty ?? 1.0;

  factory MedItem.fromMap(Map<String, dynamic> map) {
    return MedItem(
      name: map['name'] ?? '',
      dose: map['dose'] ?? '',
      form: map['form'] ?? '',
      pickAmount: map['pick_amount'] ?? 0,
      location: map['location'],
      notes: map['notes'],
      warning: map['warning'],
      floor: map['floor'],
      patient: map['patient'],
      sig: map['sig'],
      admin: map['admin'],
      calculatedQty: (map['calculated_qty'] ?? _calculateFromSig(map['sig'])).toDouble(),
      pickLocation: map['pick_location'],
      pickLocationDesc: map['pick_location_desc'],
      floorBreakdown: map['floor_breakdown'],
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'dose': dose,
      'form': form,
      'pick_amount': pickAmount,
      'location': location,
      'notes': notes,
      'warning': warning,
      'floor': floor,
      'patient': patient,
      'sig': sig,
      'admin': admin,
      'calculated_qty': calculatedQty,
      'pick_location': pickLocation,
      'pick_location_desc': pickLocationDesc,
      'floor_breakdown': floorBreakdown,
    };
  }

  static int _calculateFromSig(String? sig) {
    if (sig == null) return 1;
    sig = sig.toLowerCase();
    if (sig.contains('bid') || sig.contains('twice daily')) return 2;
    if (sig.contains('tid') || sig.contains('three times daily')) return 3;
    if (sig.contains('qid') || sig.contains('four times daily')) return 4;
    if (sig.contains('q6h') || sig.contains('every 6 hours')) return 4;
    if (sig.contains('q8h') || sig.contains('every 8 hours')) return 3;
    if (sig.contains('q12h') || sig.contains('every 12 hours')) return 2;
    if (sig.contains('qd') || sig.contains('daily') || sig.contains('once daily')) return 1;
    if (sig.contains('qhs') || sig.contains('bedtime') || sig.contains('at bedtime')) return 1;
    if (sig.contains('prn') || sig.contains('as needed')) return 1;
    
    // Try to extract numeric frequency (e.g., "take 2 tablets")
    final numMatch = RegExp(r'take (\d+)').firstMatch(sig);
    if (numMatch != null) {
      return int.tryParse(numMatch.group(1)!) ?? 1;
    }
    
    return 1; // Default
  }

  MedItem copyWith({
    String? name,
    String? dose,
    String? form,
    int? pickAmount,
    String? location,
    String? notes,
    String? warning,
    String? floor,
    String? patient,
    String? sig,
    String? admin,
    double? calculatedQty,
    String? pickLocation,
    String? pickLocationDesc,
    List<dynamic>? floorBreakdown,
  }) {
    return MedItem(
      name: name ?? this.name,
      dose: dose ?? this.dose,
      form: form ?? this.form,
      pickAmount: pickAmount ?? this.pickAmount,
      location: location ?? this.location,
      notes: notes ?? this.notes,
      warning: warning ?? this.warning,
      floor: floor ?? this.floor,
      patient: patient ?? this.patient,
      sig: sig ?? this.sig,
      admin: admin ?? this.admin,
      calculatedQty: calculatedQty ?? this.calculatedQty,
      pickLocation: pickLocation ?? this.pickLocation,
      pickLocationDesc: pickLocationDesc ?? this.pickLocationDesc,
      floorBreakdown: floorBreakdown ?? this.floorBreakdown,
    );
  }

  MedItem withLocationAndNotes(String? newLocation, String? newNotes) {
    return MedItem(
      name: name,
      dose: dose,
      form: form,
      pickAmount: pickAmount,
      location: newLocation,
      notes: newNotes,
      warning: warning,
      floor: floor,
      patient: patient,
      sig: sig,
      admin: admin,
      calculatedQty: calculatedQty,
      pickLocation: pickLocation,
      pickLocationDesc: pickLocationDesc,
      floorBreakdown: floorBreakdown,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is MedItem &&
        other.name == name &&
        other.dose == dose &&
        other.form == form &&
        other.pickAmount == pickAmount &&
        other.location == location &&
        other.notes == notes &&
        other.warning == warning &&
        other.floor == floor &&
        other.patient == patient &&
        other.sig == sig &&
        other.admin == admin &&
        other.calculatedQty == calculatedQty &&
        other.pickLocation == pickLocation &&
        other.pickLocationDesc == pickLocationDesc;
        // Skip floorBreakdown comparison for simplicity, or add deep check if needed
  }

  @override
  int get hashCode {
    return name.hashCode ^
        dose.hashCode ^
        form.hashCode ^
        pickAmount.hashCode ^
        location.hashCode ^
        notes.hashCode ^
        warning.hashCode ^
        floor.hashCode ^
        patient.hashCode ^
        sig.hashCode ^
        admin.hashCode ^
        calculatedQty.hashCode ^
        pickLocation.hashCode ^
        pickLocationDesc.hashCode;
  }

  @override
  String toString() {
    return 'MedItem(name: $name, dose: $dose, form: $form, pickAmount: $pickAmount, location: $location)';
  }
}
