"""
Not-A-Gotchi Persistence Module

Handles all database operations using SQLite with Write-Ahead Logging (WAL)
for robust persistence across power cycles.
"""

import sqlite3
import os
import time
import json
from typing import Optional, Dict, Any, List
from . import config


class DatabaseManager:
    """Manages SQLite database for pet state and history"""

    def __init__(self, db_path: str = None):
        """Initialize database manager"""
        self.db_path = db_path or config.DATABASE_PATH
        self.connection = None
        self._ensure_data_directory()
        self._initialize_database()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

    def _initialize_database(self):
        """Initialize database connection and create tables if needed"""
        try:
            self.connection = sqlite3.connect(
                self.db_path,
                timeout=config.DB_TIMEOUT,
                check_same_thread=config.DB_CHECK_SAME_THREAD
            )

            # Enable Write-Ahead Logging for better concurrency and crash recovery
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")

            # Create tables
            self._create_tables()

            print(f"Database initialized: {self.db_path}")

        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            raise

    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.connection.cursor()

        # Pet State Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pet_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hunger INTEGER NOT NULL DEFAULT 50,
                happiness INTEGER NOT NULL DEFAULT 75,
                health INTEGER NOT NULL DEFAULT 100,
                energy INTEGER NOT NULL DEFAULT 100,
                birth_time REAL NOT NULL,
                last_update REAL NOT NULL,
                last_sleep_time REAL,
                evolution_stage INTEGER NOT NULL DEFAULT 0,
                age_seconds INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL DEFAULT (julianday('now'))
            )
        ''')

        # Migrate existing databases to add energy and last_sleep_time columns
        try:
            cursor.execute("SELECT energy FROM pet_state LIMIT 1")
        except:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE pet_state ADD COLUMN energy INTEGER NOT NULL DEFAULT 100")
            print("Database migrated: Added energy column")

        try:
            cursor.execute("SELECT last_sleep_time FROM pet_state LIMIT 1")
        except:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE pet_state ADD COLUMN last_sleep_time REAL")
            print("Database migrated: Added last_sleep_time column")

        # Pet History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pet_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                stat_changes TEXT,
                notes TEXT,
                FOREIGN KEY (pet_id) REFERENCES pet_state(id)
            )
        ''')

        # System Config Table (key-value store)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL DEFAULT (julianday('now'))
            )
        ''')

        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pet_active
            ON pet_state(is_active)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_history_pet
            ON pet_history(pet_id, timestamp)
        ''')

        self.connection.commit()

    def get_active_pet(self) -> Optional[Dict[str, Any]]:
        """Get the currently active pet"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT id, name, hunger, happiness, health, energy, birth_time,
                       last_update, last_sleep_time, evolution_stage, age_seconds
                FROM pet_state
                WHERE is_active = 1
                ORDER BY id DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'hunger': row[2],
                    'happiness': row[3],
                    'health': row[4],
                    'energy': row[5],
                    'birth_time': row[6],
                    'last_update': row[7],
                    'last_sleep_time': row[8],
                    'evolution_stage': row[9],
                    'age_seconds': row[10]
                }
            return None

        except sqlite3.Error as e:
            print(f"Error retrieving active pet: {e}")
            return None

    def create_pet(self, name: str, hunger: int = None, happiness: int = None,
                   health: int = None, energy: int = None) -> Optional[int]:
        """Create a new pet and return its ID"""
        try:
            current_time = time.time()

            # Deactivate any existing active pets
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE pet_state
                SET is_active = 0
                WHERE is_active = 1
            ''')

            # Create new pet
            cursor.execute('''
                INSERT INTO pet_state
                (name, hunger, happiness, health, energy, birth_time, last_update,
                 last_sleep_time, evolution_stage, age_seconds, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1, ?)
            ''', (
                name,
                hunger if hunger is not None else config.INITIAL_HUNGER,
                happiness if happiness is not None else config.INITIAL_HAPPINESS,
                health if health is not None else config.INITIAL_HEALTH,
                energy if energy is not None else config.INITIAL_ENERGY,
                current_time,
                current_time,
                current_time,  # last_sleep_time initialized to birth time
                current_time
            ))

            pet_id = cursor.lastrowid
            self.connection.commit()

            # Log creation event
            self.log_event(pet_id, "created", notes=f"Pet '{name}' created")

            print(f"New pet created: {name} (ID: {pet_id})")
            return pet_id

        except sqlite3.Error as e:
            print(f"Error creating pet: {e}")
            self.connection.rollback()
            return None

    def update_pet(self, pet_id: int, hunger: int = None, happiness: int = None,
                   health: int = None, energy: int = None, evolution_stage: int = None,
                   age_seconds: int = None, last_update: float = None,
                   last_sleep_time: float = None) -> bool:
        """Update pet stats"""
        try:
            updates = []
            params = []

            if hunger is not None:
                updates.append("hunger = ?")
                params.append(max(config.STAT_MIN, min(config.STAT_MAX, hunger)))

            if happiness is not None:
                updates.append("happiness = ?")
                params.append(max(config.STAT_MIN, min(config.STAT_MAX, happiness)))

            if health is not None:
                updates.append("health = ?")
                params.append(max(config.STAT_MIN, min(config.STAT_MAX, health)))

            if energy is not None:
                updates.append("energy = ?")
                params.append(max(config.STAT_MIN, min(config.STAT_MAX, energy)))

            if evolution_stage is not None:
                updates.append("evolution_stage = ?")
                params.append(evolution_stage)

            if age_seconds is not None:
                updates.append("age_seconds = ?")
                params.append(age_seconds)

            if last_sleep_time is not None:
                updates.append("last_sleep_time = ?")
                params.append(last_sleep_time)

            if last_update is not None:
                updates.append("last_update = ?")
                params.append(last_update)
            else:
                updates.append("last_update = ?")
                params.append(time.time())

            if not updates:
                return True  # Nothing to update

            query = f"UPDATE pet_state SET {', '.join(updates)} WHERE id = ?"
            params.append(pet_id)

            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()

            return True

        except sqlite3.Error as e:
            print(f"Error updating pet: {e}")
            self.connection.rollback()
            return False

    def log_event(self, pet_id: int, event_type: str,
                  stat_changes: Dict[str, int] = None, notes: str = None) -> bool:
        """Log a pet event to history"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO pet_history (pet_id, timestamp, event_type, stat_changes, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                pet_id,
                time.time(),
                event_type,
                json.dumps(stat_changes) if stat_changes else None,
                notes
            ))

            self.connection.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error logging event: {e}")
            self.connection.rollback()
            return False

    def get_pet_history(self, pet_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent history for a pet"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT timestamp, event_type, stat_changes, notes
                FROM pet_history
                WHERE pet_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (pet_id, limit))

            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row[0],
                    'event_type': row[1],
                    'stat_changes': json.loads(row[2]) if row[2] else None,
                    'notes': row[3]
                })

            return history

        except sqlite3.Error as e:
            print(f"Error retrieving history: {e}")
            return []

    def set_config(self, key: str, value: Any) -> bool:
        """Set a configuration value"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, json.dumps(value), time.time()))

            self.connection.commit()
            return True

        except sqlite3.Error as e:
            print(f"Error setting config: {e}")
            self.connection.rollback()
            return False

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT value FROM system_config WHERE key = ?
            ''', (key,))

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default

        except sqlite3.Error as e:
            print(f"Error getting config: {e}")
            return default

    def check_integrity(self) -> bool:
        """Check database integrity"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            return result[0] == "ok"

        except sqlite3.Error as e:
            print(f"Database integrity check failed: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
