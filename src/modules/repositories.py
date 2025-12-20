"""
Not-A-Gotchi Repository Interfaces

Defines abstract interfaces for data access, enabling testability through
dependency injection of mock/in-memory implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import time
import uuid


# =============================================================================
# DATA TRANSFER OBJECTS
# =============================================================================

@dataclass
class PetData:
    """Data transfer object for pet state"""
    id: Optional[int] = None
    name: str = ""
    hunger: int = 50
    happiness: int = 75
    health: int = 100
    energy: int = 100
    birth_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    last_sleep_time: Optional[float] = None
    evolution_stage: int = 0
    age_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PetData':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            hunger=data.get('hunger', 50),
            happiness=data.get('happiness', 75),
            health=data.get('health', 100),
            energy=data.get('energy', 100),
            birth_time=data.get('birth_time', time.time()),
            last_update=data.get('last_update', time.time()),
            last_sleep_time=data.get('last_sleep_time'),
            evolution_stage=data.get('evolution_stage', 0),
            age_seconds=data.get('age_seconds', 0)
        )


@dataclass
class FriendData:
    """Data transfer object for friend"""
    id: Optional[int] = None
    device_name: str = ""
    pet_name: str = ""
    last_ip: Optional[str] = None
    last_port: Optional[int] = None
    last_seen: Optional[float] = None
    friendship_established: float = field(default_factory=time.time)


@dataclass
class FriendRequestData:
    """Data transfer object for friend request"""
    id: Optional[int] = None
    from_device_name: str = ""
    from_pet_name: str = ""
    from_ip: str = ""
    from_port: int = 0
    status: str = "pending"
    request_time: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)


@dataclass
class MessageData:
    """Data transfer object for message"""
    id: Optional[int] = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_device_name: str = ""
    from_pet_name: str = ""
    to_device_name: str = ""
    content: str = ""
    content_type: str = "text"
    is_read: bool = False
    received_at: float = field(default_factory=time.time)
    read_at: Optional[float] = None


# =============================================================================
# REPOSITORY INTERFACES
# =============================================================================

class PetRepository(ABC):
    """Abstract interface for pet data access"""

    @abstractmethod
    def get_active_pet(self) -> Optional[PetData]:
        """Get the currently active pet"""
        pass

    @abstractmethod
    def create_pet(self, name: str, hunger: int = None, happiness: int = None,
                   health: int = None, energy: int = None) -> Optional[int]:
        """Create a new pet and return its ID"""
        pass

    @abstractmethod
    def update_pet(self, pet_id: int, **kwargs) -> bool:
        """Update pet stats"""
        pass

    @abstractmethod
    def log_event(self, pet_id: int, event_type: str,
                  stat_changes: Dict[str, int] = None, notes: str = None) -> bool:
        """Log a pet event to history"""
        pass

    @abstractmethod
    def get_pet_history(self, pet_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent history for a pet"""
        pass


class FriendRepository(ABC):
    """Abstract interface for friend data access"""

    @abstractmethod
    def get_friends(self) -> List[FriendData]:
        """Get all friends"""
        pass

    @abstractmethod
    def get_friend(self, device_name: str) -> Optional[FriendData]:
        """Get a specific friend by device name"""
        pass

    @abstractmethod
    def add_friend(self, device_name: str, pet_name: str,
                   ip: str = None, port: int = None) -> bool:
        """Add a new friend"""
        pass

    @abstractmethod
    def update_friend(self, device_name: str, **kwargs) -> bool:
        """Update friend information"""
        pass

    @abstractmethod
    def remove_friend(self, device_name: str) -> bool:
        """Remove a friend"""
        pass

    @abstractmethod
    def is_friend(self, device_name: str) -> bool:
        """Check if device is a friend"""
        pass


