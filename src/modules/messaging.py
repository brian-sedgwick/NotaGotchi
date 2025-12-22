"""
Messaging Module

Handles message sending/receiving with queue and retry logic for NotaGotchi.

Features:
- Send messages to friends (text, emoji, preset)
- Queue messages for offline friends
- Retry with exponential backoff
- Message history and conversation tracking
- Unread message counts
- Mark messages as read
"""

import time
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Callable
from . import config


class MessageManager:
    """
    Manages messaging between NotaGotchi friends

    Message Flow:
    1. User sends message → queued in message_queue
    2. Queue processor attempts delivery
    3. On success: move to messages table (delivered)
    4. On failure: retry with exponential backoff
    5. After max retries: mark as failed
    """

    def __init__(self, db_connection: sqlite3.Connection, wifi_manager,
                 friend_manager, own_device_name: str,
                 db_lock: threading.RLock = None):
        """
        Initialize Message Manager

        Args:
            db_connection: SQLite database connection
            wifi_manager: WiFiManager instance
            friend_manager: FriendManager instance
            own_device_name: This device's name
            db_lock: Optional shared database lock for thread safety
        """
        self.connection = db_connection
        self.wifi = wifi_manager
        self.friends = friend_manager
        self.own_device_name = own_device_name
        self._lock = db_lock or threading.RLock()

        # Queue processor thread
        self.queue_processor_thread = None
        self.queue_running = False
        self.queue_lock = threading.Lock()

        # Callbacks for UI notifications
        self.on_message_received: Optional[Callable] = None
        self.on_message_delivered: Optional[Callable] = None
        self.on_message_failed: Optional[Callable] = None

    @contextmanager
    def _db_lock(self):
        """Context manager for thread-safe database access"""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    # ========================================================================
    # MESSAGE SENDING
    # ========================================================================

    # Valid content types for messages
    VALID_CONTENT_TYPES = {'text', 'emoji', 'preset'}

    def send_message(self, to_device_name: str, content: str,
                    content_type: str = "text") -> Optional[str]:
        """
        Send a message to a friend (queues if friend offline)

        Args:
            to_device_name: Friend's device name
            content: Message content
            content_type: Type of content (text, emoji, preset)

        Returns:
            Message ID if queued successfully, None if error
        """
        # Validate content is not None or empty
        if content is None:
            print("❌ Cannot send message: content is None")
            return None

        if not isinstance(content, str):
            print(f"❌ Cannot send message: content must be a string, got {type(content)}")
            return None

        # Strip whitespace and check if empty
        content = content.strip()
        if not content:
            print("❌ Cannot send message: content is empty")
            return None

        # Validate content type
        if content_type not in self.VALID_CONTENT_TYPES:
            print(f"❌ Invalid content type: {content_type}. Must be one of {self.VALID_CONTENT_TYPES}")
            return None

        # Verify friendship
        if not self.friends.is_friend(to_device_name):
            print(f"❌ Cannot send message: {to_device_name} is not a friend")
            return None

        # Validate content length
        if len(content) > config.MESSAGE_MAX_LENGTH:
            print(f"❌ Message too long: {len(content)} chars (max {config.MESSAGE_MAX_LENGTH})")
            return None

        # Generate message ID
        message_id = f"msg_{int(time.time()*1000)}_{self.own_device_name}"

        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                # Add to outgoing queue
                cursor.execute('''
                    INSERT INTO message_queue
                    (message_id, to_device_name, content, content_type, status,
                     attempts, created_at, next_retry)
                    VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)
                ''', (message_id, to_device_name, content, content_type,
                      current_time, current_time))

                self.connection.commit()

                print(f"✅ Message queued for {to_device_name}: {content[:50]}...")

                # Trigger immediate delivery attempt (queue processor will handle it)
                return message_id

            except sqlite3.Error as e:
                print(f"❌ Error queueing message: {e}")
                self.connection.rollback()
                return None

    def _attempt_delivery(self, queue_item: Dict[str, Any]) -> bool:
        """
        Attempt to deliver a queued message

        Args:
            queue_item: Message queue item dict

        Returns:
            True if delivered successfully
        """
        message_id = queue_item['message_id']
        to_device_name = queue_item['to_device_name']
        content = queue_item['content']
        content_type = queue_item['content_type']

        # Get friend's current address
        friend = self.friends.get_friend(to_device_name)
        if not friend or not friend['ip'] or not friend['port']:
            print(f"⚠️  Cannot deliver to {to_device_name}: No known address")
            return False

        # Build message payload
        message_data = {
            "type": "message",
            "message_id": message_id,
            "from_device_name": self.own_device_name,
            "from_pet_name": self.friends.connection.execute(
                "SELECT name FROM pet_state WHERE is_active = 1"
            ).fetchone()[0] if self.connection else "Unknown",
            "content": content,
            "content_type": content_type,
            "timestamp": time.time()
        }

        # Attempt delivery via WiFi
        success = self.wifi.send_message(
            friend['ip'],
            friend['port'],
            message_data
        )

        if success:
            print(f"✅ Message delivered to {to_device_name}")

            # Update friend's last seen
            self.friends.update_friend_contact(
                to_device_name,
                friend['ip'],
                friend['port']
            )

            # Move from queue to delivered
            self._mark_delivered(queue_item)

            # Callback
            if self.on_message_delivered:
                self.on_message_delivered(message_id, to_device_name)

            return True
        else:
            print(f"⚠️  Failed to deliver message to {to_device_name}")
            return False

    def _mark_delivered(self, queue_item: Dict[str, Any]):
        """Mark message as delivered and remove from queue"""
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                # Update queue status
                cursor.execute('''
                    UPDATE message_queue
                    SET status = 'delivered', delivered_at = ?
                    WHERE message_id = ?
                ''', (current_time, queue_item['message_id']))

                self.connection.commit()

            except sqlite3.Error as e:
                print(f"❌ Error marking message as delivered: {e}")
                self.connection.rollback()

    def _mark_failed(self, queue_item: Dict[str, Any], error_message: str):
        """Mark message as permanently failed"""
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                cursor.execute('''
                    UPDATE message_queue
                    SET status = 'failed', failed_at = ?, error_message = ?
                    WHERE message_id = ?
                ''', (current_time, error_message, queue_item['message_id']))

                self.connection.commit()

                print(f"❌ Message {queue_item['message_id']} marked as failed: {error_message}")

            except sqlite3.Error as e:
                print(f"❌ Error marking message as failed: {e}")
                self.connection.rollback()

        # Callback outside lock
        if self.on_message_failed:
            self.on_message_failed(queue_item['message_id'], queue_item['to_device_name'])

    # ========================================================================
    # MESSAGE RECEIVING
    # ========================================================================

    def receive_message(self, from_device_name: str, from_pet_name: str,
                       message_id: str, content: str, content_type: str,
                       timestamp: float) -> bool:
        """
        Receive and store an incoming message

        Args:
            from_device_name: Sender's device name
            from_pet_name: Sender's pet name
            message_id: Unique message ID
            content: Message content
            content_type: Type of content
            timestamp: Message timestamp

        Returns:
            True if stored successfully
        """
        # Validate required fields
        if not from_device_name or not message_id:
            print("⚠️  Received message with missing required fields")
            return False

        # Validate content
        if content is None or not isinstance(content, str):
            print(f"⚠️  Received invalid message content from {from_device_name}")
            return False

        # Validate content type
        if content_type not in self.VALID_CONTENT_TYPES:
            print(f"⚠️  Received message with invalid content type: {content_type}")
            return False

        # Validate content length (prevent overflow attacks)
        if len(content) > config.MESSAGE_MAX_LENGTH:
            print(f"⚠️  Received oversized message from {from_device_name}: {len(content)} chars")
            return False

        # Verify sender is a friend
        if not self.friends.is_friend(from_device_name):
            print(f"⚠️  Received message from non-friend: {from_device_name}")
            return False

        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                # Check for duplicate
                cursor.execute('''
                    SELECT 1 FROM messages WHERE message_id = ?
                ''', (message_id,))

                if cursor.fetchone():
                    print(f"⚠️  Duplicate message: {message_id}")
                    return True  # Already have it, return success

                # Store message
                cursor.execute('''
                    INSERT INTO messages
                    (message_id, from_device_name, from_pet_name, to_device_name,
                     content, content_type, is_read, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                ''', (message_id, from_device_name, from_pet_name, self.own_device_name,
                      content, content_type, current_time))

                self.connection.commit()

                print(f"✅ Message received from {from_pet_name}: {content[:50]}...")

            except sqlite3.Error as e:
                print(f"❌ Error storing message: {e}")
                self.connection.rollback()
                return False

        # Callback outside lock to avoid holding lock during callback
        if self.on_message_received:
            self.on_message_received({
                'message_id': message_id,
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'content': content,
                'content_type': content_type,
                'timestamp': timestamp
            })

        return True

    # ========================================================================
    # MESSAGE HISTORY & QUERIES
    # ========================================================================

    def get_conversation_history(self, friend_device_name: str,
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history with a friend

        Args:
            friend_device_name: Friend's device name
            limit: Maximum number of messages

        Returns:
            List of message dicts (newest first)
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                # Get both sent and received messages
                cursor.execute('''
                    SELECT message_id, from_device_name, from_pet_name,
                           content, content_type, is_read, received_at
                    FROM messages
                    WHERE from_device_name = ? OR to_device_name = ?
                    ORDER BY received_at DESC
                    LIMIT ?
                ''', (friend_device_name, friend_device_name, limit))

                messages = []
                for row in cursor.fetchall():
                    is_from_friend = row[1] == friend_device_name

                    messages.append({
                        'message_id': row[0],
                        'from_device_name': row[1],
                        'from_pet_name': row[2],
                        'content': row[3],
                        'content_type': row[4],
                        'is_read': row[5] == 1,
                        'received_at': row[6],
                        'direction': 'received' if is_from_friend else 'sent'
                    })

                return messages

            except sqlite3.Error as e:
                print(f"❌ Error getting conversation history: {e}")
                return []

    def get_unread_count(self, friend_device_name: str = None) -> int:
        """
        Get count of unread messages

        Args:
            friend_device_name: If specified, count only from this friend

        Returns:
            Number of unread messages
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                if friend_device_name:
                    cursor.execute('''
                        SELECT COUNT(*) FROM messages
                        WHERE from_device_name = ? AND is_read = 0
                    ''', (friend_device_name,))
                else:
                    cursor.execute('''
                        SELECT COUNT(*) FROM messages WHERE is_read = 0
                    ''')

                return cursor.fetchone()[0]

            except sqlite3.Error as e:
                print(f"❌ Error getting unread count: {e}")
                return 0

    def mark_as_read(self, message_id: str = None, friend_device_name: str = None):
        """
        Mark message(s) as read

        Args:
            message_id: Specific message to mark (optional)
            friend_device_name: Mark all from this friend (optional)
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                if message_id:
                    cursor.execute('''
                        UPDATE messages
                        SET is_read = 1, read_at = ?
                        WHERE message_id = ?
                    ''', (current_time, message_id))
                elif friend_device_name:
                    cursor.execute('''
                        UPDATE messages
                        SET is_read = 1, read_at = ?
                        WHERE from_device_name = ? AND is_read = 0
                    ''', (current_time, friend_device_name))
                else:
                    print("⚠️  Must specify message_id or friend_device_name")
                    return

                self.connection.commit()

            except sqlite3.Error as e:
                print(f"❌ Error marking as read: {e}")
                self.connection.rollback()

    def get_inbox(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get inbox (all received messages)

        Args:
            limit: Maximum number of messages

        Returns:
            List of message dicts with friend info
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                cursor.execute('''
                    SELECT m.message_id, m.from_device_name, m.from_pet_name,
                           m.content, m.content_type, m.is_read, m.received_at,
                           f.last_seen
                    FROM messages m
                    LEFT JOIN friends f ON m.from_device_name = f.device_name
                    WHERE m.to_device_name = ?
                    ORDER BY m.received_at DESC
                    LIMIT ?
                ''', (self.own_device_name, limit))

                inbox = []
                for row in cursor.fetchall():
                    inbox.append({
                        'message_id': row[0],
                        'from_device_name': row[1],
                        'from_pet_name': row[2],
                        'content': row[3],
                        'content_type': row[4],
                        'is_read': row[5] == 1,
                        'received_at': row[6],
                        'friend_last_seen': row[7]
                    })

                return inbox

            except sqlite3.Error as e:
                print(f"❌ Error getting inbox: {e}")
                return []

    # ========================================================================
    # MESSAGE DELETION
    # ========================================================================

    def delete_message(self, message_id: str) -> bool:
        """
        Delete a single message by ID

        Args:
            message_id: Message ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('DELETE FROM messages WHERE message_id = ?', (message_id,))
                deleted = cursor.rowcount > 0
                self.connection.commit()

                if deleted:
                    print(f"✅ Message deleted: {message_id}")
                else:
                    print(f"⚠️  Message not found: {message_id}")

                return deleted
            except sqlite3.Error as e:
                print(f"❌ Error deleting message: {e}")
                self.connection.rollback()
                return False

    def delete_conversation(self, friend_device_name: str) -> int:
        """
        Delete all messages with a specific friend (both sent and received)

        Args:
            friend_device_name: Device name of friend

        Returns:
            Number of messages deleted
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('''
                    DELETE FROM messages
                    WHERE from_device_name = ? OR to_device_name = ?
                ''', (friend_device_name, friend_device_name))
                count = cursor.rowcount
                self.connection.commit()

                print(f"✅ Deleted {count} message(s) with {friend_device_name}")
                return count
            except sqlite3.Error as e:
                print(f"❌ Error deleting conversation: {e}")
                self.connection.rollback()
                return 0

    def get_conversation_message_count(self, friend_device_name: str) -> int:
        """
        Get count of messages in a conversation (for confirmation dialogs)

        Args:
            friend_device_name: Device name of friend

        Returns:
            Total number of messages (sent + received) with this friend
        """
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM messages
                    WHERE from_device_name = ? OR to_device_name = ?
                ''', (friend_device_name, friend_device_name))
                return cursor.fetchone()[0]
            except sqlite3.Error as e:
                print(f"❌ Error counting messages: {e}")
                return 0

    # ========================================================================
    # QUEUE PROCESSING
    # ========================================================================

    def start_queue_processor(self):
        """Start background queue processor thread"""
        if self.queue_running:
            print("Queue processor already running")
            return

        self.queue_running = True
        self.queue_processor_thread = threading.Thread(
            target=self._queue_processor_loop,
            name="MessageQueueProcessor",
            daemon=True
        )
        self.queue_processor_thread.start()
        print("✅ Message queue processor started")

    def stop_queue_processor(self):
        """Stop queue processor thread"""
        if not self.queue_running:
            return

        print("Stopping message queue processor...")
        self.queue_running = False

        if self.queue_processor_thread and self.queue_processor_thread.is_alive():
            self.queue_processor_thread.join(timeout=2.0)

        print("✅ Message queue processor stopped")

    def _queue_processor_loop(self):
        """Background loop to process message queue"""
        print("Message queue processor thread started")

        while self.queue_running:
            try:
                # Process pending messages
                self._process_pending_messages()

                # Sleep before next check
                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                print(f"❌ Queue processor error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(10)  # Longer sleep on error

        print("Message queue processor thread stopped")

    def _process_pending_messages(self):
        """Process all pending messages in queue"""
        # Get messages with lock, then process outside lock
        with self._db_lock():
            try:
                cursor = self.connection.cursor()
                current_time = time.time()

                # Get messages ready for retry
                cursor.execute('''
                    SELECT id, message_id, to_device_name, content, content_type,
                           attempts, created_at, last_attempt
                    FROM message_queue
                    WHERE status = 'pending'
                      AND (next_retry IS NULL OR next_retry <= ?)
                    ORDER BY created_at ASC
                    LIMIT 10
                ''', (current_time,))

                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'id': row[0],
                        'message_id': row[1],
                        'to_device_name': row[2],
                        'content': row[3],
                        'content_type': row[4],
                        'attempts': row[5],
                        'created_at': row[6],
                        'last_attempt': row[7]
                    })

            except sqlite3.Error as e:
                print(f"❌ Error processing queue: {e}")
                return

        # Process each message outside the lock
        for msg in messages:
            self._process_queue_item(msg)

    def _process_queue_item(self, queue_item: Dict[str, Any]):
        """Process a single queue item with retry logic"""
        message_id = queue_item['message_id']
        attempts = queue_item['attempts']

        # Check if max retries exceeded
        if attempts >= config.MESSAGE_RETRY_MAX_ATTEMPTS:
            self._mark_failed(queue_item, f"Max retries ({attempts}) exceeded")
            return

        # Attempt delivery
        success = self._attempt_delivery(queue_item)

        if not success:
            # Calculate next retry time with exponential backoff
            next_retry = self._calculate_next_retry(attempts)

            with self._db_lock():
                try:
                    cursor = self.connection.cursor()
                    current_time = time.time()

                    cursor.execute('''
                        UPDATE message_queue
                        SET attempts = attempts + 1,
                            last_attempt = ?,
                            next_retry = ?
                        WHERE message_id = ?
                    ''', (current_time, next_retry, message_id))

                    self.connection.commit()

                    print(f"⏳ Retry scheduled for {queue_item['to_device_name']} "
                          f"(attempt {attempts + 1}/{config.MESSAGE_RETRY_MAX_ATTEMPTS}) "
                          f"in {int(next_retry - current_time)}s")

                except sqlite3.Error as e:
                    print(f"❌ Error updating queue item: {e}")
                    self.connection.rollback()

    def _calculate_next_retry(self, attempts: int) -> float:
        """
        Calculate next retry time with exponential backoff

        Args:
            attempts: Number of previous attempts

        Returns:
            Unix timestamp for next retry
        """
        # Exponential backoff: 30s, 60s, 120s, 240s, ..., max 1800s (30 min)
        delay = min(
            config.MESSAGE_RETRY_INITIAL_DELAY * (2 ** attempts),
            config.MESSAGE_RETRY_MAX_DELAY
        )

        return time.time() + delay

    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._db_lock():
            try:
                cursor = self.connection.cursor()

                # Count by status
                cursor.execute('''
                    SELECT status, COUNT(*) FROM message_queue
                    GROUP BY status
                ''')

                status_counts = {}
                for row in cursor.fetchall():
                    status_counts[row[0]] = row[1]

                # Get oldest pending
                cursor.execute('''
                    SELECT created_at FROM message_queue
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                ''')

                oldest = cursor.fetchone()
                oldest_age = (time.time() - oldest[0]) if oldest else 0

                return {
                    'pending': status_counts.get('pending', 0),
                    'delivered': status_counts.get('delivered', 0),
                    'failed': status_counts.get('failed', 0),
                    'oldest_pending_age_seconds': oldest_age
                }

            except sqlite3.Error as e:
                print(f"❌ Error getting queue status: {e}")
                return {}
