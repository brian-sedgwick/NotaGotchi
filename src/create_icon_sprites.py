#!/usr/bin/env python3
"""
Create Icon Sprites for Stat Bars

Generates 20×20 pixel black and white BMP icons optimized for e-ink display.
"""

from PIL import Image, ImageDraw
import os

# Icon size
ICON_SIZE = 20

# Output directory
ICONS_DIR = os.path.join(os.path.dirname(__file__), "resources", "sprites", "icons")


def create_food_icon():
    """Create food/meat icon (drumstick shape)"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)  # White background
    draw = ImageDraw.Draw(img)

    # Simple drumstick shape (scaled up from 12px)
    # Bone part (thin rectangle at bottom)
    draw.rectangle([(8, 14), (11, 19)], fill=0)

    # Meat part (larger circle at top)
    draw.ellipse([(5, 3), (14, 12)], fill=0)

    return img


def create_happy_icon():
    """Create smiley face icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Face circle (larger)
    draw.ellipse([(2, 2), (17, 17)], outline=0, width=2)

    # Eyes (bigger dots)
    draw.ellipse([(6, 7), (8, 9)], fill=0)
    draw.ellipse([(11, 7), (13, 9)], fill=0)

    # Smile (arc)
    draw.arc([(5, 8), (14, 15)], start=0, end=180, fill=0, width=2)

    return img


def create_heart_icon():
    """Create heart icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Heart shape using polygon (scaled up)
    # Top left bump
    draw.ellipse([(3, 4), (9, 10)], fill=0)
    # Top right bump
    draw.ellipse([(10, 4), (16, 10)], fill=0)
    # Bottom triangle
    draw.polygon([(3, 8), (16, 8), (9, 17)], fill=0)

    return img


def create_energy_icon():
    """Create lightning bolt icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Lightning bolt shape (scaled up and more defined)
    points = [
        (12, 2),   # Top right
        (8, 9),    # Middle left
        (10, 9),   # Middle right
        (6, 18),   # Bottom left
        (10, 10),  # Back to middle
        (8, 10),   # Middle left again
    ]
    draw.polygon(points, fill=0)

    return img


def main():
    """Generate all icon sprites"""
    print("Creating icon sprites...")
    print(f"Output directory: {ICONS_DIR}")

    # Create output directory if it doesn't exist
    os.makedirs(ICONS_DIR, exist_ok=True)

    # Generate icons
    icons = {
        "food.bmp": create_food_icon,
        "happy.bmp": create_happy_icon,
        "heart.bmp": create_heart_icon,
        "energy.bmp": create_energy_icon,
    }

    for filename, create_func in icons.items():
        filepath = os.path.join(ICONS_DIR, filename)
        icon = create_func()
        icon.save(filepath)
        print(f"  Created: {filename}")

    print("\nIcon sprites created successfully!")
    print(f"Location: {ICONS_DIR}")


if __name__ == "__main__":
    main()
