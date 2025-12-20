"""
Not-A-Gotchi Screen State Machine

Implements a formal state machine for screen navigation with plugin support.
Screens can be registered dynamically for extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from . import config


class TransitionResult(Enum):
    """Result of a state transition attempt."""
    SUCCESS = auto()
    BLOCKED = auto()          # Transition not allowed
    INVALID_STATE = auto()    # Target state doesn't exist
    GUARD_FAILED = auto()     # Guard condition returned False


@dataclass
class ScreenState:
    """
    Represents a screen state in the state machine.

    Attributes:
        name: Unique identifier for the state
        allowed_transitions: Set of state names this state can transition to
        on_enter: Optional callback when entering this state
        on_exit: Optional callback when exiting this state
        data: Optional arbitrary data associated with this state
    """
    name: str
    allowed_transitions: Set[str] = field(default_factory=set)
    on_enter: Optional[Callable[['ScreenStateMachine', str], None]] = None
    on_exit: Optional[Callable[['ScreenStateMachine', str], None]] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def can_transition_to(self, target: str) -> bool:
        """Check if transition to target state is allowed."""
        # Empty set means all transitions allowed
        if not self.allowed_transitions:
            return True
        return target in self.allowed_transitions


@dataclass
class Transition:
    """
    Represents a transition between states.

    Attributes:
        from_state: Source state name
        to_state: Target state name
        guard: Optional condition that must be True for transition
        action: Optional action to perform during transition
    """
    from_state: str
    to_state: str
    guard: Optional[Callable[['ScreenStateMachine'], bool]] = None
    action: Optional[Callable[['ScreenStateMachine'], None]] = None


class ScreenStateMachine:
    """
    State machine for managing screen navigation.

    Features:
    - Registered states with enter/exit callbacks
    - Guarded transitions
    - History tracking for back navigation
    - Plugin-style screen registration
    """

    def __init__(self, initial_state: str = None):
        """
        Initialize the state machine.

        Args:
            initial_state: The starting state (optional, can set later)
        """
        self._states: Dict[str, ScreenState] = {}
        self._transitions: List[Transition] = []
        self._current_state: Optional[str] = None
        self._history: List[str] = []
        self._history_limit = 10

        # State-specific data storage
        self._state_data: Dict[str, Dict[str, Any]] = {}

        # Global state change callback
        self._on_state_change: Optional[Callable[[str, str], None]] = None

        if initial_state:
            self._current_state = initial_state

    # =========================================================================
    # STATE REGISTRATION
    # =========================================================================

    def register_state(
        self,
        name: str,
        allowed_transitions: Set[str] = None,
        on_enter: Callable = None,
        on_exit: Callable = None,
        data: Dict[str, Any] = None
    ) -> 'ScreenStateMachine':
        """
        Register a new state.

        Args:
            name: Unique state identifier
            allowed_transitions: Set of allowed target states (None = all allowed)
            on_enter: Callback when entering state
            on_exit: Callback when exiting state
            data: Initial data for this state

        Returns:
            Self for method chaining
        """
        self._states[name] = ScreenState(
            name=name,
            allowed_transitions=allowed_transitions or set(),
            on_enter=on_enter,
            on_exit=on_exit,
            data=data or {}
        )
        self._state_data[name] = data.copy() if data else {}
        return self

    def register_transition(
        self,
        from_state: str,
        to_state: str,
        guard: Callable = None,
        action: Callable = None
    ) -> 'ScreenStateMachine':
        """
        Register a guarded transition.

        Args:
            from_state: Source state
            to_state: Target state
            guard: Condition that must be True
            action: Action to perform during transition

        Returns:
            Self for method chaining
        """
        self._transitions.append(Transition(
            from_state=from_state,
            to_state=to_state,
            guard=guard,
            action=action
        ))
        return self

    def set_on_state_change(self, callback: Callable[[str, str], None]) -> None:
        """
        Set global state change callback.

        Args:
            callback: Function(old_state, new_state) called on every transition
        """
        self._on_state_change = callback

    # =========================================================================
    # STATE TRANSITIONS
    # =========================================================================

    def transition_to(self, target_state: str, **kwargs) -> TransitionResult:
        """
        Attempt to transition to a new state.

        Args:
            target_state: The state to transition to
            **kwargs: Data to pass to the new state

        Returns:
            TransitionResult indicating success or failure reason
        """
        # Validate target state exists
        if target_state not in self._states:
            print(f"⚠️  Invalid state: {target_state}")
            return TransitionResult.INVALID_STATE

        # Get current state object (may be None on first transition)
        current = self._states.get(self._current_state) if self._current_state else None

        # Check if transition is allowed
        if current and not current.can_transition_to(target_state):
            print(f"⚠️  Transition from {self._current_state} to {target_state} not allowed")
            return TransitionResult.BLOCKED

        # Check guard conditions for registered transitions
        for transition in self._transitions:
            if transition.from_state == self._current_state and \
               transition.to_state == target_state:
                if transition.guard and not transition.guard(self):
                    print(f"⚠️  Guard failed for {self._current_state} -> {target_state}")
                    return TransitionResult.GUARD_FAILED

        # Execute transition
        old_state = self._current_state

        # Exit current state
        if current and current.on_exit:
            current.on_exit(self, target_state)

        # Add to history (for back navigation)
        if old_state and old_state != target_state:
            self._history.append(old_state)
            if len(self._history) > self._history_limit:
                self._history.pop(0)

        # Execute transition actions
        for transition in self._transitions:
            if transition.from_state == old_state and transition.to_state == target_state:
                if transition.action:
                    transition.action(self)

        # Update current state
        self._current_state = target_state

        # Store any passed data
        if kwargs:
            self._state_data[target_state].update(kwargs)

        # Enter new state
        target = self._states[target_state]
        if target.on_enter:
            target.on_enter(self, old_state)

        # Global callback
        if self._on_state_change:
            self._on_state_change(old_state, target_state)

        return TransitionResult.SUCCESS

    def go_back(self) -> bool:
        """
        Go back to previous state.

        Returns:
            True if back navigation succeeded
        """
        if not self._history:
            return False

        previous_state = self._history.pop()
        result = self.transition_to(previous_state)
        return result == TransitionResult.SUCCESS

    def go_home(self) -> bool:
        """
        Go directly to home state.

        Returns:
            True if navigation succeeded
        """
        result = self.transition_to(config.ScreenState.HOME)
        # Clear history after going home (navigation is complete)
        self._history.clear()
        return result == TransitionResult.SUCCESS

    # =========================================================================
    # STATE QUERIES
    # =========================================================================

    @property
    def current_state(self) -> Optional[str]:
        """Get current state name."""
        return self._current_state

    def is_in_state(self, state: str) -> bool:
        """Check if currently in given state."""
        return self._current_state == state

    def get_state_data(self, state: str = None) -> Dict[str, Any]:
        """
        Get data for a state.

        Args:
            state: State name (defaults to current state)

        Returns:
            State data dictionary
        """
        state = state or self._current_state
        return self._state_data.get(state, {})

    def set_state_data(self, key: str, value: Any, state: str = None) -> None:
        """
        Set data for a state.

        Args:
            key: Data key
            value: Data value
            state: State name (defaults to current state)
        """
        state = state or self._current_state
        if state in self._state_data:
            self._state_data[state][key] = value

    def get_history(self) -> List[str]:
        """Get navigation history."""
        return self._history.copy()

    @property
    def registered_states(self) -> List[str]:
        """Get list of registered state names."""
        return list(self._states.keys())


# =============================================================================
# SCREEN PLUGIN INTERFACE
# =============================================================================

class ScreenPlugin(ABC):
    """
    Abstract base class for screen plugins.

    Implement this to create a self-contained screen that can be
    registered with the state machine.
    """

    @property
    @abstractmethod
    def state_name(self) -> str:
        """
        The state name for this screen.

        Returns:
            Unique identifier for this screen's state
        """
        pass

    @property
    def allowed_transitions(self) -> Set[str]:
        """
        States this screen can transition to.

        Override to restrict transitions. Empty set = all transitions allowed.

        Returns:
            Set of allowed target state names
        """
        return set()

    def on_enter(self, state_machine: ScreenStateMachine, from_state: str) -> None:
        """
        Called when entering this screen.

        Override to perform setup when screen becomes active.

        Args:
            state_machine: The state machine
            from_state: The previous state
        """
        pass

    def on_exit(self, state_machine: ScreenStateMachine, to_state: str) -> None:
        """
        Called when leaving this screen.

        Override to perform cleanup when screen becomes inactive.

        Args:
            state_machine: The state machine
            to_state: The next state
        """
        pass

    @abstractmethod
    def render(self, context: Dict[str, Any]) -> Any:
        """
        Render this screen.

        Args:
            context: Render context with display, pet, etc.

        Returns:
            PIL Image to display
        """
        pass

    def handle_input(self, event: Any, state_machine: ScreenStateMachine) -> bool:
        """
        Handle input event for this screen.

        Override to handle screen-specific input.

        Args:
            event: The input event
            state_machine: The state machine for navigation

        Returns:
            True if event was handled
        """
        return False

    def register(self, state_machine: ScreenStateMachine) -> None:
        """
        Register this plugin with a state machine.

        Args:
            state_machine: The state machine to register with
        """
        state_machine.register_state(
            name=self.state_name,
            allowed_transitions=self.allowed_transitions,
            on_enter=self.on_enter,
            on_exit=self.on_exit
        )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_default_state_machine() -> ScreenStateMachine:
    """
    Create a state machine with all default NotaGotchi screens registered.

    Returns:
        Configured ScreenStateMachine
    """
    sm = ScreenStateMachine(initial_state=config.ScreenState.HOME)

    # Register all standard screens from config.ScreenState
    standard_states = [
        config.ScreenState.HOME,
        config.ScreenState.MENU,
        config.ScreenState.NAME_ENTRY,
        config.ScreenState.SETTINGS,
        config.ScreenState.CONFIRM,
        config.ScreenState.CARE_MENU,
        config.ScreenState.FRIENDS_LIST,
        config.ScreenState.FIND_FRIENDS,
        config.ScreenState.FRIEND_REQUESTS,
        config.ScreenState.INBOX,
        config.ScreenState.MESSAGE_DETAIL,
        config.ScreenState.MESSAGE_TYPE_MENU,
        config.ScreenState.EMOJI_CATEGORY,
        config.ScreenState.EMOJI_SELECT,
        config.ScreenState.PRESET_CATEGORY,
        config.ScreenState.PRESET_SELECT,
        config.ScreenState.TEXT_COMPOSE,
    ]

    for state in standard_states:
        sm.register_state(state)

    return sm
