#!/usr/bin/env python3
"""
Create placeholder sprites for Not-A-Gotchi

Generates simple 100×100 1-bit BMP sprites for all emotions and stages.
"""

import os
from PIL import Image, ImageDraw, ImageFont


SPRITE_SIZE = (100, 100)
SPRITES_DIR = os.path.join(os.path.dirname(__file__), "resources", "sprites")


def create_sprite(filename, draw_function):
    """Create a sprite with the given drawing function"""
    # Create white background
    image = Image.new("1", SPRITE_SIZE, 1)
    draw = ImageDraw.Draw(image)

    # Call the drawing function
    draw_function(draw)

    # Save as BMP
    filepath = os.path.join(SPRITES_DIR, filename)
    image.save(filepath)
    print(f"Created: {filename}")


def draw_happy(draw):
    """Draw happy face ^_^"""
    # Eyes (happy slits)
    draw.arc([(25, 30), (40, 40)], start=180, end=360, fill=0, width=3)
    draw.arc([(60, 30), (75, 40)], start=180, end=360, fill=0, width=3)
    # Smile
    draw.arc([(30, 45), (70, 75)], start=0, end=180, fill=0, width=3)


def draw_sad(draw):
    """Draw sad face T_T"""
    # Eyes (sad)
    draw.line([(30, 30), (30, 40)], fill=0, width=2)
    draw.line([(70, 30), (70, 40)], fill=0, width=2)
    # Frown
    draw.arc([(30, 60), (70, 80)], start=180, end=360, fill=0, width=3)


def draw_hungry(draw):
    """Draw hungry face with open mouth"""
    # Eyes
    draw.ellipse([(25, 30), (35, 40)], fill=0)
    draw.ellipse([(65, 30), (75, 40)], fill=0)
    # Open mouth (O shape)
    draw.ellipse([(40, 55), (60, 75)], outline=0, width=3)


def draw_sick(draw):
    """Draw sick face X_X"""
    # Eyes (X marks)
    draw.line([(25, 30), (35, 40)], fill=0, width=2)
    draw.line([(25, 40), (35, 30)], fill=0, width=2)
    draw.line([(65, 30), (75, 40)], fill=0, width=2)
    draw.line([(65, 40), (75, 30)], fill=0, width=2)
    # Wavy mouth
    draw.arc([(30, 55), (50, 65)], start=0, end=180, fill=0, width=2)
    draw.arc([(50, 55), (70, 65)], start=180, end=360, fill=0, width=2)


def draw_sleeping(draw):
    """Draw sleeping face -_- zzz"""
    # Eyes (closed lines)
    draw.line([(25, 35), (40, 35)], fill=0, width=2)
    draw.line([(60, 35), (75, 35)], fill=0, width=2)
    # Mouth (small line)
    draw.line([(40, 60), (60, 60)], fill=0, width=2)
    # Z's for sleeping
    draw.text((75, 15), "z", fill=0)
    draw.text((82, 8), "z", fill=0)


def draw_excited(draw):
    """Draw excited face with sparkles"""
    # Eyes (wide open stars)
    # Left eye star
    draw.line([(30, 25), (30, 40)], fill=0, width=2)
    draw.line([(22, 32), (38, 32)], fill=0, width=2)
    # Right eye star
    draw.line([(70, 25), (70, 40)], fill=0, width=2)
    draw.line([(62, 32), (78, 32)], fill=0, width=2)
    # Big smile
    draw.arc([(25, 45), (75, 80)], start=0, end=180, fill=0, width=3)
    # Sparkles
    draw.line([(10, 10), (15, 15)], fill=0, width=2)
    draw.line([(85, 10), (90, 15)], fill=0, width=2)


def draw_content(draw):
    """Draw content face :)"""
    # Eyes (dots)
    draw.ellipse([(28, 32), (35, 39)], fill=0)
    draw.ellipse([(65, 32), (72, 39)], fill=0)
    # Small smile
    draw.arc([(35, 55), (65, 70)], start=0, end=180, fill=0, width=2)


