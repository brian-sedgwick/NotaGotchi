"""
Unit tests for Repository implementations

Tests in-memory repository implementations for testing.
"""

import sys
import os
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import pytest, fall back to simple runner
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from modules.repositories import (
    PetData,
    FriendData,
    FriendRequestData,
    MessageData,
    InMemoryPetRepository,
    InMemoryFriendRepository,
    InMemoryFriendRequestRepository,
    InMemoryMessageRepository
)


class TestPetData:
    """Tests for PetData dataclass"""

    def test_default_values(self):
        """PetData should have sensible defaults"""
        pet = PetData()

        assert pet.id is None
        assert pet.name == ""
        assert pet.hunger == 50
        assert pet.happiness == 75
        assert pet.health == 100
        assert pet.energy == 100

    def test_to_dict(self):
        """to_dict should convert to dictionary"""
        pet = PetData(id=1, name="Buddy", hunger=30)
        data = pet.to_dict()

        assert data['id'] == 1
        assert data['name'] == "Buddy"
        assert data['hunger'] == 30

    def test_from_dict(self):
        """from_dict should create from dictionary"""
        data = {'id': 1, 'name': 'Buddy', 'hunger': 30}
        pet = PetData.from_dict(data)

        assert pet.id == 1
        assert pet.name == "Buddy"
        assert pet.hunger == 30


class TestInMemoryPetRepository:
    """Tests for InMemoryPetRepository"""

    def test_create_pet(self):
        """Should create a new pet and return ID"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy")

        assert pet_id is not None
        assert pet_id == 1

    def test_create_multiple_pets(self):
        """Should assign unique IDs to each pet"""
        repo = InMemoryPetRepository()
        id1 = repo.create_pet("Buddy")
        id2 = repo.create_pet("Max")

        assert id1 != id2

    def test_get_active_pet(self):
        """Should return the most recently created pet"""
        repo = InMemoryPetRepository()
        repo.create_pet("Buddy")
        repo.create_pet("Max")

        active = repo.get_active_pet()

        assert active is not None
        assert active.name == "Max"

    def test_get_active_pet_empty_repo(self):
        """Should return None when no pets exist"""
        repo = InMemoryPetRepository()
        assert repo.get_active_pet() is None

    def test_create_pet_with_custom_stats(self):
        """Should create pet with custom stats"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy", hunger=30, happiness=80)

        pet = repo.get_active_pet()

        assert pet.hunger == 30
        assert pet.happiness == 80

    def test_update_pet(self):
        """Should update pet stats"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy", hunger=50)

        success = repo.update_pet(pet_id, hunger=30)

        assert success
        pet = repo.get_active_pet()
        assert pet.hunger == 30

    def test_update_pet_clamps_stats(self):
        """Should clamp stats to valid range"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy")

        repo.update_pet(pet_id, hunger=150)  # Above max
        pet = repo.get_active_pet()
        assert pet.hunger == 100

        repo.update_pet(pet_id, happiness=-50)  # Below min
        pet = repo.get_active_pet()
        assert pet.happiness == 0

    def test_update_nonexistent_pet(self):
        """Should return False for nonexistent pet"""
        repo = InMemoryPetRepository()
        success = repo.update_pet(999, hunger=30)

        assert success is False

    def test_log_event(self):
        """Should log events"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy")

        success = repo.log_event(pet_id, "feed", stat_changes={'hunger': -30})

        assert success

    def test_get_pet_history(self):
        """Should retrieve pet history"""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Buddy")
        time.sleep(0.001)  # Ensure timestamp difference
        repo.log_event(pet_id, "feed", notes="Fed the pet")
        time.sleep(0.001)  # Ensure timestamp difference
        repo.log_event(pet_id, "play", notes="Played with pet")

        history = repo.get_pet_history(pet_id)

        # Should have 3 events: created + feed + play
        assert len(history) == 3
        # Verify all event types are present
        event_types = [h['event_type'] for h in history]
        assert 'created' in event_types
        assert 'feed' in event_types
        assert 'play' in event_types
        # Most recent (play) should be first
        assert history[0]['event_type'] == 'play'


class TestInMemoryFriendRepository:
    """Tests for InMemoryFriendRepository"""

    def test_add_friend(self):
        """Should add a new friend"""
        repo = InMemoryFriendRepository()
        success = repo.add_friend("device_123", "Max")

        assert success

    def test_add_duplicate_friend(self):
        """Should reject duplicate friend"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_123", "Max")

        success = repo.add_friend("device_123", "Different")

        assert success is False

    def test_get_friends(self):
        """Should return all friends"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_1", "Max")
        repo.add_friend("device_2", "Luna")

        friends = repo.get_friends()

        assert len(friends) == 2

    def test_get_friend(self):
        """Should return specific friend by device name"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_123", "Max", ip="192.168.1.100", port=5555)

        friend = repo.get_friend("device_123")

        assert friend is not None
        assert friend.pet_name == "Max"
        assert friend.last_ip == "192.168.1.100"

    def test_get_nonexistent_friend(self):
        """Should return None for nonexistent friend"""
        repo = InMemoryFriendRepository()
        assert repo.get_friend("nonexistent") is None

    def test_is_friend(self):
        """Should check if device is a friend"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_123", "Max")

        assert repo.is_friend("device_123") is True
        assert repo.is_friend("unknown") is False

    def test_update_friend(self):
        """Should update friend information"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_123", "Max")

        success = repo.update_friend("device_123", last_ip="192.168.1.200")

        assert success
        friend = repo.get_friend("device_123")
        assert friend.last_ip == "192.168.1.200"

    def test_remove_friend(self):
        """Should remove a friend"""
        repo = InMemoryFriendRepository()
        repo.add_friend("device_123", "Max")

        success = repo.remove_friend("device_123")

        assert success
        assert repo.is_friend("device_123") is False


