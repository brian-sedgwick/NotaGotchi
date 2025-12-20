"""
Integration Tests for NotaGotchi

Tests that verify multiple components work together correctly.
"""

import sys
import os
import time
import unittest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import pytest, fall back to unittest
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from modules import config
from modules.pet import Pet, _clamp_stat, calculate_stat_degradation, apply_stat_changes
from modules.repositories import (
    InMemoryPetRepository,
    InMemoryFriendRepository,
    InMemoryFriendRequestRepository,
    InMemoryMessageRepository,
    PetData,
    FriendData,
    MessageData
)
from modules.action_handler import ActionHandler
from modules.message_handlers import (
    MessageHandlerRegistry,
    MessageHandlerContext,
    FriendRequestHandler,
    FriendRequestAcceptedHandler,
    ChatMessageHandler,
    create_default_registry
)
from modules.screen_state_machine import (
    ScreenStateMachine,
    ScreenPlugin,
    TransitionResult,
    create_default_state_machine
)
from modules.logging_config import setup_logging, get_logger
from modules.metrics import Timer, MovingAverage, PerformanceMetrics, get_metrics


class TestPetWithRepositoryIntegration:
    """Tests Pet logic working with repositories."""

    def test_create_pet_and_store_in_repository(self):
        """Pet can be created and stored in repository."""
        repo = InMemoryPetRepository()

        # Create pet via repository
        pet_id = repo.create_pet("Buddy", hunger=30, happiness=80)

        # Retrieve and verify
        pet_data = repo.get_active_pet()
        assert pet_data is not None
        assert pet_data.name == "Buddy"
        assert pet_data.hunger == 30
        assert pet_data.happiness == 80

    def test_pet_stat_updates_persist_to_repository(self):
        """Pet stat changes are properly persisted."""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Max", hunger=50)

        # Simulate feeding (reduce hunger)
        repo.update_pet(pet_id, hunger=20)

        # Verify persistence
        pet_data = repo.get_active_pet()
        assert pet_data.hunger == 20

    def test_pet_event_logging(self):
        """Pet events are logged to repository."""
        repo = InMemoryPetRepository()
        pet_id = repo.create_pet("Luna")

        # Log some events
        repo.log_event(pet_id, "feed", stat_changes={'hunger': -30})
        repo.log_event(pet_id, "play", stat_changes={'happiness': +20})

        # Check history
        history = repo.get_pet_history(pet_id)
        assert len(history) >= 2  # At least feed and play events


class TestMessageHandlerIntegration:
    """Tests message handling workflow."""

    def test_friend_request_workflow(self):
        """Complete friend request send/receive/accept workflow."""
        # Setup repositories
        friend_repo = InMemoryFriendRepository()
        request_repo = InMemoryFriendRequestRepository()

        # Setup handler registry
        registry = create_default_registry()

        # Create context with mock managers
        class MockFriendManager:
            def __init__(self, repo):
                self.repo = repo
                self.received_requests = []

            def receive_friend_request(self, device_name, pet_name, ip, port):
                expires = time.time() + 86400
                self.repo.create_request(device_name, pet_name, ip, port, expires)
                self.received_requests.append(device_name)
                return True

            def is_friend(self, device_name):
                return self.repo.is_friend(device_name)

            def add_friend(self, device_name, pet_name, ip, port):
                return friend_repo.add_friend(device_name, pet_name, ip, port)

        mock_friends = MockFriendManager(request_repo)

        context = MessageHandlerContext(
            friend_manager=mock_friends,
            message_manager=None,
            wifi_manager=None,
            own_pet_name="MyPet"
        )

        # Simulate receiving a friend request
        friend_request_msg = {
            'type': 'friend_request',
            'from_device_name': 'device_123',
            'from_pet_name': 'FriendPet',
            'from_ip': '192.168.1.100',
            'from_port': 5555
        }

        result = registry.handle_message(friend_request_msg, '192.168.1.100', context)
        assert result is True
        assert 'device_123' in mock_friends.received_requests

    def test_chat_message_requires_friendship(self):
        """Chat messages from non-friends are rejected."""
        friend_repo = InMemoryFriendRepository()
        registry = create_default_registry()

        class MockFriendManager:
            def is_friend(self, device_name):
                return friend_repo.is_friend(device_name)

        context = MessageHandlerContext(
            friend_manager=MockFriendManager(),
            message_manager=None,
            wifi_manager=None,
            own_pet_name="MyPet"
        )

        # Try to receive message from non-friend
        chat_msg = {
            'type': 'message',
            'from_device_name': 'stranger_device',
            'from_pet_name': 'Stranger',
            'content': 'Hello!',
            'content_type': 'text'
        }

        result = registry.handle_message(chat_msg, '192.168.1.200', context)
        assert result is False  # Should be rejected

    def test_unknown_message_type_handled_gracefully(self):
        """Unknown message types don't crash the system."""
        registry = create_default_registry()
        context = MessageHandlerContext(
            friend_manager=None,
            message_manager=None,
            wifi_manager=None,
            own_pet_name="MyPet"
        )

        unknown_msg = {
            'type': 'unknown_type',
            'data': 'something'
        }

        result = registry.handle_message(unknown_msg, '192.168.1.1', context)
        assert result is False  # Gracefully handled