def draw_dead(draw):
    """Draw dead face with X eyes"""
    # Eyes (X marks)
    draw.line([(25, 30), (35, 40)], fill=0, width=3)
    draw.line([(25, 40), (35, 30)], fill=0, width=3)
    draw.line([(65, 30), (75, 40)], fill=0, width=3)
    draw.line([(65, 40), (75, 30)], fill=0, width=3)
    # Flat line mouth
    draw.line([(30, 65), (70, 65)], fill=0, width=2)
    # Tombstone shape
    draw.rectangle([(5, 5), (95, 95)], outline=0, width=3)


def draw_egg(draw):
    """Draw egg shape"""
    # Egg outline
    draw.ellipse([(20, 10), (80, 90)], outline=0, width=3)
    # Crack pattern
    draw.line([(50, 30), (45, 45)], fill=0, width=2)
    draw.line([(45, 45), (55, 50)], fill=0, width=2)
    draw.line([(55, 50), (50, 60)], fill=0, width=2)


def draw_baby(draw):
    """Draw baby with pacifier"""
    # Round head
    draw.ellipse([(25, 15), (75, 65)], outline=0, width=2)
    # Eyes (small dots)
    draw.ellipse([(38, 30), (42, 34)], fill=0)
    draw.ellipse([(58, 30), (62, 34)], fill=0)
    # Pacifier
    draw.ellipse([(42, 45), (58, 55)], outline=0, width=2)
    draw.rectangle([(48, 50), (52, 60)], fill=0)


def draw_child(draw):
    """Draw child with curious expression"""
    # Head
    draw.ellipse([(20, 10), (80, 70)], outline=0, width=2)
    # Eyes (wide)
    draw.ellipse([(32, 28), (42, 38)], outline=0, width=2)
    draw.ellipse([(58, 28), (68, 38)], outline=0, width=2)
    # Small smile
    draw.arc([(35, 45), (65, 60)], start=0, end=180, fill=0, width=2)
    # Small body
    draw.rectangle([(35, 70), (65, 90)], outline=0, width=2)


def draw_teen(draw):
    """Draw teen with attitude"""
    # Head
    draw.ellipse([(15, 5), (85, 75)], outline=0, width=2)
    # Cool eyes (half-closed)
    draw.arc([(28, 28), (42, 38)], start=0, end=180, fill=0, width=2)
    draw.arc([(58, 28), (72, 38)], start=0, end=180, fill=0, width=2)
    # Smirk
    draw.arc([(35, 48), (60, 62)], start=0, end=150, fill=0, width=2)
    # Body
    draw.rectangle([(30, 75), (70, 95)], outline=0, width=2)


def draw_adult(draw):
    """Draw adult with confident expression"""
    # Head
    draw.ellipse([(10, 5), (90, 75)], outline=0, width=2)
    # Eyes (confident)
    draw.ellipse([(28, 25), (38, 35)], fill=0)
    draw.ellipse([(62, 25), (72, 35)], fill=0)
    # Content smile
    draw.arc([(30, 45), (70, 65)], start=0, end=180, fill=0, width=2)
    # Body
    draw.rectangle([(25, 75), (75, 95)], outline=0, width=2)
    # Arms
    draw.line([(25, 80), (10, 85)], fill=0, width=2)
    draw.line([(75, 80), (90, 85)], fill=0, width=2)


def main():
    """Create all placeholder sprites"""
    # Ensure sprites directory exists
    os.makedirs(SPRITES_DIR, exist_ok=True)

    print("Creating placeholder sprites...")
    print(f"Output directory: {SPRITES_DIR}")
    print()

    # Emotion sprites
    create_sprite("happy.bmp", draw_happy)
    create_sprite("sad.bmp", draw_sad)
    create_sprite("hungry.bmp", draw_hungry)
    create_sprite("sick.bmp", draw_sick)
    create_sprite("sleeping.bmp", draw_sleeping)
    create_sprite("excited.bmp", draw_excited)
    create_sprite("content.bmp", draw_content)
    create_sprite("dead.bmp", draw_dead)

    # Stage sprites
    create_sprite("egg.bmp", draw_egg)
    create_sprite("baby.bmp", draw_baby)
    create_sprite("child.bmp", draw_child)
    create_sprite("teen.bmp", draw_teen)
    create_sprite("adult.bmp", draw_adult)

    print()
    print("All sprites created successfully!")
    print(f"Total: 13 sprites (8 emotions + 5 stages)")


if __name__ == "__main__":
    main()
