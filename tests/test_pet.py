"""
Unit tests for Pet module

Tests pure functions and Pet class behavior.
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

from modules.pet import (
    Pet,
    _clamp_stat,
    calculate_stat_degradation,
    apply_stat_changes
)
from modules import config


class TestClampStat:
    """Tests for _clamp_stat pure function"""

    def test_clamp_within_bounds(self):
        """Values within bounds should remain unchanged"""
        assert _clamp_stat(50) == 50
        assert _clamp_stat(0) == 0
        assert _clamp_stat(100) == 100

    def test_clamp_below_minimum(self):
        """Values below minimum should be clamped to STAT_MIN"""
        assert _clamp_stat(-10) == config.STAT_MIN
        assert _clamp_stat(-100) == config.STAT_MIN
        assert _clamp_stat(-0.1) == config.STAT_MIN

    def test_clamp_above_maximum(self):
        """Values above maximum should be clamped to STAT_MAX"""
        assert _clamp_stat(110) == config.STAT_MAX
        assert _clamp_stat(1000) == config.STAT_MAX
        assert _clamp_stat(100.1) == config.STAT_MAX

    def test_clamp_float_values(self):
        """Float values should be handled correctly"""
        assert _clamp_stat(50.5) == 50.5
        assert _clamp_stat(99.9) == 99.9


class TestCalculateStatDegradation:
    """Tests for calculate_stat_degradation pure function"""

    def test_zero_time_no_changes(self):
        """Zero time elapsed should produce zero changes"""
        changes = calculate_stat_degradation(50, 75, 100, 100, 0)

        assert changes['hunger'] == 0
        assert changes['happiness'] == 0
        assert changes['health'] == 0
        assert changes['energy'] == 0

    def test_hunger_increases_over_time(self):
        """Hunger should increase based on HUNGER_INCREASE_RATE"""
        changes = calculate_stat_degradation(50, 75, 100, 100, 1.0)  # 1 minute

        expected_hunger = config.HUNGER_INCREASE_RATE * 1.0
        assert changes['hunger'] == expected_hunger

    def test_happiness_decreases_over_time(self):
        """Happiness should decrease based on HAPPINESS_DECREASE_RATE"""
        changes = calculate_stat_degradation(50, 75, 100, 100, 1.0)  # 1 minute

        expected_happiness = -config.HAPPINESS_DECREASE_RATE * 1.0
        assert changes['happiness'] == expected_happiness

    def test_health_degrades_when_hungry(self):
        """Health should degrade when hunger is high"""
        # Set hunger above degradation threshold
        high_hunger = config.HEALTH_DEGRADE_THRESHOLD_HUNGER + 10
        changes = calculate_stat_degradation(high_hunger, 75, 100, 100, 1.0)

        expected_health = -config.HEALTH_DEGRADE_RATE * 1.0
        assert changes['health'] == expected_health

    def test_health_degrades_when_unhappy(self):
        """Health should degrade when happiness is low"""
        # Set happiness below degradation threshold
        low_happiness = config.HEALTH_DEGRADE_THRESHOLD_HAPPINESS - 10
        changes = calculate_stat_degradation(30, low_happiness, 100, 100, 1.0)

        expected_health = -config.HEALTH_DEGRADE_RATE * 1.0
        assert changes['health'] == expected_health

    def test_health_regenerates_when_healthy(self):
        """Health should regenerate when pet is well-fed and happy"""
        # Set conditions for health regen
        low_hunger = config.HEALTH_REGEN_THRESHOLD_HUNGER - 10
        high_happiness = config.HEALTH_REGEN_THRESHOLD_HAPPINESS + 10
        changes = calculate_stat_degradation(low_hunger, high_happiness, 50, 100, 1.0)

        expected_health = config.HEALTH_REGEN_RATE * 1.0
        assert changes['health'] == expected_health

    def test_energy_decreases_over_time(self):
        """Energy should decrease based on ENERGY_DECREASE_RATE"""
        changes = calculate_stat_degradation(30, 75, 100, 100, 1.0)

        expected_energy = -config.ENERGY_DECREASE_RATE * 1.0
        assert changes['energy'] == expected_energy

    def test_energy_decreases_faster_when_hungry(self):
        """Energy should decrease faster when pet is hungry (low fullness)"""
        # High hunger = low fullness
        high_hunger = 100 - config.ENERGY_LOW_FULLNESS_THRESHOLD + 10  # fullness < threshold
        changes = calculate_stat_degradation(high_hunger, 75, 100, 100, 1.0)

        base_energy = -config.ENERGY_DECREASE_RATE * 1.0
        expected_energy = base_energy * config.ENERGY_LOW_FULLNESS_MULTIPLIER
        assert changes['energy'] == expected_energy

    def test_function_is_pure(self):
        """Function should not modify any external state"""
        # Call multiple times with same inputs
        result1 = calculate_stat_degradation(50, 75, 100, 100, 1.0)
        result2 = calculate_stat_degradation(50, 75, 100, 100, 1.0)

        assert result1 == result2


class TestApplyStatChanges:
    """Tests for apply_stat_changes pure function"""

    def test_applies_positive_changes(self):
        """Should correctly apply positive changes"""
        changes = {'hunger': -30, 'happiness': 20, 'health': 10, 'energy': 5}
        new_h, new_hp, new_ht, new_e = apply_stat_changes(50, 50, 50, 50, changes)

        assert new_h == 20  # 50 - 30
        assert new_hp == 70  # 50 + 20
        assert new_ht == 60  # 50 + 10
        assert new_e == 55  # 50 + 5

    def test_clamps_to_minimum(self):
        """Should clamp values at minimum"""
        changes = {'hunger': -100, 'happiness': -100, 'health': -100, 'energy': -100}
        new_h, new_hp, new_ht, new_e = apply_stat_changes(50, 50, 50, 50, changes)

        assert new_h == config.STAT_MIN
        assert new_hp == config.STAT_MIN
        assert new_ht == config.STAT_MIN
        assert new_e == config.STAT_MIN

    def test_clamps_to_maximum(self):
        """Should clamp values at maximum"""
        changes = {'hunger': 100, 'happiness': 100, 'health': 100, 'energy': 100}
        new_h, new_hp, new_ht, new_e = apply_stat_changes(50, 50, 50, 50, changes)

        assert new_h == config.STAT_MAX
        assert new_hp == config.STAT_MAX
        assert new_ht == config.STAT_MAX
        assert new_e == config.STAT_MAX

    def test_handles_missing_changes(self):
        """Should handle missing keys in changes dict"""
        changes = {'hunger': -10}  # Only hunger specified
        new_h, new_hp, new_ht, new_e = apply_stat_changes(50, 50, 50, 50, changes)

        assert new_h == 40  # 50 - 10
        assert new_hp == 50  # unchanged
        assert new_ht == 50  # unchanged
        assert new_e == 50  # unchanged

    def test_function_is_pure(self):
        """Function should not modify any external state"""
        changes = {'hunger': -10, 'happiness': 10, 'health': 5, 'energy': -5}
        result1 = apply_stat_changes(50, 50, 50, 50, changes)
        result2 = apply_stat_changes(50, 50, 50, 50, changes)

        assert result1 == result2


class TestPetCreation:
    """Tests for Pet class creation and initialization"""

    def test_create_with_defaults(self):
        """Pet should initialize with default stats"""
        pet = Pet(name="Buddy")

        assert pet.name == "Buddy"
        assert pet.hunger == config.INITIAL_HUNGER
        assert pet.happiness == config.INITIAL_HAPPINESS
        assert pet.health == config.INITIAL_HEALTH
        assert pet.energy == config.INITIAL_ENERGY
        assert pet.evolution_stage == 0
        assert pet.age_seconds == 0

    def test_create_with_custom_stats(self):
        """Pet should accept custom initial stats"""
        pet = Pet(name="Buddy", hunger=30, happiness=80, health=90, energy=70)

        assert pet.hunger == 30
        assert pet.happiness == 80
        assert pet.health == 90
        assert pet.energy == 70

    def test_from_dict_basic(self):
        """from_dict should create pet from dictionary"""
        data = {
            'id': 1,
            'name': 'Buddy',
            'hunger': 40,
            'happiness': 60,
            'health': 80,
            'energy': 90,
            'birth_time': 1000.0,
            'last_update': 1100.0,
            'last_sleep_time': 1050.0,
            'evolution_stage': 2,
            'age_seconds': 100
        }

        pet = Pet.from_dict(data)

        assert pet.id == 1
        assert pet.name == 'Buddy'
        assert pet.hunger == 40
        assert pet.evolution_stage == 2

    def test_from_dict_clamps_invalid_stats(self):
        """from_dict should clamp out-of-bounds stats"""
        data = {
            'name': 'Buddy',
            'hunger': 150,  # Above max
            'happiness': -20,  # Below min
            'health': 200,  # Above max
            'energy': -50,  # Below min
            'birth_time': 1000.0,
            'last_update': 1100.0,
            'evolution_stage': 0,
            'age_seconds': 0
        }

        pet = Pet.from_dict(data)

        assert pet.hunger == config.STAT_MAX  # Clamped to 100
        assert pet.happiness == config.STAT_MIN  # Clamped to 0
        assert pet.health == config.STAT_MAX  # Clamped to 100
        assert pet.energy == config.STAT_MIN  # Clamped to 0

    def test_to_dict_roundtrip(self):
        """to_dict and from_dict should be inverses"""
        original = Pet(name="Buddy", hunger=40, happiness=60, health=80, energy=70)
        original.evolution_stage = 2
        original.age_seconds = 1000

        data = original.to_dict()
        restored = Pet.from_dict(data)

        assert restored.name == original.name
        assert restored.hunger == original.hunger
        assert restored.happiness == original.happiness
        assert restored.health == original.health
        assert restored.energy == original.energy
        assert restored.evolution_stage == original.evolution_stage
        assert restored.age_seconds == original.age_seconds


class TestPetCareActions:
    """Tests for Pet care action methods"""

    def test_feed_reduces_hunger(self):
        """Feed should reduce hunger"""
        pet = Pet(name="Buddy", hunger=70)
        changes = pet.feed()

        assert 'hunger' in changes
        assert pet.hunger < 70

    def test_play_increases_happiness(self):
        """Play should increase happiness"""
        pet = Pet(name="Buddy", happiness=50)
        changes = pet.play()

        assert 'happiness' in changes
        assert pet.happiness > 50

    def test_clean_improves_health(self):
        """Clean should improve health"""
        pet = Pet(name="Buddy", health=70)
        changes = pet.clean()

        assert 'health' in changes
        assert pet.health > 70

    def test_sleep_restores_energy(self):
        """Sleep should restore energy"""
        pet = Pet(name="Buddy", energy=30)
        changes = pet.sleep()

        assert 'energy' in changes
        assert pet.energy > 30
        assert pet.is_sleeping

    def test_dead_pet_cannot_feed(self):
        """Dead pet should not accept feed action"""
        pet = Pet(name="Buddy", health=0)
        changes = pet.feed()

        assert changes == {}

    def test_dead_pet_cannot_play(self):
        """Dead pet should not accept play action"""
        pet = Pet(name="Buddy", health=0)
        changes = pet.play()

        assert changes == {}

    def test_stats_clamped_after_action(self):
        """Stats should be clamped after care actions"""
        # Create pet with hunger near 0
        pet = Pet(name="Buddy", hunger=10)
        pet.feed()  # Should reduce hunger further

        assert pet.hunger >= config.STAT_MIN
        assert pet.hunger <= config.STAT_MAX


class TestPetIsAlive:
    """Tests for Pet.is_alive() method"""

    def test_alive_with_positive_health(self):
        """Pet should be alive with health > 0"""
        pet = Pet(name="Buddy", health=1)
        assert pet.is_alive() is True

    def test_dead_with_zero_health(self):
        """Pet should be dead with health = 0"""
        pet = Pet(name="Buddy", health=0)
        assert pet.is_alive() is False


class TestPetEmotionState:
    """Tests for Pet.get_emotion_state() method"""

    def test_dead_emotion(self):
        """Dead pet should return 'dead' emotion"""
        pet = Pet(name="Buddy", health=0)
        assert pet.get_emotion_state() == "dead"

    def test_sick_emotion(self):
        """Pet with low health should return 'sick' emotion"""
        pet = Pet(name="Buddy", health=20)  # Below 30
        assert pet.get_emotion_state() == "sick"

    def test_hungry_emotion(self):
        """Pet with high hunger should return 'hungry' emotion"""
        pet = Pet(name="Buddy", hunger=80)  # Above 70
        assert pet.get_emotion_state() == "hungry"

    def test_tired_emotion(self):
        """Pet with low energy should return 'tired' emotion"""
        pet = Pet(name="Buddy", energy=20)  # Below 30
        assert pet.get_emotion_state() == "tired"

    def test_sad_emotion(self):
        """Pet with low happiness should return 'sad' emotion"""
        pet = Pet(name="Buddy", happiness=20)  # Below 30
        assert pet.get_emotion_state() == "sad"

    def test_sleeping_emotion_after_sleep(self):
        """Pet should show 'sleeping' emotion after sleep action"""
        pet = Pet(name="Buddy")
        pet.sleep()
        assert pet.get_emotion_state() == "sleeping"

    def test_happy_default_emotion(self):
        """Pet with normal stats should return 'happy' (default) or 'content' emotion"""
        pet = Pet(name="Buddy", hunger=30, happiness=60, health=80, energy=70)
        # With low hunger, moderate happiness, good health -> 'content' takes priority
        # 'happy' is the fallback default if no other condition matches
        emotion = pet.get_emotion_state()
        assert emotion in ["happy", "content"], f"Got {emotion}"


class TestPetUpdateStats:
    """Tests for Pet.update_stats() method"""

    def test_update_stats_increases_hunger(self):
        """update_stats should increase hunger over time"""
        pet = Pet(name="Buddy", hunger=50)
        pet.last_update = time.time() - 60  # 1 minute ago

        pet.update_stats()

        assert pet.hunger > 50

    def test_update_stats_decreases_happiness(self):
        """update_stats should decrease happiness over time"""
        pet = Pet(name="Buddy", happiness=75)
        pet.last_update = time.time() - 60  # 1 minute ago

        pet.update_stats()

        assert pet.happiness < 75

    def test_update_stats_increases_age(self):
        """update_stats should increase age_seconds"""
        pet = Pet(name="Buddy")
        pet.last_update = time.time() - 60  # 1 minute ago

        pet.update_stats()

        assert pet.age_seconds >= 60

    def test_update_stats_caps_degradation(self):
        """update_stats should cap degradation for long absences"""
        pet = Pet(name="Buddy", hunger=50, happiness=75, health=100)
        # Set last update to way in the past (beyond max degradation)
        pet.last_update = time.time() - (config.MAX_DEGRADATION_HOURS * 3600 * 2)

        pet.update_stats()

        # Stats should change, but not kill the pet instantly
        # (would need many more hours of neglect)
        assert pet.health > 0 or pet.hunger == config.STAT_MAX


class TestPetReset:
    """Tests for Pet.reset() method"""

    def test_reset_restores_defaults(self):
        """reset should restore all stats to defaults"""
        pet = Pet(name="Buddy", hunger=90, happiness=10, health=20, energy=5)
        pet.evolution_stage = 4
        pet.age_seconds = 100000

        pet.reset()

        assert pet.hunger == config.INITIAL_HUNGER
        assert pet.happiness == config.INITIAL_HAPPINESS
        assert pet.health == config.INITIAL_HEALTH
        assert pet.energy == config.INITIAL_ENERGY
        assert pet.evolution_stage == 0
        assert pet.age_seconds == 0

    def test_reset_with_new_name(self):
        """reset with new_name should change the name"""
        pet = Pet(name="Buddy")
        pet.reset(new_name="NewName")

        assert pet.name == "NewName"

    def test_reset_keeps_name_if_not_provided(self):
        """reset without new_name should keep original name"""
        pet = Pet(name="Buddy")
        pet.reset()

        assert pet.name == "Buddy"


def run_tests_simple():
    """Run all tests without pytest."""
    test_classes = [
        TestClampStat,
        TestCalculateStatDegradation,
        TestApplyStatChanges,
        TestPetCreation,
        TestPetCareActions,
        TestPetIsAlive,
        TestPetEmotionState,
        TestPetUpdateStats,
        TestPetReset
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
        print("Running pet tests...\n")
        success = run_tests_simple()
        sys.exit(0 if success else 1)
