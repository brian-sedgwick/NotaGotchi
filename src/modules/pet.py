"""
Not-A-Gotchi Pet Module

Core pet logic including stats, behavior, growth, and care actions.
"""

import time
from typing import Optional, Dict, Any
from . import config


class Pet:
    """Represents the virtual pet with all its states and behaviors"""

    def __init__(self, name: str, pet_id: int = None, hunger: int = None,
                 happiness: int = None, health: int = None, birth_time: float = None,
                 last_update: float = None, evolution_stage: int = 0,
                 age_seconds: int = 0):
        """
        Initialize a pet instance

        Args:
            name: Pet's name
            pet_id: Database ID (None for new pets)
            hunger: Current hunger level (0-100)
            happiness: Current happiness level (0-100)
            health: Current health level (0-100)
            birth_time: Timestamp of pet creation
            last_update: Timestamp of last stat update
            evolution_stage: Current evolution stage (0-4)
            age_seconds: Total age in seconds
        """
        self.id = pet_id
        self.name = name
        self.hunger = hunger if hunger is not None else config.INITIAL_HUNGER
        self.happiness = happiness if happiness is not None else config.INITIAL_HAPPINESS
        self.health = health if health is not None else config.INITIAL_HEALTH
        self.birth_time = birth_time if birth_time is not None else time.time()
        self.last_update = last_update if last_update is not None else time.time()
        self.evolution_stage = evolution_stage
        self.age_seconds = age_seconds

        # Track if pet just evolved (for display purposes)
        self.just_evolved = False
        self.evolution_display_timer = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pet':
        """Create Pet instance from dictionary (e.g., database row)"""
        return cls(
            name=data['name'],
            pet_id=data.get('id'),
            hunger=data['hunger'],
            happiness=data['happiness'],
            health=data['health'],
            birth_time=data['birth_time'],
            last_update=data['last_update'],
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
            'birth_time': self.birth_time,
            'last_update': self.last_update,
            'evolution_stage': self.evolution_stage,
            'age_seconds': self.age_seconds
        }

    def update_stats(self, current_time: float = None) -> Dict[str, float]:
        """
        Update pet stats based on time elapsed since last update

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

        # Track changes
        changes = {
            'hunger': 0,
            'happiness': 0,
            'health': 0
        }

        # Update hunger (increases over time)
        hunger_change = config.HUNGER_INCREASE_RATE * time_elapsed_minutes
        self.hunger = min(config.STAT_MAX, self.hunger + hunger_change)
        changes['hunger'] = hunger_change

        # Update happiness (decreases over time)
        happiness_change = config.HAPPINESS_DECREASE_RATE * time_elapsed_minutes
        self.happiness = max(config.STAT_MIN, self.happiness - happiness_change)
        changes['happiness'] = -happiness_change

        # Update health based on conditions
        health_change = 0

        # Health degrades if hungry or unhappy
        if self.hunger > config.HEALTH_DEGRADE_THRESHOLD_HUNGER or \
           self.happiness < config.HEALTH_DEGRADE_THRESHOLD_HAPPINESS:
            health_change -= config.HEALTH_DEGRADE_RATE * time_elapsed_minutes

        # Health regenerates if well-fed and happy
        elif self.hunger < config.HEALTH_REGEN_THRESHOLD_HUNGER and \
             self.happiness > config.HEALTH_REGEN_THRESHOLD_HAPPINESS:
            health_change += config.HEALTH_REGEN_RATE * time_elapsed_minutes

        self.health = max(config.STAT_MIN, min(config.STAT_MAX, self.health + health_change))
        changes['health'] = health_change

        # Update age
        self.age_seconds += int(time_elapsed_seconds)

        # Check for evolution
        old_stage = self.evolution_stage
        self._check_evolution()
        if old_stage != self.evolution_stage:
            self.just_evolved = True
            self.evolution_display_timer = config.EVOLUTION_DISPLAY_DURATION

        # Update last update time
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

    def feed(self) -> Dict[str, int]:
        """
        Feed the pet

        Returns:
            Dictionary of stat changes
        """
        changes = config.CARE_ACTIONS['feed'].copy()

        self.hunger = max(config.STAT_MIN, min(config.STAT_MAX, self.hunger + changes['hunger']))
        self.happiness = max(config.STAT_MIN, min(config.STAT_MAX, self.happiness + changes['happiness']))
        self.health = max(config.STAT_MIN, min(config.STAT_MAX, self.health + changes['health']))

        print(f"{self.name} was fed!")
        return changes

    def play(self) -> Dict[str, int]:
        """
        Play with the pet

        Returns:
            Dictionary of stat changes
        """
        changes = config.CARE_ACTIONS['play'].copy()

        self.hunger = max(config.STAT_MIN, min(config.STAT_MAX, self.hunger + changes['hunger']))
        self.happiness = max(config.STAT_MIN, min(config.STAT_MAX, self.happiness + changes['happiness']))
        self.health = max(config.STAT_MIN, min(config.STAT_MAX, self.health + changes['health']))

        print(f"{self.name} enjoyed playing!")
        return changes

    def clean(self) -> Dict[str, int]:
        """
        Clean the pet

        Returns:
            Dictionary of stat changes
        """
        changes = config.CARE_ACTIONS['clean'].copy()

        self.hunger = max(config.STAT_MIN, min(config.STAT_MAX, self.hunger + changes['hunger']))
        self.happiness = max(config.STAT_MIN, min(config.STAT_MAX, self.happiness + changes['happiness']))
        self.health = max(config.STAT_MIN, min(config.STAT_MAX, self.health + changes['health']))

        print(f"{self.name} is now clean!")
        return changes

    def sleep(self) -> Dict[str, int]:
        """
        Put the pet to sleep

        Returns:
            Dictionary of stat changes
        """
        changes = config.CARE_ACTIONS['sleep'].copy()

        self.hunger = max(config.STAT_MIN, min(config.STAT_MAX, self.hunger + changes['hunger']))
        self.happiness = max(config.STAT_MIN, min(config.STAT_MAX, self.happiness + changes['happiness']))
        self.health = max(config.STAT_MIN, min(config.STAT_MAX, self.health + changes['health']))

        print(f"{self.name} is resting...")
        return changes

    def get_emotion_state(self) -> str:
        """
        Determine pet's current emotional state based on stats

        Returns:
            Emotion name (e.g., "happy", "sad", "hungry", etc.)
        """
        # Evaluate emotion rules in order
        for rule in config.EMOTION_RULES:
            if rule['condition'](self.hunger, self.happiness, self.health):
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

    def is_alive(self) -> bool:
        """Check if pet is still alive"""
        return self.health > 0

    def get_stats_dict(self) -> Dict[str, int]:
        """Get current stats as dictionary"""
        return {
            'hunger': int(self.hunger),
            'happiness': int(self.happiness),
            'health': int(self.health)
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
        self.birth_time = time.time()
        self.last_update = time.time()
        self.evolution_stage = 0
        self.age_seconds = 0
        self.just_evolved = False
        self.evolution_display_timer = 0

        print(f"Pet reset: {self.name}")

    def __repr__(self) -> str:
        """String representation of pet"""
        return (f"Pet(name={self.name}, hunger={self.hunger:.1f}, "
                f"happiness={self.happiness:.1f}, health={self.health:.1f}, "
                f"stage={self.evolution_stage}, age={self.get_age_display()})")
