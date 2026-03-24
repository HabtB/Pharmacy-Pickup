import sqlite3
import hashlib
import os
import json
import bcrypt
from datetime import datetime

DB_NAME = "pharmacy_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'picker',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Pick Sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS pick_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'completed',
            total_items INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create Pick Items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS pick_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            med_name TEXT NOT NULL,
            med_id TEXT,
            expected_qty INTEGER,
            actual_qty INTEGER,
            location TEXT,
            is_picked BOOLEAN DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES pick_sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized.")

def hash_password(password):
    """Hash a password using bcrypt (slow, brute-force resistant)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _is_bcrypt_hash(h):
    """Check if a stored hash is bcrypt format (starts with $2b$)."""
    return h.startswith('$2b$') or h.startswith('$2a$')

def _legacy_sha256(password):
    """Old SHA-256 hash for backward compatibility."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role='picker'):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  (username, password_hash, role))
        conn.commit()
        print(f"User {username} created.")
        return True
    except sqlite3.IntegrityError:
        print(f"User {username} already exists.")
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()

    if not user:
        conn.close()
        return None

    stored_hash = user['password_hash']

    # Try bcrypt first (new format)
    if _is_bcrypt_hash(stored_hash):
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            conn.close()
            return dict(user)
    else:
        # Backward compatibility: verify against legacy SHA-256 hash
        if stored_hash == _legacy_sha256(password):
            # Auto-upgrade to bcrypt on successful login
            new_hash = hash_password(password)
            c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user['id']))
            conn.commit()
            print(f"User {username}: password hash upgraded from SHA-256 to bcrypt.")
            conn.close()
            return dict(user)

    conn.close()
    return None

def save_pick_session(user_id, items):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Create session
        c.execute('INSERT INTO pick_sessions (user_id, status, total_items, end_time) VALUES (?, ?, ?, ?)',
                  (user_id, 'completed', len(items), datetime.now()))
        session_id = c.lastrowid
        
        # Insert items
        for item in items:
            c.execute('''
                INSERT INTO pick_items (
                    session_id, med_name, med_id, expected_qty, actual_qty, location, is_picked
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                item.get('name', 'Unknown'),
                item.get('med_id', ''),
                item.get('pick_amount', 0),
                item.get('actual_picked_amount', item.get('pick_amount', 0)), # Default to pick_amount if actual not set
                item.get('location', ''),
                item.get('is_picked', False)
            ))
        
        conn.commit()
        return session_id
    except Exception as e:
        print(f"Error saving session: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# Initialize DB on import if not exists
if not os.path.exists(DB_NAME):
    init_db()
