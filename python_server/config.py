"""
Centralized configuration — all settings read from environment variables.
"""
import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# --- Flask ---
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', '').lower() == 'true'

# --- JWT ---
_jwt_from_env = os.environ.get('JWT_SECRET')
if _jwt_from_env:
    JWT_SECRET = _jwt_from_env
else:
    JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "\n" + "!" * 70 +
        "\n!!! JWT_SECRET env var is NOT set."
        "\n!!! Generated a random secret for this session."
        "\n!!! All tokens will be INVALIDATED on server restart."
        "\n!!! Set JWT_SECRET in your .env or environment for persistent sessions."
        "\n" + "!" * 70
    )

JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))

# --- Default Users (seeded on startup) ---
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
PICKER_USERNAME = os.environ.get('PICKER_USERNAME', 'user')
PICKER_PASSWORD = os.environ.get('PICKER_PASSWORD')

# --- Server ---
SERVER_HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.environ.get('SERVER_PORT', '5003'))
