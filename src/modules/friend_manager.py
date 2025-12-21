"""
Friend Manager Module

Manages friend relationships and friend requests for NotaGotchi social features.

Features:
- Send/accept/reject friend requests
- Verify friendship status
- Track friend online status
- Auto-expire old friend requests
- Update friend IP/port on contact
"""

import time
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from . import config


class FriendManager:
    """
    Manages friend relationships and friend requests

    Friend Request Flow:
    1. Device A sends friend request to Device B
    2. Request stored in friend_requests table on Device B
    3. Device B user accepts/rejects request
    4. On accept: both devices add each other to friends table
    5. Messaging now allowed between friends
    """

    def __init__(self, db_connection: sqlite3.Connection, own_device_name: str,
                 db_lock: threading.RLock = None):
        """
        Initialize Friend Manager

        Args:
            db_connection: SQLite database connection
            own_device_name: This device's name (e.g., "notagotchi_Buddy")
            db_lock: Optional shared database lock for thread safety
        """
        self.connection = db_connection
        self.own_device_name = own_device_name
        self._lock = db_lock or threading.RLock()

    @contextmanager
    def _db_lock(self):
        """Context manager for thread-safe database access"""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    # ========================================================================
    # FRIEND REQUEST METHODS
    # ========================================================================

    def receive_friend_request(self, from_device_name: str, from_pet_name: str,
                              from_ip: str, from_port: int) -> bool:
        """
        Receive and store an incoming friend request

        Args:
            from_device_name: Device name of requester
            from_pet_name: Pet name of requester
            from_ip: IP address of requester
            from_port: Port of requester

        Returns:
            True if request stored, False if already exists or error
        """
        # Don't allow friend requests from self
        if from_device_name == self.own_device_name:
            return False

        with self._db_lock():
            try:
                # Check if already friends
                if self._is_friend_internal(from_device_name):
                    print(f"Already friends with {from_device_name}")
                    return False

                # Check if there's already a pending request from this device
                existing = self._get_pending_request_internal(from_device_name)
                if existing:
                    print(f"Friend request from {from_device_name} already exists")
                    return False

                # Clean up expired requests
                self._cleanup_expired_requests_internal()

                # Calculate expiration time
                current_time = time.time()
                expires_at = current_time + (config.FRIEND_REQUEST_EXPIRATION_HOURS * 3600)

                # Store request
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO friend_requests
                    (from_device_name, from_pet_name, from_ip, from_port,
                     status, request_time, expires_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                ''', (from_device_name, from_pet_name, from_ip, from_port,
                      current_time, expires_at))

                self.connection.commit()
                print(f"✅ Friend request received from {from_pet_name} ({from_device_name})")
                return True

            except sqlite3.IntegrityError:
                print(f"Friend request from {from_device_name} already exists")
                return False
            except sqlite3.Error as e:
                print(f"❌ Error storing friend request: {e}")
                self.connection.rollback()
                return False

    def accept_friend_request(self, from_device_name: str) -> Optional[Dict[str, Any]]:
        """
        Accept a pending friend request and establish friendship

        Args:
            from_device_name: Device name to accept

        Returns:
            Friend info dict if successful, None otherwise
        """
        with self._db_lock():
            try:
                # Get the pending request
                request = self._get_pending_request_internal(from_device_name)
                if not request:
                    print(f"❌ No pending friend request from {from_device_name}")
                    return None

                # Check if expired
                if time.time() > request['expires_at']:
                    print(f"❌ Friend request from {from_device_name} has expired")
                    self._delete_request_internal(from_device_name)
                    return None

                current_time = time.time()
                cursor = self.connection.cursor()

                # Begin explicit transaction for atomicity
                cursor.execute('BEGIN IMMEDIATE')

                try:
                    # Add to friends table
                    cursor.execute('''
                        INSERT INTO friends
                        (device_name, pet_name, last_ip, last_port, last_seen, friendship_established)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (request['from_device_name'], request['from_pet_name'],
                          request['from_ip'], request['from_port'],
                          current_time, current_time))

                    # Update request status
                    cursor.execute('''
                        UPDATE friend_requests
                        SET status = 'accepted', response_time = ?
                        WHERE from_device_name = ? AND status = 'pending'
                    ''', (current_time, from_device_name))

                    self.connection.commit()

                except Exception:
                    self.connection.rollback()
                    raise

                friend_info = {
                    'device_name': request['from_device_name'],
                    'pet_name': request['from_pet_name'],
                    'ip': request['from_ip'],
                    'port': request['from_port']
                }

                print(f"✅ Friend request accepted: {request['from_pet_name']}")
                return friend_info

            except sqlite3.Error as e:
                print(f"❌ Error accepting friend request: {e}")
                self.connection.rollback()
                return None

    def reject_friend_request(self, from_device_name: str) -> bool:
        """
        Reject a pending friend request (deletes the record to allow re-sending)

        Args:
            from_device_name: Device name to reject

        Returns:
            True if rejected successfully
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                cursor.execute('''
                    DELETE FROM friend_requests
                    WHERE from_device_name = ? AND status = 'pending'
                ''', (from_device_name,))

                if cursor.rowcount > 0:
                    self.connection.commit()
                    print(f"Friend request rejected and deleted: {from_device_name}")
                    return True
                else:
                    print(f"No pending friend request from {from_device_name}")
                    return False

            except sqlite3.Error as e:
                print(f"❌ Error rejecting friend request: {e}")
                self.connection.rollback()
                return False

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """
        Get all pending friend requests (not expired)

        Returns:
            List of pending friend request dicts
        """
        with self._db_lock():
            try:
                # Clean up expired requests first
                self._cleanup_expired_requests_internal()

                cursor = self.connection.cursor()
                current_time = time.time()

                cursor.execute('''
                    SELECT from_device_name, from_pet_name, from_ip, from_port,
                           request_time, expires_at
                    FROM friend_requests
                    WHERE status = 'pending' AND expires_at > ?
                    ORDER BY request_time DESC
                ''', (current_time,))

                requests = []
                for row in cursor.fetchall():
                    requests.append({
                        'device_name': row[0],
                        'pet_name': row[1],
                        'ip': row[2],
                        'port': row[3],
                        'request_time': row[4],
                        'expires_at': row[5],
                        'hours_until_expiry': (row[5] - current_time) / 3600
                    })

                return requests

            except sqlite3.Error as e:
                print(f"❌ Error getting pending requests: {e}")
                return []

    # ========================================================================
    # FRIEND MANAGEMENT METHODS
    # ========================================================================

    def get_friends(self, online_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of friends

        Args:
            online_only: If True, only return friends seen recently

        Returns:
            List of friend dicts
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                if online_only:
                    # Consider "online" if seen in last 5 minutes
                    cutoff_time = time.time() - 300
                    cursor.execute('''
                        SELECT device_name, pet_name, last_ip, last_port, last_seen,
                               friendship_established
                        FROM friends
                        WHERE last_seen > ? AND device_name != ?
                        ORDER BY last_seen DESC
                    ''', (cutoff_time, self.own_device_name))
                else:
                    cursor.execute('''
                        SELECT device_name, pet_name, last_ip, last_port, last_seen,
                               friendship_established
                        FROM friends
                        WHERE device_name != ?
                        ORDER BY last_seen DESC
                    ''', (self.own_device_name,))

                friends = []
                current_time = time.time()

                for row in cursor.fetchall():
                    is_online = row[4] and (current_time - row[4]) < 300 if row[4] else False

                    friends.append({
                        'device_name': row[0],
                        'pet_name': row[1],
                        'ip': row[2],
                        'port': row[3],
                        'last_seen': row[4],
                        'friendship_established': row[5],
                        'is_online': is_online,
                        'minutes_since_seen': (current_time - row[4]) / 60 if row[4] else None
                    })

                return friends

            except sqlite3.Error as e:
                print(f"❌ Error getting friends: {e}")
                return []

    def get_friend(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Get info about a specific friend

        Args:
            device_name: Friend's device name

        Returns:
            Friend info dict or None if not found
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT device_name, pet_name, last_ip, last_port, last_seen,
                           friendship_established
                    FROM friends
                    WHERE device_name = ?
                ''', (device_name,))

                row = cursor.fetchone()
                if row:
                    current_time = time.time()
                    is_online = row[4] and (current_time - row[4]) < 300 if row[4] else False

                    return {
                        'device_name': row[0],
                        'pet_name': row[1],
                        'ip': row[2],
                        'port': row[3],
                        'last_seen': row[4],
                        'friendship_established': row[5],
                        'is_online': is_online
                    }

                return None

            except sqlite3.Error as e:
                print(f"❌ Error getting friend: {e}")
                return None

    def _is_friend_internal(self, device_name: str) -> bool:
        """Internal is_friend check without lock - for use within locked context"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT 1 FROM friends WHERE device_name = ?
            ''', (device_name,))
            return cursor.fetchone() is not None
        except sqlite3.Error:
            return False

    def is_friend(self, device_name: str) -> bool:
        """
        Check if a device is in friends list

        Args:
            device_name: Device name to check

        Returns:
            True if device is a friend
        """
        with self._db_lock():
            return self._is_friend_internal(device_name)

    def update_friend_contact(self, device_name: str, ip: str, port: int) -> bool:
        """
        Update friend's last known IP/port and last seen time

        Called when we successfully contact a friend

        Args:
            device_name: Friend's device name
            ip: Friend's current IP
            port: Friend's current port

        Returns:
            True if updated successfully
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                cursor.execute('''
                    UPDATE friends
                    SET last_ip = ?, last_port = ?, last_seen = ?
                    WHERE device_name = ?
                ''', (ip, port, current_time, device_name))

                if cursor.rowcount > 0:
                    self.connection.commit()
                    return True
                else:
                    print(f"⚠️  Friend {device_name} not found for update")
                    return False

            except sqlite3.Error as e:
                print(f"❌ Error updating friend contact: {e}")
                self.connection.rollback()
                return False

    def add_friend(self, device_name: str, pet_name: str,
                   ip: str, port: int) -> bool:
        """
        Add a friend directly to the friends list.

        Used when someone accepts OUR friend request - we add them as a friend
        without going through the request flow.

        Args:
            device_name: Friend's device name
            pet_name: Friend's pet name
            ip: Friend's IP address
            port: Friend's port

        Returns:
            True if added successfully
        """
        # Check if already friends
        if self.is_friend(device_name):
            print(f"Already friends with {device_name}")
            return False

        # Check friend limit
        if not self.can_add_more_friends():
            print(f"❌ Friend limit reached ({config.MAX_FRIENDS} friends)")
            return False

        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                cursor.execute('''
                    INSERT INTO friends
                    (device_name, pet_name, last_ip, last_port, last_seen, friendship_established)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (device_name, pet_name, ip, port, current_time, current_time))

                self.connection.commit()
                print(f"✅ {pet_name} added to friends!")
                return True

            except sqlite3.Error as e:
                print(f"❌ Error adding friend: {e}")
                self.connection.rollback()
                return False

    def remove_friend(self, device_name: str) -> bool:
        """
        Remove a friend from the friends list

        Args:
            device_name: Device name to remove

        Returns:
            True if removed successfully
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('''
                    DELETE FROM friends WHERE device_name = ?
                ''', (device_name,))

                if cursor.rowcount > 0:
                    self.connection.commit()
                    print(f"Friend removed: {device_name}")
                    return True
                else:
                    print(f"Friend not found: {device_name}")
                    return False

            except sqlite3.Error as e:
                print(f"❌ Error removing friend: {e}")
                self.connection.rollback()
                return False

    def get_friend_count(self) -> int:
        """
        Get total number of friends

        Returns:
            Friend count
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('SELECT COUNT(*) FROM friends')
                return cursor.fetchone()[0]

            except sqlite3.Error as e:
                print(f"❌ Error counting friends: {e}")
                return 0

    def can_add_more_friends(self) -> bool:
        """
        Check if we can add more friends (haven't hit limit)

        Returns:
            True if under the MAX_FRIENDS limit
        """
        return self.get_friend_count() < config.MAX_FRIENDS

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    def _get_pending_request_internal(self, from_device_name: str) -> Optional[Dict[str, Any]]:
        """Internal get_pending_request without lock - for use within locked context"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT from_device_name, from_pet_name, from_ip, from_port,
                       request_time, expires_at
                FROM friend_requests
                WHERE from_device_name = ? AND status = 'pending'
            ''', (from_device_name,))

            row = cursor.fetchone()
            if row:
                return {
                    'from_device_name': row[0],
                    'from_pet_name': row[1],
                    'from_ip': row[2],
                    'from_port': row[3],
                    'request_time': row[4],
                    'expires_at': row[5]
                }

            return None

        except sqlite3.Error as e:
            print(f"❌ Error getting pending request: {e}")
            return None

    def _get_pending_request(self, from_device_name: str) -> Optional[Dict[str, Any]]:
        """Get a pending friend request by device name"""
        with self._db_lock():
            return self._get_pending_request_internal(from_device_name)

    def _cleanup_expired_requests_internal(self) -> int:
        """Internal cleanup without lock - for use within locked context"""
        try:
            cursor = self.connection.cursor()
            current_time = time.time()

            cursor.execute('''
                DELETE FROM friend_requests
                WHERE status = 'pending' AND expires_at < ?
            ''', (current_time,))

            deleted_count = cursor.rowcount

            if deleted_count > 0:
                self.connection.commit()
                print(f"Cleaned up {deleted_count} expired friend request(s)")

            return deleted_count

        except sqlite3.Error as e:
            print(f"❌ Error cleaning up expired requests: {e}")
            self.connection.rollback()
            return 0

    def _cleanup_expired_requests(self) -> int:
        """
        Delete expired friend requests

        Returns:
            Number of requests deleted
        """
        with self._db_lock():
            return self._cleanup_expired_requests_internal()

    def _delete_request_internal(self, from_device_name: str) -> bool:
        """Internal delete_request without lock - for use within locked context"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                DELETE FROM friend_requests WHERE from_device_name = ?
            ''', (from_device_name,))

            self.connection.commit()
            return True

        except sqlite3.Error as e:
            print(f"❌ Error deleting request: {e}")
            self.connection.rollback()
            return False

    def _delete_request(self, from_device_name: str) -> bool:
        """Delete a friend request"""
        with self._db_lock():
            return self._delete_request_internal(from_device_name)