class FriendRequestRepository(ABC):
    """Abstract interface for friend request data access"""

    @abstractmethod
    def get_pending_requests(self) -> List[FriendRequestData]:
        """Get all pending friend requests"""
        pass

    @abstractmethod
    def get_request(self, from_device_name: str) -> Optional[FriendRequestData]:
        """Get a specific request"""
        pass

    @abstractmethod
    def create_request(self, from_device_name: str, from_pet_name: str,
                       from_ip: str, from_port: int, expires_at: float) -> bool:
        """Create a new friend request"""
        pass

    @abstractmethod
    def update_request_status(self, from_device_name: str, status: str) -> bool:
        """Update request status (accepted/rejected)"""
        pass

    @abstractmethod
    def delete_request(self, from_device_name: str) -> bool:
        """Delete a friend request"""
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired requests, return count removed"""
        pass


class MessageRepository(ABC):
    """Abstract interface for message data access"""

    @abstractmethod
    def get_messages(self, device_name: str = None, unread_only: bool = False,
                     limit: int = 100) -> List[MessageData]:
        """Get messages, optionally filtered"""
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[MessageData]:
        """Get a specific message"""
        pass

    @abstractmethod
    def save_message(self, message: MessageData) -> bool:
        """Save a received message"""
        pass

    @abstractmethod
    def mark_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        pass

    @abstractmethod
    def get_unread_count(self, device_name: str = None) -> int:
        """Get count of unread messages"""
        pass

    @abstractmethod
    def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        pass


# =============================================================================
# IN-MEMORY IMPLEMENTATIONS (FOR TESTING)
# =============================================================================

class InMemoryPetRepository(PetRepository):
    """In-memory implementation of PetRepository for testing"""

    def __init__(self):
        self._pets: Dict[int, PetData] = {}
        self._active_pet_id: Optional[int] = None
        self._next_id = 1
        self._history: List[Dict[str, Any]] = []

    def get_active_pet(self) -> Optional[PetData]:
        if self._active_pet_id and self._active_pet_id in self._pets:
            return self._pets[self._active_pet_id]
        return None

    def create_pet(self, name: str, hunger: int = None, happiness: int = None,
                   health: int = None, energy: int = None) -> Optional[int]:
        pet_id = self._next_id
        self._next_id += 1

        pet = PetData(
            id=pet_id,
            name=name,
            hunger=hunger if hunger is not None else 50,
            happiness=happiness if happiness is not None else 75,
            health=health if health is not None else 100,
            energy=energy if energy is not None else 100
        )

        self._pets[pet_id] = pet
        self._active_pet_id = pet_id

        self.log_event(pet_id, "created", notes=f"Pet '{name}' created")
        return pet_id

    def update_pet(self, pet_id: int, **kwargs) -> bool:
        if pet_id not in self._pets:
            return False

        pet = self._pets[pet_id]
        for key, value in kwargs.items():
            if hasattr(pet, key) and value is not None:
                # Clamp stat values to 0-100
                if key in ('hunger', 'happiness', 'health', 'energy'):
                    value = max(0, min(100, value))
                setattr(pet, key, value)

        if 'last_update' not in kwargs:
            pet.last_update = time.time()

        return True

    def log_event(self, pet_id: int, event_type: str,
                  stat_changes: Dict[str, int] = None, notes: str = None) -> bool:
        self._history.append({
            'pet_id': pet_id,
            'timestamp': time.time(),
            'event_type': event_type,
            'stat_changes': stat_changes,
            'notes': notes
        })
        return True

    def get_pet_history(self, pet_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        pet_history = [h for h in self._history if h['pet_id'] == pet_id]
        return sorted(pet_history, key=lambda x: x['timestamp'], reverse=True)[:limit]


class InMemoryFriendRepository(FriendRepository):
    """In-memory implementation of FriendRepository for testing"""

    def __init__(self):
        self._friends: Dict[str, FriendData] = {}
        self._next_id = 1

    def get_friends(self) -> List[FriendData]:
        return list(self._friends.values())

    def get_friend(self, device_name: str) -> Optional[FriendData]:
        return self._friends.get(device_name)

    def add_friend(self, device_name: str, pet_name: str,
                   ip: str = None, port: int = None) -> bool:
        if device_name in self._friends:
            return False

        friend = FriendData(
            id=self._next_id,
            device_name=device_name,
            pet_name=pet_name,
            last_ip=ip,
            last_port=port,
            last_seen=time.time() if ip else None
        )
        self._next_id += 1
        self._friends[device_name] = friend
        return True

    def update_friend(self, device_name: str, **kwargs) -> bool:
        if device_name not in self._friends:
            return False

        friend = self._friends[device_name]
        for key, value in kwargs.items():
            if hasattr(friend, key):
                setattr(friend, key, value)
        return True

    def remove_friend(self, device_name: str) -> bool:
        if device_name in self._friends:
            del self._friends[device_name]
            return True
        return False

    def is_friend(self, device_name: str) -> bool:
        return device_name in self._friends


class InMemoryFriendRequestRepository(FriendRequestRepository):
    """In-memory implementation of FriendRequestRepository for testing"""

    def __init__(self):
        self._requests: Dict[str, FriendRequestData] = {}
        self._next_id = 1

    def get_pending_requests(self) -> List[FriendRequestData]:
        now = time.time()
        return [r for r in self._requests.values()
                if r.status == 'pending' and r.expires_at > now]

    def get_request(self, from_device_name: str) -> Optional[FriendRequestData]:
        return self._requests.get(from_device_name)

    def create_request(self, from_device_name: str, from_pet_name: str,
                       from_ip: str, from_port: int, expires_at: float) -> bool:
        request = FriendRequestData(
            id=self._next_id,
            from_device_name=from_device_name,
            from_pet_name=from_pet_name,
            from_ip=from_ip,
            from_port=from_port,
            expires_at=expires_at
        )
        self._next_id += 1
        self._requests[from_device_name] = request
        return True

    def update_request_status(self, from_device_name: str, status: str) -> bool:
        if from_device_name not in self._requests:
            return False
        self._requests[from_device_name].status = status
        return True

    def delete_request(self, from_device_name: str) -> bool:
        if from_device_name in self._requests:
            del self._requests[from_device_name]
            return True
        return False

    def cleanup_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._requests.items() if v.expires_at <= now]
        for k in expired:
            del self._requests[k]
        return len(expired)


class InMemoryMessageRepository(MessageRepository):
    """In-memory implementation of MessageRepository for testing"""

    def __init__(self):
        self._messages: Dict[str, MessageData] = {}
        self._next_id = 1

    def get_messages(self, device_name: str = None, unread_only: bool = False,
                     limit: int = 100) -> List[MessageData]:
        messages = list(self._messages.values())

        if device_name:
            messages = [m for m in messages if m.from_device_name == device_name]

        if unread_only:
            messages = [m for m in messages if not m.is_read]

        messages.sort(key=lambda x: x.received_at, reverse=True)
        return messages[:limit]

    def get_message(self, message_id: str) -> Optional[MessageData]:
        return self._messages.get(message_id)

    def save_message(self, message: MessageData) -> bool:
        if not message.id:
            message.id = self._next_id
            self._next_id += 1
        self._messages[message.message_id] = message
        return True

    def mark_read(self, message_id: str) -> bool:
        if message_id not in self._messages:
            return False
        self._messages[message_id].is_read = True
        self._messages[message_id].read_at = time.time()
        return True

    def get_unread_count(self, device_name: str = None) -> int:
        messages = list(self._messages.values())
        if device_name:
            messages = [m for m in messages if m.from_device_name == device_name]
        return sum(1 for m in messages if not m.is_read)

    def delete_message(self, message_id: str) -> bool:
        if message_id in self._messages:
            del self._messages[message_id]
            return True
        return False
