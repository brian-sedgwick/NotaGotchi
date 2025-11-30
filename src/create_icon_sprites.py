#!/usr/bin/env python3
"""
Create Icon Sprites for Stat Bars

Generates 12×12 pixel black and white BMP icons optimized for e-ink display.
"""

from PIL import Image, ImageDraw
import os

# Icon size
ICON_SIZE = 12

# Output directory
ICONS_DIR = os.path.join(os.path.dirname(__file__), "resources", "sprites", "icons")


def create_food_icon():
    """Create food/meat icon (drumstick shape)"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)  # White background
    draw = ImageDraw.Draw(img)

    # Simple drumstick shape
    # Bone part (thin rectangle at bottom)
    draw.rectangle([(5, 8), (6, 11)], fill=0)

    # Meat part (circle at top)
    draw.ellipse([(3, 2), (8, 7)], fill=0)

    return img


def create_happy_icon():
    """Create smiley face icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Face circle
    draw.ellipse([(1, 1), (10, 10)], outline=0, width=1)

    # Eyes
    draw.point((4, 4), fill=0)
    draw.point((7, 4), fill=0)

    # Smile (arc)
    draw.arc([(3, 5), (8, 9)], start=0, end=180, fill=0, width=1)

    return img


def create_heart_icon():
    """Create heart icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Heart shape using polygon
    # Top left bump
    draw.ellipse([(2, 2), (5, 5)], fill=0)
    # Top right bump
    draw.ellipse([(6, 2), (9, 5)], fill=0)
    # Bottom triangle
    draw.polygon([(2, 4), (9, 4), (5, 10)], fill=0)

    return img


def create_energy_icon():
    """Create lightning bolt icon"""
    img = Image.new('1', (ICON_SIZE, ICON_SIZE), 1)
    draw = ImageDraw.Draw(img)

    # Lightning bolt shape
    points = [
        (7, 1),   # Top right
        (5, 5),   # Middle left
        (6, 5),   # Middle right
        (4, 11),  # Bottom left
        (6, 6),   # Back to middle
        (5, 6),   # Middle left again
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
