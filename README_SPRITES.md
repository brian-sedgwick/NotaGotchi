# Not-A-Gotchi Sprite Documentation

This document explains the sprite system for Not-A-Gotchi and how to create or replace pet sprites.

## Overview

Not-A-Gotchi uses a **swappable sprite system** - you can change the pet's appearance by simply replacing the sprite files in the `src/resources/sprites/` directory. No code changes required!

## Sprite Specifications

### Required Format
- **File Format**: BMP (Bitmap)
- **Color Depth**: 1-bit (black & white only)
- **Dimensions**: 100×100 pixels (square)
- **File Size**: ~1.3KB per sprite (uncompressed)
- **Background**: White (1)
- **Foreground**: Black (0)

### Important Notes
- The e-ink display is black and white only, so sprites must be 1-bit
- White pixels appear as white on the display
- Black pixels appear as black on the display
- Keep designs simple and high-contrast for best visibility on e-ink
- Avoid fine details or gray tones (they won't display properly)

## Required Sprite Files

The game requires **13 sprite files total**:

### Emotion Sprites (8 files)
These sprites display based on the pet's current emotional state:

| Filename | Emotion | When Displayed |
|----------|---------|----------------|
| `happy.bmp` | Happy | Default positive state |
| `sad.bmp` | Sad | Low happiness (<30) |
| `hungry.bmp` | Hungry | High hunger (>70) |
| `sick.bmp` | Sick | Low health (<30) |
| `sleeping.bmp` | Sleeping | During/after sleep action |
| `excited.bmp` | Excited | Very happy (>80) and well-fed |
| `content.bmp` | Content | All stats in healthy range |
| `dead.bmp` | Dead | Health = 0 (game over) |

### Stage Sprites (5 files)
These sprites display during evolution transitions:

| Filename | Stage | Age Range (Default) |
|----------|-------|---------------------|
| `egg.bmp` | Egg | 0-5 minutes |
| `baby.bmp` | Baby | 5-60 minutes |
| `child.bmp` | Child | 1-24 hours |
| `teen.bmp` | Teen | 1-3 days |
| `adult.bmp` | Adult | 3+ days |

## Sprite Priority

The game displays sprites in this priority order:
1. **Dead sprite** - If health = 0, always show `dead.bmp`
2. **Stage sprite** - For 5 seconds after evolution, show stage sprite
3. **Emotion sprite** - Otherwise, show emotion based on current stats

## Creating Sprites

### Recommended Tools
- **GIMP** (free, cross-platform) - Export as "1-bit BMP"
- **Photoshop** - Save as BMP, Bitmap mode
- **Paint.NET** - Save as 1-bit BMP
- **MS Paint** - Simple option for basic sprites

### Step-by-Step Guide (GIMP)

1. **Create New Image**
   - File → New
   - Set size to 100×100 pixels
   - Fill with white

2. **Draw Your Pet**
   - Use black brush/pencil for drawing
   - Keep it simple and high-contrast
   - Test visibility by zooming out

3. **Convert to 1-bit**
   - Image → Mode → Indexed
   - Use black and white (1-bit) palette
   - Image → Mode → Bitmap

4. **Export as BMP**
   - File → Export As
   - Choose filename (e.g., `happy.bmp`)
   - Select "BMP" format
   - Ensure 1-bit color depth

5. **Verify Size**
   - Check file size (~1-2KB)
   - Verify dimensions (100×100)

### Using the Placeholder Generator

The project includes a placeholder sprite generator:

```bash
cd src
python3 create_placeholder_sprites.py
```

This creates simple geometric placeholder sprites for all 13 files. Use these as:
- Templates to understand the style
- Temporary sprites while creating your own
- Starting point for customization

## Replacing Sprites

### On Development Machine

1. Create your sprites (100×100, 1-bit BMP)
2. Name them according to the table above
3. Copy to `src/resources/sprites/` directory

### On Raspberry Pi (Deployed)

**Method 1: SCP (Secure Copy)**
```bash
scp my_sprites/*.bmp pi@not-a-gotchi:~/not-a-gotchi/src/resources/sprites/
```

**Method 2: Via Git**
```bash
# Add sprites to git repo
git add src/resources/sprites/*.bmp
git commit -m "Update pet sprites"
git push

# On Raspberry Pi
cd ~/not-a-gotchi
git pull
```

**Method 3: Direct File Transfer**
- Use USB drive
- Copy files directly to `/home/pi/not-a-gotchi/src/resources/sprites/`

**No Restart Needed!** The sprite manager caches sprites, but new sprites will load automatically when the emotion/stage changes.

## Testing Sprites

### On Development Machine
```bash
cd src
python3 -c "from modules.sprite_manager import SpriteManager; sm = SpriteManager(); sm.preload_all_sprites()"
```

This will report any missing or incorrectly formatted sprites.

### On Raspberry Pi
Run the app in simulation mode to test without hardware:
```bash
python3 /home/pi/not-a-gotchi/src/main.py --simulation
```

## Troubleshooting

### Sprite Not Loading
- **Check filename**: Must exactly match the names in tables above
- **Check format**: Must be 1-bit BMP, not PNG/JPG/GIF
- **Check size**: Must be exactly 100×100 pixels
- **Check location**: Must be in `src/resources/sprites/` directory

### Sprite Looks Wrong on Display
- **Too detailed**: Simplify the design, use thicker lines
- **Low contrast**: Increase contrast between black and white areas
- **Inverted colors**: Swap black and white in your image editor

### Missing Sprite Warning
```
Warning: Sprite not found: happy.bmp
```
- Create the missing file
- Or copy placeholder using: `cp baby.bmp happy.bmp` (temporary fix)

## Example: Converting Existing Images

If you have existing character images (PNG, JPG, etc.):

1. **Open in GIMP**
2. **Resize**: Image → Scale Image → 100×100 pixels
3. **Convert to B&W**: Colors → Desaturate → Desaturate
4. **Increase Contrast**: Colors → Brightness-Contrast (boost contrast)
5. **Convert to Indexed**: Image → Mode → Indexed → 1-bit palette
6. **Export as BMP**: File → Export As → filename.bmp

## Character Sets

You can create themed sprite sets! Examples:
- **Scooby-Doo**: Different poses for emotions/stages
- **General Grievous**: Lightsaber battles, poses
- **Custom Pet**: Your own original character
- **Pixel Art**: Retro game-style pets
- **Minimalist**: Simple geometric shapes

Just ensure all 13 sprites maintain a consistent style.

## Tips for Great Sprites

✅ **Do:**
- Use thick, bold lines (3-5 pixels wide)
- Keep designs simple and iconic
- Test at 100×100 size before creating others
- Use clear facial expressions for emotions
- Make each sprite easily distinguishable

❌ **Don't:**
- Use gradients or anti-aliasing
- Add fine details or textures
- Use colors (they'll be lost)
- Make sprites too complex
- Forget to test on actual e-ink display

## Need Help?

- Check the `tests/` directory for display test scripts
- Look at placeholder sprites for inspiration
- Test sprites in simulation mode before deployment
- Remember: simple is better for e-ink displays!

---

**Happy sprite creating!** 🎨

Change your pet's look anytime by swapping out the BMP files!
