"""
Not-A-Gotchi Pet Module

Core pet logic including stats, behavior, growth, and care actions.
"""

import time
from typing import Optional, Dict, Any, Tuple
from . import config


def _clamp_stat(value: float) -> float:
    """
    Clamp a stat value to valid bounds [STAT_MIN, STAT_MAX].

    This is a pure function with no side effects.

    Args:
        value: The stat value to clamp

    Returns:
        The value clamped to [0, 100]
    """
    return max(config.STAT_MIN, min(config.STAT_MAX, value))


def calculate_stat_degradation(
    hunger: float,
    happiness: float,
    health: float,
    energy: float,
    time_elapsed_minutes: float
) -> Dict[str, float]:
    """
    Calculate stat changes based on time elapsed.

    This is a PURE FUNCTION with no side effects - it only calculates
    and returns the changes, it does not modify any state.

    Args:
        hunger: Current hunger level (0-100)
        happiness: Current happiness level (0-100)
        health: Current health level (0-100)
        energy: Current energy level (0-100)
        time_elapsed_minutes: Time elapsed in minutes

    Returns:
        Dictionary of stat changes (deltas, not final values)
    """
    changes = {
        'hunger': 0.0,
        'happiness': 0.0,
        'health': 0.0,
        'energy': 0.0
    }

    # Hunger increases over time
    changes['hunger'] = config.HUNGER_INCREASE_RATE * time_elapsed_minutes

    # Happiness decreases over time
    changes['happiness'] = -config.HAPPINESS_DECREASE_RATE * time_elapsed_minutes

    # Health changes based on conditions
    # Calculate what hunger/happiness will be after applying their changes
    projected_hunger = hunger + changes['hunger']
    projected_happiness = happiness + changes['happiness']

    if projected_hunger > config.HEALTH_DEGRADE_THRESHOLD_HUNGER or \
       projected_happiness < config.HEALTH_DEGRADE_THRESHOLD_HAPPINESS:
        changes['health'] = -config.HEALTH_DEGRADE_RATE * time_elapsed_minutes
    elif projected_hunger < config.HEALTH_REGEN_THRESHOLD_HUNGER and \
         projected_happiness > config.HEALTH_REGEN_THRESHOLD_HAPPINESS:
        changes['health'] = config.HEALTH_REGEN_RATE * time_elapsed_minutes

    # Energy decreases over time, faster when hungry
    energy_change = -config.ENERGY_DECREASE_RATE * time_elapsed_minutes
    fullness = 100 - projected_hunger
    if fullness < config.ENERGY_LOW_FULLNESS_THRESHOLD:
        energy_change *= config.ENERGY_LOW_FULLNESS_MULTIPLIER
    changes['energy'] = energy_change

    return changes


def apply_stat_changes(
    hunger: float,
    happiness: float,
    health: float,
    energy: float,
    changes: Dict[str, float]
) -> Tuple[float, float, float, float]:
    """
    Apply stat changes and clamp to valid bounds.

    This is a PURE FUNCTION with no side effects.

    Args:
        hunger, happiness, health, energy: Current stat values
        changes: Dictionary of changes to apply

    Returns:
        Tuple of (new_hunger, new_happiness, new_health, new_energy)
    """
    new_hunger = _clamp_stat(hunger + changes.get('hunger', 0))
    new_happiness = _clamp_stat(happiness + changes.get('happiness', 0))
    new_health = _clamp_stat(health + changes.get('health', 0))
    new_energy = _clamp_stat(energy + changes.get('energy', 0))

    return new_hunger, new_happiness, new_health, new_energy


