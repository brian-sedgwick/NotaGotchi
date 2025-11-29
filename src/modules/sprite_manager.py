"""
Not-A-Gotchi Sprite Manager Module

Handles loading, caching, and managing pet sprites from BMP files.
"""

import os
from typing import Optional, Dict
from PIL import Image
from . import config


class SpriteManager:
    """Manages loading and caching of pet sprites"""

    def __init__(self, sprites_dir: str = None):
        """
        Initialize sprite manager

        Args:
            sprites_dir: Path to sprites directory (uses config default if None)
        """
        self.sprites_dir = sprites_dir or config.SPRITES_DIR
        self._sprite_cache: Dict[str, Image.Image] = {}
        self._missing_sprites: set = set()

        print(f"Sprite manager initialized: {self.sprites_dir}")

    def load_sprite(self, filename: str) -> Optional[Image.Image]:
        """
        Load a sprite from file, with caching

        Args:
            filename: Sprite filename (e.g., "happy.bmp")

        Returns:
            PIL Image object, or None if not found
        """
        # Check cache first
        if filename in self._sprite_cache:
            return self._sprite_cache[filename]

        # Check if we already know it's missing
        if filename in self._missing_sprites:
            return None

        # Try to load from disk
        sprite_path = os.path.join(self.sprites_dir, filename)

        if not os.path.exists(sprite_path):
            print(f"Warning: Sprite not found: {filename}")
            self._missing_sprites.add(filename)
            return None

        try:
            image = Image.open(sprite_path)

            # Validate dimensions
            if image.size != config.SPRITE_SIZE:
                print(f"Warning: Sprite {filename} has incorrect size {image.size}, "
                      f"expected {config.SPRITE_SIZE}. Resizing...")
                image = image.resize(config.SPRITE_SIZE, Image.LANCZOS)

            # Convert to 1-bit if needed
            if image.mode != config.SPRITE_FORMAT:
                print(f"Converting {filename} from {image.mode} to {config.SPRITE_FORMAT}")
                image = image.convert(config.SPRITE_FORMAT)

            # Cache the loaded sprite
            self._sprite_cache[filename] = image

            print(f"Loaded sprite: {filename}")
            return image

        except Exception as e:
            print(f"Error loading sprite {filename}: {e}")
            self._missing_sprites.add(filename)
            return None

    def get_emotion_sprite(self, emotion: str) -> Optional[Image.Image]:
        """
        Get sprite for an emotion state

        Args:
            emotion: Emotion name (e.g., "happy", "sad")

        Returns:
            PIL Image object, or None if not found
        """
        filename = config.EMOTION_SPRITES.get(emotion)
        if filename:
            return self.load_sprite(filename)
        return None

    def get_stage_sprite(self, stage: int) -> Optional[Image.Image]:
        """
        Get sprite for an evolution stage

        Args:
            stage: Evolution stage (0-4)

        Returns:
            PIL Image object, or None if not found
        """
        filename = config.STAGE_SPRITES.get(stage)
        if filename:
            return self.load_sprite(filename)
        return None

    def get_sprite_by_name(self, sprite_name: str) -> Optional[Image.Image]:
        """
        Get sprite by filename

        Args:
            sprite_name: Sprite filename (e.g., "happy.bmp")

        Returns:
            PIL Image object, or None if not found
        """
        return self.load_sprite(sprite_name)

    def create_placeholder_sprite(self, text: str = "?") -> Image.Image:
        """
        Create a simple placeholder sprite when actual sprite is missing

        Args:
            text: Text to display in placeholder

        Returns:
            PIL Image object
        """
        from PIL import ImageDraw, ImageFont

        # Create blank white image
        image = Image.new("1", config.SPRITE_SIZE, 1)
        draw = ImageDraw.Draw(image)

        # Draw a border
        draw.rectangle([(0, 0), (config.SPRITE_SIZE[0]-1, config.SPRITE_SIZE[1]-1)],
                      outline=0, width=2)

        # Draw simple face or text
        try:
            # Try to use default font
            font = ImageFont.load_default()

            # Draw a simple smiley face
            if text == "?":
                # Eyes
                draw.ellipse([(30, 35), (40, 45)], fill=0)
                draw.ellipse([(60, 35), (70, 45)], fill=0)
                # Smile
                draw.arc([(30, 50), (70, 70)], start=0, end=180, fill=0, width=2)
            else:
                # Draw text centered
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (config.SPRITE_SIZE[0] - text_width) // 2
                y = (config.SPRITE_SIZE[1] - text_height) // 2
                draw.text((x, y), text, fill=0, font=font)

        except Exception as e:
            print(f"Error creating placeholder: {e}")

        return image

    def preload_all_sprites(self):
        """Preload all configured sprites into cache"""
        print("Preloading all sprites...")

        # Load emotion sprites
        for emotion, filename in config.EMOTION_SPRITES.items():
            self.load_sprite(filename)

        # Load stage sprites
        for stage, filename in config.STAGE_SPRITES.items():
            self.load_sprite(filename)

        loaded_count = len(self._sprite_cache)
        missing_count = len(self._missing_sprites)
        total_count = loaded_count + missing_count

        print(f"Preload complete: {loaded_count}/{total_count} sprites loaded")

        if missing_count > 0:
            print(f"Missing sprites: {', '.join(self._missing_sprites)}")

    def clear_cache(self):
        """Clear the sprite cache"""
        self._sprite_cache.clear()
        self._missing_sprites.clear()
        print("Sprite cache cleared")

    def get_cache_info(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached': len(self._sprite_cache),
            'missing': len(self._missing_sprites)
        }

    def list_available_sprites(self) -> list:
        """List all BMP files in sprites directory"""
        if not os.path.exists(self.sprites_dir):
            return []

        sprites = [f for f in os.listdir(self.sprites_dir)
                  if f.endswith('.bmp')]
        return sorted(sprites)
