"""
Not-A-Gotchi Input Handler Module

Handles rotary encoder input (rotation and button press).
"""

import time
from typing import Callable, Optional
from queue import Queue
from . import config

# Try to import GPIO libraries
try:
    from gpiozero import RotaryEncoder, Button
    GPIO_AVAILABLE = True
except ImportError:
    print("Warning: gpiozero not available. Input will run in simulation mode.")
    GPIO_AVAILABLE = False


class InputEvent:
    """Represents an input event"""

    TYPE_ROTATE_CW = "rotate_cw"
    TYPE_ROTATE_CCW = "rotate_ccw"
    TYPE_BUTTON_PRESS = "button_press"
    TYPE_BUTTON_LONG_PRESS = "button_long_press"

    def __init__(self, event_type: str, timestamp: float = None):
        """
        Create input event

        Args:
            event_type: Type of event
            timestamp: Event timestamp (defaults to current time)
        """
        self.type = event_type
        self.timestamp = timestamp if timestamp is not None else time.time()

    def __repr__(self):
        return f"InputEvent(type={self.type}, time={self.timestamp:.2f})"


class InputHandler:
    """Handles rotary encoder and button input"""

    def __init__(self, simulation_mode: bool = False):
        """
        Initialize input handler

        Args:
            simulation_mode: If True, don't initialize actual hardware
        """
        self.simulation_mode = simulation_mode or not GPIO_AVAILABLE
        self.event_queue = Queue()

        # Hardware components
        self.encoder = None
        self.button = None

        # Button state tracking
        self.button_pressed_time = None
        self.button_long_press_fired = False

        if not self.simulation_mode:
            self._initialize_hardware()

    def _initialize_hardware(self):
        """Initialize GPIO hardware for encoder and button"""
        try:
            print("Initializing rotary encoder input...")

            # Initialize rotary encoder
            self.encoder = RotaryEncoder(
                config.ENCODER_CLK_PIN,
                config.ENCODER_DT_PIN,
                bounce_time=config.BUTTON_DEBOUNCE_TIME
            )

            # Initialize button
            self.button = Button(
                config.ENCODER_SW_PIN,
                bounce_time=config.BUTTON_DEBOUNCE_TIME
            )

            # Set up callbacks
            self.encoder.when_rotated_clockwise = self._on_rotate_cw
            self.encoder.when_rotated_counter_clockwise = self._on_rotate_ccw
            self.button.when_pressed = self._on_button_pressed
            self.button.when_released = self._on_button_released

            print("Input hardware initialized successfully")

        except Exception as e:
            print(f"Error initializing input hardware: {e}")
            print("Falling back to simulation mode")
            self.simulation_mode = True
            self.encoder = None
            self.button = None

    def _on_rotate_cw(self):
        """Callback for clockwise rotation"""
        event = InputEvent(InputEvent.TYPE_ROTATE_CW)
        self.event_queue.put(event)
        print("→ Rotate CW")

    def _on_rotate_ccw(self):
        """Callback for counter-clockwise rotation"""
        event = InputEvent(InputEvent.TYPE_ROTATE_CCW)
        self.event_queue.put(event)
        print("← Rotate CCW")

    def _on_button_pressed(self):
        """Callback for button press (button down)"""
        self.button_pressed_time = time.time()
        self.button_long_press_fired = False
        print("⬇ Button pressed")

    def _on_button_released(self):
        """Callback for button release (button up)"""
        if self.button_pressed_time is None:
            return

        press_duration = time.time() - self.button_pressed_time

        # If long press already fired, don't fire short press
        if not self.button_long_press_fired:
            if press_duration >= config.LONG_PRESS_DURATION:
                event = InputEvent(InputEvent.TYPE_BUTTON_LONG_PRESS)
                print("⬆ Button released (LONG)")
            else:
                event = InputEvent(InputEvent.TYPE_BUTTON_PRESS)
                print("⬆ Button released (short)")

            self.event_queue.put(event)

        self.button_pressed_time = None
        self.button_long_press_fired = False

    def check_long_press(self):
        """Check if button is being held for long press"""
        if self.button_pressed_time is not None and not self.button_long_press_fired:
            press_duration = time.time() - self.button_pressed_time

            if press_duration >= config.LONG_PRESS_DURATION:
                # Fire long press event
                event = InputEvent(InputEvent.TYPE_BUTTON_LONG_PRESS)
                self.event_queue.put(event)
                self.button_long_press_fired = True
                print("⏱ Long press detected")

    def get_event(self) -> Optional[InputEvent]:
        """
        Get next input event from queue

        Returns:
            InputEvent or None if queue is empty
        """
        if not self.event_queue.empty():
            return self.event_queue.get()
        return None

    def has_events(self) -> bool:
        """Check if there are pending events"""
        return not self.event_queue.empty()

    def simulate_event(self, event_type: str):
        """
        Simulate an input event (for testing/simulation mode)

        Args:
            event_type: Type of event to simulate
        """
        event = InputEvent(event_type)
        self.event_queue.put(event)
        print(f"Simulated: {event_type}")

    def clear_events(self):
        """Clear all pending events from queue"""
        while not self.event_queue.empty():
            self.event_queue.get()

    def close(self):
        """Clean up input resources"""
        if not self.simulation_mode:
            if self.encoder:
                self.encoder.close()
            if self.button:
                self.button.close()
            print("Input handler closed")
