#!/usr/bin/env python3
"""
Test script for emotion system fixes:
1. Dead state recovery bug fix
2. Sleeping emotion display
3. Tired emotion state
"""

import sys
import os
import time

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.pet import Pet
from modules import config


def test_dead_state_fix():
    """Test that dead pets cannot perform actions"""
    print("\n" + "="*60)
    print("TEST 1: Dead State Recovery Bug Fix")
    print("="*60)

    # Create a pet with 0 health (dead)
    pet = Pet("TestPet", health=0, hunger=50, happiness=50, energy=50)
    print(f"Initial state: {pet}")
    print(f"Is alive: {pet.is_alive()}")
    print(f"Emotion: {pet.get_emotion_state()}")

    # Try to perform actions on dead pet
    print("\nAttempting to feed dead pet...")
    changes = pet.feed()
    print(f"Changes returned: {changes}")
    print(f"Health after feed: {pet.health}")
    assert pet.health == 0, "Dead pet health should remain 0 after feed"
    assert changes == {}, "Feed should return empty dict for dead pet"

    print("\nAttempting to clean dead pet...")
    changes = pet.clean()
    print(f"Changes returned: {changes}")
    print(f"Health after clean: {pet.health}")
    assert pet.health == 0, "Dead pet health should remain 0 after clean"
    assert changes == {}, "Clean should return empty dict for dead pet"

    print("\nAttempting to make dead pet sleep...")
    changes = pet.sleep()
    print(f"Changes returned: {changes}")
    print(f"Health after sleep: {pet.health}")
    assert pet.health == 0, "Dead pet health should remain 0 after sleep"
    assert changes == {}, "Sleep should return empty dict for dead pet"

    print("\n✓ PASS: Dead pets cannot perform actions")


def test_sleeping_emotion():
    """Test that sleeping emotion displays after sleep action"""
    print("\n" + "="*60)
    print("TEST 2: Sleeping Emotion Display")
    print("="*60)

    # Create a healthy pet
    pet = Pet("TestPet", health=80, hunger=50, happiness=50, energy=30)
    print(f"Initial state: {pet}")
    print(f"Initial emotion: {pet.get_emotion_state()}")

    # Perform sleep action
    print("\nPutting pet to sleep...")
    changes = pet.sleep()
    print(f"Changes: {changes}")
    print(f"Is sleeping: {pet.is_sleeping}")
    print(f"Sleep timer: {pet.sleep_display_timer}")
    print(f"Emotion after sleep: {pet.get_emotion_state()}")

    assert pet.is_sleeping == True, "Pet should be in sleeping state"
    assert pet.sleep_display_timer == config.SLEEP_DISPLAY_DURATION, \
        f"Sleep timer should be {config.SLEEP_DISPLAY_DURATION}"
    assert pet.get_emotion_state() == "sleeping", "Emotion should be sleeping"

    # Tick timer partway
    print(f"\nTicking timer by 5 seconds...")
    pet.tick_sleep_timer(5.0)
    print(f"Sleep timer after 5s: {pet.sleep_display_timer}")
    print(f"Emotion: {pet.get_emotion_state()}")
    assert pet.sleep_display_timer == config.SLEEP_DISPLAY_DURATION - 5, \
        "Timer should decrease by 5"
    assert pet.get_emotion_state() == "sleeping", \
        "Should still be sleeping while timer > 0"

    # Tick timer to expiration
    print(f"\nTicking timer by {config.SLEEP_DISPLAY_DURATION} seconds...")
    pet.tick_sleep_timer(config.SLEEP_DISPLAY_DURATION)
    print(f"Sleep timer after expiration: {pet.sleep_display_timer}")
    print(f"Is sleeping: {pet.is_sleeping}")
    print(f"Emotion: {pet.get_emotion_state()}")

    assert pet.is_sleeping == False, "Pet should not be sleeping after timer expires"
    assert pet.sleep_display_timer == 0, "Timer should be 0"
    assert pet.get_emotion_state() != "sleeping", \
        "Emotion should not be sleeping after timer expires"

    print("\n✓ PASS: Sleeping emotion displays correctly")


def test_tired_emotion():
    """Test that tired emotion triggers when energy is low"""
    print("\n" + "="*60)
    print("TEST 3: Tired Emotion State")
    print("="*60)

    # Create a pet with low energy but otherwise okay stats
    pet = Pet("TestPet", health=80, hunger=50, happiness=50, energy=25)
    print(f"Initial state: {pet}")
    print(f"Energy: {pet.energy}")
    print(f"Emotion: {pet.get_emotion_state()}")

    assert pet.get_emotion_state() == "tired", \
        f"Pet with energy=25 should be tired, got {pet.get_emotion_state()}"

    # Test priority: tired should be lower priority than sick and hungry
    print("\nTesting emotion priority...")

    # Sick should override tired
    pet.health = 25
    print(f"Health={pet.health}, Energy={pet.energy}, Emotion={pet.get_emotion_state()}")
    assert pet.get_emotion_state() == "sick", "Sick should override tired"

    # Hungry should override tired
    pet.health = 80
    pet.hunger = 75
    print(f"Hunger={pet.hunger}, Energy={pet.energy}, Emotion={pet.get_emotion_state()}")
    assert pet.get_emotion_state() == "hungry", "Hungry should override tired"

    # Tired should override sad
    pet.hunger = 50
    pet.happiness = 25
    print(f"Happiness={pet.happiness}, Energy={pet.energy}, Emotion={pet.get_emotion_state()}")
    assert pet.get_emotion_state() == "tired", "Tired should override sad"

    # High energy should not be tired
    pet.energy = 80
    pet.happiness = 50
    print(f"\nEnergy={pet.energy}, Emotion={pet.get_emotion_state()}")
    assert pet.get_emotion_state() != "tired", \
        "Pet with high energy should not be tired"

    print("\n✓ PASS: Tired emotion triggers correctly")


def test_sleep_restores_energy():
    """Test that sleep action restores energy and prevents tired state"""
    print("\n" + "="*60)
    print("TEST 4: Sleep Action Restores Energy")
    print("="*60)

    # Create a tired pet
    pet = Pet("TestPet", health=80, hunger=50, happiness=50, energy=20)
    print(f"Initial state: {pet}")
    print(f"Initial energy: {pet.energy}")
    print(f"Initial emotion: {pet.get_emotion_state()}")
    assert pet.get_emotion_state() == "tired", "Pet should be tired"

    # Sleep action
    print("\nPutting pet to sleep...")
    changes = pet.sleep()
    print(f"Changes: {changes}")
    print(f"Energy after sleep: {pet.energy}")

    # Wait for sleep timer to expire
    print("\nWaiting for sleep timer to expire...")
    pet.tick_sleep_timer(config.SLEEP_DISPLAY_DURATION + 1)
    print(f"Emotion after sleep expires: {pet.get_emotion_state()}")

    assert pet.energy >= 70, f"Energy should be restored, got {pet.energy}"
    assert pet.get_emotion_state() != "tired", \
        "Pet should no longer be tired after sleeping"

    print("\n✓ PASS: Sleep restores energy and resolves tired state")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("EMOTION SYSTEM FIXES TEST SUITE")
    print("="*60)

    try:
        test_dead_state_fix()
        test_sleeping_emotion()
        test_tired_emotion()
        test_sleep_restores_energy()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        return True

    except AssertionError as e:
        print(f"\n✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