class TestScreenStateMachineIntegration:
    """Tests screen navigation workflow."""

    def test_default_state_machine_has_all_screens(self):
        """Default state machine has all required screens registered."""
        sm = create_default_state_machine()

        required_screens = [
            config.ScreenState.HOME,
            config.ScreenState.MENU,
            config.ScreenState.CARE_MENU,
            config.ScreenState.FRIENDS_LIST,
            config.ScreenState.INBOX,
        ]

        for screen in required_screens:
            assert screen in sm.registered_states

    def test_navigation_workflow(self):
        """User can navigate through menu screens."""
        sm = create_default_state_machine()

        # Start at home
        assert sm.current_state == config.ScreenState.HOME

        # Go to menu
        result = sm.transition_to(config.ScreenState.MENU)
        assert result == TransitionResult.SUCCESS
        assert sm.current_state == config.ScreenState.MENU

        # Go to care menu
        result = sm.transition_to(config.ScreenState.CARE_MENU)
        assert result == TransitionResult.SUCCESS
        assert sm.current_state == config.ScreenState.CARE_MENU

        # Go back
        success = sm.go_back()
        assert success is True
        assert sm.current_state == config.ScreenState.MENU

    def test_go_home_clears_history(self):
        """Going home clears navigation history."""
        sm = create_default_state_machine()

        # Navigate around
        sm.transition_to(config.ScreenState.MENU)
        sm.transition_to(config.ScreenState.CARE_MENU)
        sm.transition_to(config.ScreenState.FRIENDS_LIST)

        # Verify history exists
        assert len(sm.get_history()) > 0

        # Go home
        sm.go_home()

        # History should be cleared
        assert len(sm.get_history()) == 0
        assert sm.current_state == config.ScreenState.HOME

    def test_state_data_persistence(self):
        """State-specific data persists across navigation."""
        sm = create_default_state_machine()

        # Set data for menu state
        sm.transition_to(config.ScreenState.MENU)
        sm.set_state_data('selected_index', 2)

        # Navigate away
        sm.transition_to(config.ScreenState.HOME)

        # Navigate back
        sm.transition_to(config.ScreenState.MENU)

        # Data should persist
        data = sm.get_state_data(config.ScreenState.MENU)
        assert data.get('selected_index') == 2


class TestMetricsIntegration:
    """Tests performance metrics collection."""

    def test_timer_measures_elapsed_time(self):
        """Timer accurately measures code execution time."""
        with Timer() as t:
            time.sleep(0.01)  # 10ms

        # Should be approximately 10ms (allow some variance)
        assert 5 < t.elapsed_ms < 50

    def test_moving_average_calculates_correctly(self):
        """Moving average produces correct results."""
        avg = MovingAverage(window_size=5)

        # Add 5 samples: 10, 20, 30, 40, 50
        for i in range(1, 6):
            avg.add(i * 10)

        # Average should be 30
        assert avg.average == 30.0
        assert avg.min == 10.0
        assert avg.max == 50.0
        assert avg.count == 5

    def test_moving_average_window_slides(self):
        """Moving average drops old values as new ones arrive."""
        avg = MovingAverage(window_size=3)

        # Add 3 samples
        avg.add(10)
        avg.add(20)
        avg.add(30)
        assert avg.average == 20.0

        # Add one more - oldest (10) should drop
        avg.add(40)
        # Now have: 20, 30, 40 -> average = 30
        assert avg.average == 30.0

    def test_metrics_records_and_summarizes(self):
        """PerformanceMetrics collects and summarizes data."""
        metrics = PerformanceMetrics()

        # Record some frame times
        for i in range(10):
            metrics.record_frame_time(10.0 + i)  # 10-19ms

        summary = metrics.get_summary()
        assert 'frame_time_ms' in summary
        assert summary['frame_time_ms']['count'] == 10
        assert summary['frame_time_ms']['min'] == 10.0
        assert summary['frame_time_ms']['max'] == 19.0


