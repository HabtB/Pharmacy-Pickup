"""
Location routes — CRUD API for medication location data.
"""
import logging
from flask import Blueprint, request, jsonify

from models.medication_locations import (
    get_all_locations, get_location_count, search_locations,
    add_location, update_location, delete_location,
)

logger = logging.getLogger(__name__)

locations_bp = Blueprint('locations', __name__)


@locations_bp.route('/api/locations', methods=['GET'])
def list_locations():
    """
    List medication locations.

    Query params:
        limit (int): max rows (default 0 = all)
        offset (int): pagination offset
        updated_since (str): ISO timestamp for incremental sync
    """
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    updated_since = request.args.get('updated_since')

    locations = get_all_locations(limit=limit, offset=offset, updated_since=updated_since)
    total = get_location_count()

    return jsonify({
        'success': True,
        'locations': locations,
        'total': total,
        'returned': len(locations),
    })


@locations_bp.route('/api/locations/search', methods=['GET'])
def search():
    """Search locations by medication name."""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify({'success': False, 'message': 'Query must be at least 2 characters'}), 400

    limit = request.args.get('limit', 50, type=int)
    results = search_locations(query, limit=limit)

    return jsonify({
        'success': True,
        'results': results,
        'count': len(results),
    })


@locations_bp.route('/api/locations', methods=['POST'])
def create_location():
    """Add a new medication location (admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    name = data.get('name', '').strip()
    location_code = data.get('location_code', '').strip()

    if not name or not location_code:
        return jsonify({'success': False, 'message': 'name and location_code are required'}), 400

    new_id = add_location(
        name=name,
        location_code=location_code,
        location_desc=data.get('location_desc', ''),
        image_file=data.get('image_file', ''),
        category=data.get('category', ''),
    )

    logger.info(f"Created medication location: {name} → {location_code} (id={new_id})")
    return jsonify({'success': True, 'id': new_id}), 201


@locations_bp.route('/api/locations/<int:location_id>', methods=['PUT'])
def modify_location(location_id):
    """Update a medication location (admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    updated = update_location(location_id, **data)

    if updated:
        logger.info(f"Updated medication location id={location_id}")
        return jsonify({'success': True, 'message': 'Location updated'})
    else:
        return jsonify({'success': False, 'message': 'Location not found or no changes'}), 404


@locations_bp.route('/api/locations/<int:location_id>', methods=['DELETE'])
def remove_location(location_id):
    """Delete a medication location (admin only)."""
    deleted = delete_location(location_id)

    if deleted:
        logger.info(f"Deleted medication location id={location_id}")
        return jsonify({'success': True, 'message': 'Location deleted'})
    else:
        return jsonify({'success': False, 'message': 'Location not found'}), 404