class TestInMemoryFriendRequestRepository:
    """Tests for InMemoryFriendRequestRepository"""

    def test_create_request(self):
        """Should create a friend request"""
        repo = InMemoryFriendRequestRepository()
        expires = time.time() + 86400  # 24 hours

        success = repo.create_request(
            "device_123", "Max", "192.168.1.100", 5555, expires
        )

        assert success

    def test_get_pending_requests(self):
        """Should return pending requests"""
        repo = InMemoryFriendRequestRepository()
        expires = time.time() + 86400

        repo.create_request("device_1", "Max", "192.168.1.100", 5555, expires)
        repo.create_request("device_2", "Luna", "192.168.1.101", 5555, expires)

        pending = repo.get_pending_requests()

        assert len(pending) == 2

    def test_get_pending_excludes_expired(self):
        """Should exclude expired requests"""
        repo = InMemoryFriendRequestRepository()

        # Create expired request
        expired = time.time() - 100
        repo.create_request("device_1", "Max", "192.168.1.100", 5555, expired)

        # Create valid request
        valid = time.time() + 86400
        repo.create_request("device_2", "Luna", "192.168.1.101", 5555, valid)

        pending = repo.get_pending_requests()

        assert len(pending) == 1
        assert pending[0].from_pet_name == "Luna"

    def test_get_request(self):
        """Should get specific request"""
        repo = InMemoryFriendRequestRepository()
        expires = time.time() + 86400
        repo.create_request("device_123", "Max", "192.168.1.100", 5555, expires)

        request = repo.get_request("device_123")

        assert request is not None
        assert request.from_pet_name == "Max"

    def test_update_request_status(self):
        """Should update request status"""
        repo = InMemoryFriendRequestRepository()
        expires = time.time() + 86400
        repo.create_request("device_123", "Max", "192.168.1.100", 5555, expires)

        success = repo.update_request_status("device_123", "accepted")

        assert success
        request = repo.get_request("device_123")
        assert request.status == "accepted"

    def test_delete_request(self):
        """Should delete a request"""
        repo = InMemoryFriendRequestRepository()
        expires = time.time() + 86400
        repo.create_request("device_123", "Max", "192.168.1.100", 5555, expires)

        success = repo.delete_request("device_123")

        assert success
        assert repo.get_request("device_123") is None

    def test_cleanup_expired(self):
        """Should remove expired requests"""
        repo = InMemoryFriendRequestRepository()

        # Create expired request
        expired = time.time() - 100
        repo.create_request("device_1", "Max", "192.168.1.100", 5555, expired)

        # Create valid request
        valid = time.time() + 86400
        repo.create_request("device_2", "Luna", "192.168.1.101", 5555, valid)

        count = repo.cleanup_expired()

        assert count == 1
        assert repo.get_request("device_1") is None
        assert repo.get_request("device_2") is not None


