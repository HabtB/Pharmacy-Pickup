import 'package:flutter/material.dart';
import '../models/med_item.dart';

class MedicationSearchDelegate extends SearchDelegate<int?> {
  final List<MedItem> medications;

  MedicationSearchDelegate(this.medications);

  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      IconButton(
        icon: const Icon(Icons.clear),
        onPressed: () {
          query = '';
        },
      ),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.arrow_back),
      onPressed: () {
        close(context, null);
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    return _buildList(context);
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    return _buildList(context);
  }

  Widget _buildList(BuildContext context) {
    final queryLower = query.toLowerCase();

    final List<int> matches = [];
    for (int i = 0; i < medications.length; i++) {
      final med = medications[i];
      if (med.name.toLowerCase().contains(queryLower) ||
          med.dose.toLowerCase().contains(queryLower) ||
          (med.location?.toLowerCase().contains(queryLower) ?? false)) {
        matches.add(i);
      }
    }

    if (matches.isEmpty) {
      return Center(
        child: Text(
          'No medications found for "$query"',
          style: Theme.of(context).textTheme.titleMedium,
        ),
      );
    }

    return ListView.builder(
      itemCount: matches.length,
      itemBuilder: (context, index) {
        final realIndex = matches[index];
        final med = medications[realIndex];

        final locationDesc = med.pickLocationDesc ?? med.location ?? 'Unknown Location';

        return ListTile(
          leading: CircleAvatar(
            backgroundColor: Colors.blue.shade50,
            child: const Icon(Icons.medication, color: Colors.blue),
          ),
          title: Text('${med.name} ${med.dose}'),
          subtitle: Text(locationDesc),
          trailing: Text('#${realIndex + 1}'),
          onTap: () {
            close(context, realIndex);
          },
        );
      },
    );
  }
}
