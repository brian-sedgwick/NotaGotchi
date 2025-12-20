#!/usr/bin/env python3
"""
Quick cleanup script for friend list and friend requests.
Run from command line: python3 cleanup_friends.py
"""

import sqlite3
import os
import sys

# Database path (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # src/
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)               # NotaGotchi/
DATA_DIR = os.path.join(PROJECT_ROOT, "data")            # NotaGotchi/data/
DATABASE_PATH = os.path.join(DATA_DIR, "not-a-gotchi.db")


def cleanup():
    if not os.path.exists(DATABASE_PATH):
        print(f"Database not found: {DATABASE_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Count before cleanup
    cursor.execute("SELECT COUNT(*) FROM friends")
    friends_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM friend_requests")
    requests_count = cursor.fetchone()[0]

    print(f"Found {friends_count} friends, {requests_count} friend requests")

    # Clear tables
    cursor.execute("DELETE FROM friends")
    cursor.execute("DELETE FROM friend_requests")
    conn.commit()

    print("Cleared friends and friend_requests tables")
    conn.close()


if __name__ == "__main__":
    cleanup()