class TestLoggingIntegration:
    """Tests logging configuration."""

    def test_logger_creation(self):
        """Loggers can be created for modules."""
        logger = get_logger("test_module")
        assert logger is not None
        assert "notagotchi.test_module" in logger.name

    def test_multiple_loggers_same_hierarchy(self):
        """Multiple loggers share the same root."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Both should be under notagotchi namespace
        assert logger1.name.startswith("notagotchi.")
        assert logger2.name.startswith("notagotchi.")


class TestActionHandlerIntegration:
    """Tests ActionHandler with dependencies."""

    def test_action_handler_dependency_injection(self):
        """ActionHandler receives dependencies via callables."""
        # Create mock pet
        pet = Pet(name="TestPet", pet_id=1)

        # Track if callbacks were called
        save_called = False
        action_occurred_value = False

        def mock_save():
            nonlocal save_called
            save_called = True

        def mock_set_action(val):
            nonlocal action_occurred_value
            action_occurred_value = val

        # Create mock screen manager
        class MockScreenManager:
            def go_home(self):
                pass

        # Create mock db
        class MockDB:
            def log_event(self, *args, **kwargs):
                pass

        handler = ActionHandler(
            get_pet=lambda: pet,
            get_db=lambda: MockDB(),
            get_screen_manager=lambda: MockScreenManager(),
            get_social_coordinator=lambda: None,
            get_message_manager=lambda: None,
            save_pet=mock_save,
            set_action_occurred=mock_set_action,
            create_new_pet=lambda name: None
        )

        # Perform feed action
        result = handler.action_feed()

        assert result is True
        assert save_called is True
        assert action_occurred_value is True


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_pet_lifecycle_workflow(self):
        """Complete pet lifecycle: create, care, check stats."""
        # Create pet
        pet = Pet(name="E2E_Pet", pet_id=1)
        initial_hunger = pet.hunger

        # Feed pet
        changes = pet.feed()
        assert changes is not None
        assert pet.hunger < initial_hunger  # Hunger reduced

        # Play with pet
        initial_happiness = pet.happiness
        changes = pet.play()
        assert pet.happiness > initial_happiness  # Happiness increased

        # Check emotion
        emotion = pet.get_emotion_state()
        assert emotion in ['happy', 'content', 'excited']  # Should be positive

    def test_friend_and_message_workflow(self):
        """Complete social workflow: add friend, send message."""
        friend_repo = InMemoryFriendRepository()
        message_repo = InMemoryMessageRepository()

        # Add a friend
        friend_repo.add_friend("friend_device", "FriendPet", "192.168.1.50", 5555)

        # Verify friendship
        assert friend_repo.is_friend("friend_device") is True

        # Create a message
        message = MessageData(
            message_id="msg_001",
            from_device_name="my_device",
            from_pet_name="MyPet",
            to_device_name="friend_device",
            content="Hello friend!"
        )
        message_repo.save_message(message)

        # Retrieve message
        retrieved = message_repo.get_message("msg_001")
        assert retrieved is not None
        assert retrieved.content == "Hello friend!"


def run_tests_simple():
    """Run all tests without pytest."""
    test_classes = [
        TestPetWithRepositoryIntegration,
        TestMessageHandlerIntegration,
        TestScreenStateMachineIntegration,
        TestMetricsIntegration,
        TestLoggingIntegration,
        TestActionHandlerIntegration,
        TestEndToEndWorkflow
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
        print("Running integration tests...\n")
        success = run_tests_simple()
        sys.exit(0 if success else 1)
