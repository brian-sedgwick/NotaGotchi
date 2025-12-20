"""
Not-A-Gotchi Friend Status Poller

Background thread that periodically polls friend presence to update online status.
Uses parallel checking with ThreadPoolExecutor for efficient multi-friend polling.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Callable, Optional, Tuple, List
from modules.logging_config import get_logger
from modules import config

logger = get_logger("friend_status_poller")


class FriendStatusPoller:
    """
    Background thread that periodically polls friend presence.

    Features:
    - Parallel friend checking (ThreadPoolExecutor)
    - Configurable polling interval (default 15s)
    - Status change detection and notification
    - Thread-safe database updates
    """

    def __init__(self, friend_manager, wifi_manager,
                 polling_interval: float = None,
                 check_timeout: float = None,
                 max_parallel_checks: int = None):
        """
        Initialize the friend status poller.

        Args:
            friend_manager: FriendManager instance for database operations
            wifi_manager: WiFiManager instance for network checks
            polling_interval: Seconds between polls (default from config)
            check_timeout: Seconds to wait per device (default from config)
            max_parallel_checks: Max concurrent checks (default from config)
        """
        self.friends = friend_manager
        self.wifi = wifi_manager

        # Configuration
        self.polling_interval = polling_interval or config.FRIEND_POLL_INTERVAL
        self.check_timeout = check_timeout or config.FRIEND_CHECK_TIMEOUT
        self.max_parallel_checks = max_parallel_checks or config.FRIEND_MAX_PARALLEL_CHECKS

        # Thread management
        self.running = False
        self.poller_thread = None
        self._lock = threading.Lock()

        # UI callbacks
        self.on_friend_online: Optional[Callable[[str], None]] = None
        self.on_friend_offline: Optional[Callable[[str], None]] = None

        # Track previous online status for change detection
        self._previous_status: Dict[str, bool] = {}

        logger.info(f"FriendStatusPoller initialized: interval={self.polling_interval}s, "
                   f"timeout={self.check_timeout}s, max_parallel={self.max_parallel_checks}")

    def start(self) -> None:
        """Start the background polling thread."""
        with self._lock:
            if self.running:
                logger.warning("Friend status poller already running")
                return

            self.running = True
            self.poller_thread = threading.Thread(
                target=self._poller_loop,
                daemon=True,
                name="FriendStatusPoller"
            )
            self.poller_thread.start()
            logger.info("Friend status poller started")

    def stop(self) -> None:
        """Stop the background polling thread."""
        with self._lock:
            if not self.running:
                logger.warning("Friend status poller not running")
                return

            self.running = False

        # Wait for thread to finish (with timeout)
        if self.poller_thread and self.poller_thread.is_alive():
            self.poller_thread.join(timeout=2.0)

            if self.poller_thread.is_alive():
                logger.warning("Friend status poller thread did not terminate cleanly")
            else:
                logger.info("Friend status poller stopped")

    def _poller_loop(self) -> None:
        """
        Main polling loop (runs in background thread).

        Wakes up periodically, checks all friends in parallel,
        and triggers callbacks on status changes.
        """
        logger.info("Friend status poller loop started")

        while self.running:
            try:
                # Poll all friends
                start_time = time.time()
                reachability_map = self._poll_all_friends()
                elapsed = time.time() - start_time

                logger.debug(f"Polled {len(reachability_map)} friends in {elapsed:.2f}s")

                # Detect status changes and trigger callbacks
                self._detect_status_changes(reachability_map)

                # Sleep until next poll
                # Adjust sleep time to maintain consistent interval
                sleep_time = max(0.1, self.polling_interval - elapsed)

                # Break sleep into small chunks to allow quick shutdown
                sleep_end = time.time() + sleep_time
                while self.running and time.time() < sleep_end:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error in poller loop: {e}", exc_info=True)
                # Continue running despite errors
                time.sleep(1.0)

        logger.info("Friend status poller loop exited")

    def _poll_all_friends(self) -> Dict[str, bool]:
        """
        Check all friends in parallel.

        Returns:
            Dict mapping device_name to reachability (True/False)
        """
        friends = self.friends.get_friends()

        if not friends:
            return {}

        reachability_map = {}

        # Check all friends concurrently
        with ThreadPoolExecutor(max_workers=self.max_parallel_checks) as executor:
            # Submit all checks at once
            futures = {
                executor.submit(self._check_friend_reachability, friend): friend
                for friend in friends
            }

            # Collect results as they complete
            for future in as_completed(futures, timeout=self.check_timeout + 1):
                try:
                    device_name, is_reachable = future.result()
                    reachability_map[device_name] = is_reachable

                    # Update last_seen if reachable (thread-safe)
                    if is_reachable:
                        friend = futures[future]
                        self.friends.update_friend_contact(
                            device_name,
                            friend['ip'],
                            friend['port']
                        )
                        logger.debug(f"Friend {device_name} is reachable")
                    else:
                        logger.debug(f"Friend {device_name} is not reachable")

                except Exception as e:
                    # Mark as unreachable on error
                    friend = futures[future]
                    device_name = friend['device_name']
                    reachability_map[device_name] = False
                    logger.warning(f"Error checking friend {device_name}: {e}")

        return reachability_map

    def _check_friend_reachability(self, friend: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Check if a single friend is reachable (runs in ThreadPoolExecutor).

        Args:
            friend: Friend dict with device_name, ip, port

        Returns:
            Tuple of (device_name, is_reachable)
        """
        device_name = friend['device_name']

        if not friend.get('ip') or not friend.get('port'):
            logger.debug(f"Friend {device_name} has no IP/port, marking unreachable")
            return (device_name, False)

        try:
            # Use existing WiFiManager.is_device_reachable()
            is_reachable = self.wifi.is_device_reachable(
                friend['ip'],
                friend['port'],
                timeout=self.check_timeout
            )

            return (device_name, is_reachable)

        except Exception as e:
            logger.warning(f"Exception checking {device_name}: {e}")
            return (device_name, False)

    def _detect_status_changes(self, reachability_map: Dict[str, bool]) -> None:
        """
        Detect online/offline transitions and trigger callbacks.

        Args:
            reachability_map: Dict mapping device_name to current reachability
        """
        current_time = time.time()
        friends = self.friends.get_friends()

        for friend in friends:
            device_name = friend['device_name']
            pet_name = friend['pet_name']

            # Get previous status
            was_online = self._previous_status.get(device_name, False)

            # Determine current status
            # Online if: reachable OR last_seen within threshold
            is_reachable = reachability_map.get(device_name, False)
            last_seen = friend.get('last_seen')

            now_online = is_reachable or (
                last_seen and
                (current_time - last_seen) < config.FRIEND_ONLINE_THRESHOLD
            )

            # Update tracking
            self._previous_status[device_name] = now_online

            # Detect transitions
            if now_online and not was_online:
                # Friend came online
                logger.info(f"Friend came online: {pet_name} ({device_name})")
                print(f"✅ {pet_name} came online")

                if self.on_friend_online:
                    try:
                        self.on_friend_online(device_name)
                    except Exception as e:
                        logger.error(f"Error in on_friend_online callback: {e}", exc_info=True)

            elif not now_online and was_online:
                # Friend went offline
                logger.info(f"Friend went offline: {pet_name} ({device_name})")
                print(f"⚠️  {pet_name} went offline")

                if self.on_friend_offline:
                    try:
                        self.on_friend_offline(device_name)
                    except Exception as e:
                        logger.error(f"Error in on_friend_offline callback: {e}", exc_info=True)