class TestInMemoryMessageRepository:
    """Tests for InMemoryMessageRepository"""

    def test_save_message(self):
        """Should save a message"""
        repo = InMemoryMessageRepository()
        message = MessageData(
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="device_2",
            content="Hello!"
        )

        success = repo.save_message(message)

        assert success

    def test_get_message(self):
        """Should retrieve a message by ID"""
        repo = InMemoryMessageRepository()
        message = MessageData(
            message_id="msg_123",
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="device_2",
            content="Hello!"
        )
        repo.save_message(message)

        retrieved = repo.get_message("msg_123")

        assert retrieved is not None
        assert retrieved.content == "Hello!"

    def test_get_messages(self):
        """Should retrieve all messages"""
        repo = InMemoryMessageRepository()

        for i in range(3):
            message = MessageData(
                message_id=f"msg_{i}",
                from_device_name=f"device_{i}",
                from_pet_name=f"Pet{i}",
                to_device_name="me",
                content=f"Message {i}"
            )
            repo.save_message(message)

        messages = repo.get_messages()

        assert len(messages) == 3

    def test_get_messages_filtered_by_device(self):
        """Should filter messages by device"""
        repo = InMemoryMessageRepository()

        msg1 = MessageData(
            message_id="msg_1",
            from_device_name="device_a",
            from_pet_name="Max",
            to_device_name="me",
            content="From A"
        )
        msg2 = MessageData(
            message_id="msg_2",
            from_device_name="device_b",
            from_pet_name="Luna",
            to_device_name="me",
            content="From B"
        )
        repo.save_message(msg1)
        repo.save_message(msg2)

        messages = repo.get_messages(device_name="device_a")

        assert len(messages) == 1
        assert messages[0].from_pet_name == "Max"

    def test_get_messages_unread_only(self):
        """Should filter unread messages"""
        repo = InMemoryMessageRepository()

        msg1 = MessageData(
            message_id="msg_1",
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="me",
            content="Unread",
            is_read=False
        )
        msg2 = MessageData(
            message_id="msg_2",
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="me",
            content="Read",
            is_read=True
        )
        repo.save_message(msg1)
        repo.save_message(msg2)

        messages = repo.get_messages(unread_only=True)

        assert len(messages) == 1
        assert messages[0].content == "Unread"

    def test_mark_read(self):
        """Should mark message as read"""
        repo = InMemoryMessageRepository()
        message = MessageData(
            message_id="msg_123",
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="me",
            content="Hello!",
            is_read=False
        )
        repo.save_message(message)

        success = repo.mark_read("msg_123")

        assert success
        retrieved = repo.get_message("msg_123")
        assert retrieved.is_read is True
        assert retrieved.read_at is not None

    def test_get_unread_count(self):
        """Should return count of unread messages"""
        repo = InMemoryMessageRepository()

        for i in range(5):
            message = MessageData(
                message_id=f"msg_{i}",
                from_device_name="device_1",
                from_pet_name="Max",
                to_device_name="me",
                content=f"Message {i}",
                is_read=(i < 2)  # First 2 are read
            )
            repo.save_message(message)

        count = repo.get_unread_count()

        assert count == 3  # 5 total - 2 read = 3 unread

    def test_delete_message(self):
        """Should delete a message"""
        repo = InMemoryMessageRepository()
        message = MessageData(
            message_id="msg_123",
            from_device_name="device_1",
            from_pet_name="Max",
            to_device_name="me",
            content="Hello!"
        )
        repo.save_message(message)

        success = repo.delete_message("msg_123")

        assert success
        assert repo.get_message("msg_123") is None


def run_tests_simple():
    """Run all tests without pytest."""
    test_classes = [
        TestPetData,
        TestInMemoryPetRepository,
        TestInMemoryFriendRepository,
        TestInMemoryFriendRequestRepository,
        TestInMemoryMessageRepository
    ]

    passed = 0
    failed = 0
    errors = []

    for test_class in test_classes:
        class_name = test_class.__name__
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith('test_'):
                test_method = getattr(instance, method_name)
                full_name = f"{class_name}.{method_name}"

                try:
                    test_method()
                    print(f"  PASS: {full_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  FAIL: {full_name}")
                    print(f"        {e}")
                    failed += 1
                    errors.append((full_name, str(e)))
                except Exception as e:
                    print(f"  ERROR: {full_name}")
                    print(f"         {type(e).__name__}: {e}")
                    failed += 1
                    errors.append((full_name, f"{type(e).__name__}: {e}"))

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")

    if errors:
        print("\nFailures:")
        for name, error in errors:
            print(f"  - {name}: {error}")

    return failed == 0


if __name__ == '__main__':
    if HAS_PYTEST:
        pytest.main([__file__, '-v'])
    else:
        print("Running repository tests...\n")
        success = run_tests_simple()
        sys.exit(0 if success else 1)