class Pet:
    """Represents the virtual pet with all its states and behaviors"""

    def __init__(self, name: str, pet_id: int = None, hunger: int = None,
                 happiness: int = None, health: int = None, energy: int = None,
                 birth_time: float = None, last_update: float = None,
                 last_sleep_time: float = None, evolution_stage: int = 0,
                 age_seconds: int = 0):
        """
        Initialize a pet instance

        Args:
            name: Pet's name
            pet_id: Database ID (None for new pets)
            hunger: Current hunger level (0-100)
            happiness: Current happiness level (0-100)
            health: Current health level (0-100)
            energy: Current energy level (0-100)
            birth_time: Timestamp of pet creation
            last_update: Timestamp of last stat update
            last_sleep_time: Timestamp of last sleep action
            evolution_stage: Current evolution stage (0-4)
            age_seconds: Total age in seconds
        """
        self.id = pet_id
        self.name = name
        self.hunger = hunger if hunger is not None else config.INITIAL_HUNGER
        self.happiness = happiness if happiness is not None else config.INITIAL_HAPPINESS
        self.health = health if health is not None else config.INITIAL_HEALTH
        self.energy = energy if energy is not None else config.INITIAL_ENERGY
        self.birth_time = birth_time if birth_time is not None else time.time()
        self.last_update = last_update if last_update is not None else time.time()
        self.last_sleep_time = last_sleep_time if last_sleep_time is not None else time.time()
        self.evolution_stage = evolution_stage
        self.age_seconds = age_seconds

        # Track if pet just evolved (for display purposes)
        self.just_evolved = False
        self.evolution_display_timer = 0

        # Track if pet is sleeping (for emotion display purposes)
        self.is_sleeping = False
        self.sleep_display_timer = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pet':
        """
        Create Pet instance from dictionary (e.g., database row).

        Validates and clamps all stat values to valid bounds [0, 100]
        to handle potentially corrupted database values.
        """
        # Validate and clamp stat values on load
        hunger = _clamp_stat(data.get('hunger', config.INITIAL_HUNGER))
        happiness = _clamp_stat(data.get('happiness', config.INITIAL_HAPPINESS))
        health = _clamp_stat(data.get('health', config.INITIAL_HEALTH))
        energy = _clamp_stat(data.get('energy', config.INITIAL_ENERGY))

        return cls(
            name=data['name'],
            pet_id=data.get('id'),
            hunger=hunger,
            happiness=happiness,
            health=health,
            energy=energy,
            birth_time=data['birth_time'],
            last_update=data['last_update'],
            last_sleep_time=data.get('last_sleep_time', data['birth_time']),  # Default for old saves
            evolution_stage=data['evolution_stage'],
            age_seconds=data['age_seconds']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert pet to dictionary for database storage"""
        return {
            'id': self.id,
            'name': self.name,
            'hunger': self.hunger,
            'happiness': self.happiness,
            'health': self.health,
            'energy': self.energy,
            'birth_time': self.birth_time,
            'last_update': self.last_update,
            'last_sleep_time': self.last_sleep_time,
            'evolution_stage': self.evolution_stage,
            'age_seconds': self.age_seconds
        }

    def update_stats(self, current_time: float = None) -> Dict[str, float]:
        """
        Update pet stats based on time elapsed since last update.

        Uses pure functions for calculation, then applies side effects
        (state mutation, evolution checks).

        Returns:
            Dictionary of stat changes
        """
        if current_time is None:
            current_time = time.time()

        # Calculate time elapsed (in minutes)
        time_elapsed_seconds = current_time - self.last_update
        time_elapsed_minutes = time_elapsed_seconds / 60.0

        # Cap the elapsed time to prevent instant death after long absences
        max_elapsed_seconds = config.MAX_DEGRADATION_HOURS * 3600
        if time_elapsed_seconds > max_elapsed_seconds:
            time_elapsed_minutes = max_elapsed_seconds / 60.0
            print(f"Capped degradation to {config.MAX_DEGRADATION_HOURS} hours")

        # PURE: Calculate stat changes using pure function
        changes = calculate_stat_degradation(
            self.hunger, self.happiness, self.health, self.energy,
            time_elapsed_minutes
        )

        # PURE: Apply changes using pure function
        new_hunger, new_happiness, new_health, new_energy = apply_stat_changes(
            self.hunger, self.happiness, self.health, self.energy,
            changes
        )

        # SIDE EFFECT: Apply the calculated values to state
        self.hunger = new_hunger
        self.happiness = new_happiness
        self.health = new_health
        self.energy = new_energy

        # SIDE EFFECT: Update age
        self.age_seconds += int(time_elapsed_seconds)

        # SIDE EFFECT: Check for evolution
        old_stage = self.evolution_stage
        self._check_evolution()
        if old_stage != self.evolution_stage:
            self.just_evolved = True
            self.evolution_display_timer = config.EVOLUTION_DISPLAY_DURATION

        # SIDE EFFECT: Update last update time
        self.last_update = current_time

        return changes

    def _check_evolution(self):
        """Check if pet should evolve to next stage"""
        for stage in range(4, -1, -1):  # Check from highest to lowest
            if self.age_seconds >= config.STAGE_THRESHOLDS[stage]:
                if self.evolution_stage != stage:
                    print(f"Pet evolved to stage {stage}!")
                self.evolution_stage = stage
                return

    def _apply_care_action(self, action_name: str) -> Dict[str, int]:
        """
        Apply a care action's stat changes.

        This is an internal helper that eliminates code duplication
        across feed(), play(), clean(), and sleep() methods.

        Args:
            action_name: Name of the action (must be in config.CARE_ACTIONS)

        Returns:
            Dictionary of stat changes applied
        """
        changes = config.CARE_ACTIONS[action_name].copy()

        # Apply changes using the pure function
        self.hunger, self.happiness, self.health, self.energy = apply_stat_changes(
            self.hunger, self.happiness, self.health, self.energy,
            changes
        )

        return changes

    def feed(self) -> Dict[str, int]:
        """
        Feed the pet.

        Returns:
            Dictionary of stat changes (empty dict if dead)
        """
        if not self.is_alive():
            print(f"{self.name} is dead and cannot be fed.")
            return {}

        changes = self._apply_care_action('feed')
        print(f"{self.name} was fed!")
        return changes

    def play(self) -> Dict[str, int]:
        """
        Play with the pet.

        Returns:
            Dictionary of stat changes (empty dict if dead)
        """
        if not self.is_alive():
            print(f"{self.name} is dead and cannot play.")
            return {}

        changes = self._apply_care_action('play')
        print(f"{self.name} enjoyed playing!")
        return changes

    def clean(self) -> Dict[str, int]:
        """
        Clean the pet.

        Returns:
            Dictionary of stat changes (empty dict if dead)
        """
        if not self.is_alive():
            print(f"{self.name} is dead and cannot be cleaned.")
            return {}

        changes = self._apply_care_action('clean')
        print(f"{self.name} is now clean!")
        return changes

    def sleep(self) -> Dict[str, int]:
        """
        Put the pet to sleep.

        Returns:
            Dictionary of stat changes (empty dict if dead)
        """
        if not self.is_alive():
            print(f"{self.name} is dead and cannot sleep.")
            return {}

        changes = self._apply_care_action('sleep')
        self.last_sleep_time = time.time()

        # Set sleeping state for temporary display
        self.is_sleeping = True
        self.sleep_display_timer = config.SLEEP_DISPLAY_DURATION

        print(f"{self.name} is resting...")
        return changes

    def get_emotion_state(self) -> str:
        """
        Determine pet's current emotional state based on stats

        Returns:
            Emotion name (e.g., "happy", "sad", "hungry", etc.)
        """
        # Check if sleeping state should be displayed (temporary after sleep action)
        if self.is_sleeping and self.sleep_display_timer > 0:
            return "sleeping"

        # Evaluate emotion rules in order
        for rule in config.EMOTION_RULES:
            if rule['condition'](self.hunger, self.happiness, self.health, self.energy):
                return rule['emotion']

        # Default fallback (should never reach here due to catch-all rule)
        return "happy"

    def get_stage_sprite(self) -> str:
        """
        Get the sprite filename for current evolution stage

        Returns:
            Sprite filename (e.g., "egg.bmp", "adult.bmp")
        """
        return config.STAGE_SPRITES.get(self.evolution_stage, "egg.bmp")

    def get_current_sprite(self) -> str:
        """
        Get the appropriate sprite for current state

        Priority:
        1. Dead sprite if health is 0
        2. Stage sprite if just evolved
        3. Emotion sprite based on current stats

        Returns:
            Sprite filename
        """
        # Dead overrides everything
        if self.health <= 0:
            return config.EMOTION_SPRITES['dead']

        # Show evolution sprite for a few seconds after evolving
        if self.just_evolved and self.evolution_display_timer > 0:
            return self.get_stage_sprite()

        # Otherwise show emotion sprite
        emotion = self.get_emotion_state()
        return config.EMOTION_SPRITES.get(emotion, config.EMOTION_SPRITES['happy'])

    def tick_evolution_timer(self, delta_time: float):
        """
        Update evolution display timer

        Args:
            delta_time: Time elapsed in seconds
        """
        if self.just_evolved and self.evolution_display_timer > 0:
            self.evolution_display_timer -= delta_time
            if self.evolution_display_timer <= 0:
                self.just_evolved = False
                self.evolution_display_timer = 0

    def tick_sleep_timer(self, delta_time: float):
        """
        Update sleeping display timer

        Args:
            delta_time: Time elapsed in seconds
        """
        if self.is_sleeping and self.sleep_display_timer > 0:
            self.sleep_display_timer -= delta_time
            if self.sleep_display_timer <= 0:
                self.is_sleeping = False
                self.sleep_display_timer = 0

    def is_alive(self) -> bool:
        """Check if pet is still alive"""
        return self.health > 0

    def get_stats_dict(self) -> Dict[str, int]:
        """Get current stats as dictionary"""
        return {
            'hunger': int(self.hunger),
            'happiness': int(self.happiness),
            'health': int(self.health),
            'energy': int(self.energy)
        }

    def get_age_display(self) -> str:
        """Get human-readable age string"""
        if self.age_seconds < 60:
            return f"{self.age_seconds}s"
        elif self.age_seconds < 3600:
            minutes = self.age_seconds // 60
            return f"{minutes}m"
        elif self.age_seconds < 86400:
            hours = self.age_seconds // 3600
            return f"{hours}h"
        else:
            days = self.age_seconds // 86400
            return f"{days}d"

    def reset(self, new_name: str = None):
        """
        Reset pet to egg stage

        Args:
            new_name: Optional new name (keeps current name if None)
        """
        if new_name:
            self.name = new_name

        self.hunger = config.INITIAL_HUNGER
        self.happiness = config.INITIAL_HAPPINESS
        self.health = config.INITIAL_HEALTH
        self.energy = config.INITIAL_ENERGY
        self.birth_time = time.time()
        self.last_update = time.time()
        self.last_sleep_time = time.time()
        self.evolution_stage = 0
        self.age_seconds = 0
        self.just_evolved = False
        self.evolution_display_timer = 0
        self.is_sleeping = False
        self.sleep_display_timer = 0

        print(f"Pet reset: {self.name}")

    def __repr__(self) -> str:
        """String representation of pet"""
        return (f"Pet(name={self.name}, hunger={self.hunger:.1f}, "
                f"happiness={self.happiness:.1f}, health={self.health:.1f}, "
                f"stage={self.evolution_stage}, age={self.get_age_display()})")
