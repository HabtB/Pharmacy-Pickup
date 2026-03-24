"""
Medication Locations — SQLite-backed storage for medication location data.

Replaces the CSV-based approach with a proper database table, supporting
CRUD operations and incremental sync for Flutter clients.
"""
import csv
import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_NAME = os.path.join(os.path.dirname(__file__), '..', 'pharmacy_data.db')


def _get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_locations_table():
    """Create the medication_locations table if it doesn't exist."""
    conn = _get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS medication_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            location_code TEXT NOT NULL,
            location_desc TEXT DEFAULT '',
            image_file TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Index for fast name lookups
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_med_loc_name
        ON medication_locations (name)
    ''')
    # Index for incremental sync
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_med_loc_updated
        ON medication_locations (updated_at)
    ''')
    conn.commit()
    conn.close()
    logger.info("medication_locations table initialized")


def import_from_csv(csv_path: str = None, force: bool = False) -> int:
    """
    One-time import of medication_locations.csv into SQLite.

    Args:
        csv_path: Path to CSV file. Defaults to medication_locations.csv in python_server/.
        force: If True, drops and recreates the table. If False, skips if data exists.

    Returns:
        Number of rows imported.
    """
    if csv_path is None:
        csv_path = os.path.join(
            os.path.dirname(__file__), '..', 'medication_locations.csv'
        )

    conn = _get_conn()

    # Check if data already exists
    if not force:
        count = conn.execute('SELECT COUNT(*) FROM medication_locations').fetchone()[0]
        if count > 0:
            logger.info(f"medication_locations already has {count} rows — skipping import")
            conn.close()
            return count

    if not os.path.exists(csv_path):
        logger.warning(f"CSV not found at {csv_path} — skipping import")
        conn.close()
        return 0

    logger.info(f"Importing medication locations from {csv_path}...")

    # Clear existing data if force
    if force:
        conn.execute('DELETE FROM medication_locations')

    now = datetime.now(timezone.utc).isoformat()
    imported = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header

        batch = []
        for row in reader:
            if len(row) < 2:
                continue

            med_name = row[0].strip()
            location_code = row[1].strip() if len(row) > 1 else ""
            # row[2] is empty in the CSV
            location_desc = row[3].strip() if len(row) > 3 else ""
            image_file = row[4].strip() if len(row) > 4 else ""

            if not med_name or not location_code:
                continue

            # Derive category from location_code
            category = _code_to_category(location_code)

            batch.append((med_name, category, location_code, location_desc, image_file, now, now))
            imported += 1

        conn.executemany(
            '''INSERT INTO medication_locations
               (name, category, location_code, location_desc, image_file, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            batch
        )

    conn.commit()
    conn.close()
    logger.info(f"✓ Imported {imported} medication locations from CSV")
    return imported


def _code_to_category(code: str) -> str:
    """Derive category from location code."""
    cats = {
        'PHRM': 'Pharmacy',
        'STR': 'Store Room',
        'VIT': 'Vitamins',
        'IV': 'IV Section',
        'FRIDGE': 'Refrigerated',
        'HIV': 'HIV',
    }
    return cats.get(code.upper(), code)


# ── CRUD Operations ────────────────────────────────────────────────────────

def get_all_locations(limit: int = 0, offset: int = 0,
                      updated_since: str = None) -> List[Dict]:
    """
    Get medication locations, optionally filtered by last update time.

    Args:
        limit: Max rows to return (0 = all)
        offset: Rows to skip
        updated_since: ISO timestamp — only return rows updated after this
    """
    conn = _get_conn()

    if updated_since:
        query = 'SELECT * FROM medication_locations WHERE updated_at > ? ORDER BY name'
        params: list = [updated_since]
    else:
        query = 'SELECT * FROM medication_locations ORDER BY name'
        params = []

    if limit > 0:
        query += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_location_count() -> int:
    """Get total number of medication locations."""
    conn = _get_conn()
    count = conn.execute('SELECT COUNT(*) FROM medication_locations').fetchone()[0]
    conn.close()
    return count


def search_locations(query: str, limit: int = 50) -> List[Dict]:
    """Search locations by medication name (LIKE match)."""
    conn = _get_conn()
    rows = conn.execute(
        'SELECT * FROM medication_locations WHERE name LIKE ? ORDER BY name LIMIT ?',
        (f'%{query}%', limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_location(name: str, location_code: str,
                 location_desc: str = '', image_file: str = '',
                 category: str = '') -> int:
    """Add a new medication location. Returns the new row ID."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    if not category:
        category = _code_to_category(location_code)

    cursor = conn.execute(
        '''INSERT INTO medication_locations
           (name, category, location_code, location_desc, image_file, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (name, category, location_code, location_desc, image_file, now, now)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def update_location(location_id: int, **fields) -> bool:
    """Update a medication location by ID. Returns True if updated."""
    allowed = {'name', 'category', 'location_code', 'location_desc', 'image_file'}
    updates = {k: v for k, v in fields.items() if k in allowed}

    if not updates:
        return False

    updates['updated_at'] = datetime.now(timezone.utc).isoformat()

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [location_id]

    conn = _get_conn()
    cursor = conn.execute(
        f'UPDATE medication_locations SET {set_clause} WHERE id = ?',
        values
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_location(location_id: int) -> bool:
    """Delete a medication location by ID. Returns True if deleted."""
    conn = _get_conn()
    cursor = conn.execute('DELETE FROM medication_locations WHERE id = ?', (location_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0
