"""
Auth routes — login and session management.
"""
import jwt
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify

import database_manager
from config import JWT_SECRET, JWT_EXPIRY_HOURS

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    role = data.get('role', 'picker')  # Default role is picker

    # Validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400

    # Only allow picker role for self-registration (admins created separately)
    if role not in ['picker', 'pharmacist']:
        role = 'picker'

    try:
        user_id = database_manager.create_user(username, password, role)
        if user_id:
            logger.info(f"New user registered: {username} (role: {role})")
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'id': user_id,
                    'username': username,
                    'role': role
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Username already exists'}), 409
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    user = database_manager.verify_user(username, password)
    if user:
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
            'iat': datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@auth_bp.route('/api/save_session', methods=['POST'])
def save_session():
    data = request.json
    user_id = data.get('user_id')
    items = data.get('items')

    if not user_id or not items:
        return jsonify({'success': False, 'message': 'Missing user_id or items'}), 400

    session_id = database_manager.save_pick_session(user_id, items)

    if session_id:
        return jsonify({'success': True, 'message': 'Session saved', 'session_id': session_id})
    else:
        return jsonify({'success': False, 'message': 'Failed to save session'}), 500
