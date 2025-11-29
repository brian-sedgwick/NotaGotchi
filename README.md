# Not-A-Gotchi 🐾

A digital pet for Raspberry Pi Zero 2W with e-ink display - a modern take on the classic Tamagotchi experience.

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)

## Features

- 🐣 **Pet Lifecycle**: Watch your pet grow from egg to adult through 5 distinct stages
- ❤️ **Care System**: Feed, play, clean, and put your pet to sleep
- 📊 **Dynamic Stats**: Hunger, happiness, and health that change over time
- 😊 **Emotions**: 8 different emotional states based on how well you care for your pet
- 🎨 **Swappable Sprites**: Change your pet's appearance by replacing BMP files (no code changes!)
- 💾 **Persistent State**: SQLite database with power-loss protection (WAL mode)
- 🔄 **Auto-start**: Runs automatically on boot via systemd
- 🖥️ **E-ink Display**: 2.13" Waveshare display with partial refresh optimization
- 🎮 **Simple Controls**: Single rotary encoder with button for all interactions

## Hardware Requirements

- **Raspberry Pi Zero 2W** (or any Raspberry Pi with GPIO)
- **Waveshare 2.13" e-Paper Display V4** (250×122 pixels)
- **Rotary Encoder with Push Button**
- Power supply and SD card

### GPIO Pin Assignments

| Component | Pin | GPIO |
|-----------|-----|------|
| Encoder - Clock | 16 | GPIO 23 |
| Encoder - Data | 15 | GPIO 22 |
| Encoder - Button | 13 | GPIO 27 |
| Display - RST | 11 | GPIO 17 |
| Display - DC | 22 | GPIO 25 |
| Display - CS | 24 | GPIO 8 |
| Display - BUSY | 18 | GPIO 24 |
| Display - SPI (MOSI) | 19 | GPIO 10 |
| Display - SPI (SCK) | 23 | GPIO 11 |

## Quick Start

### Installation on Raspberry Pi

```bash
# 1. Clone the repository
cd ~
git clone <your-repo-url> not-a-gotchi
cd not-a-gotchi

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Enable SPI for e-ink display
sudo raspi-config
# → Interface Options → SPI → Enable

# 4. Generate placeholder sprites
cd src
python3 create_placeholder_sprites.py
cd ..

# 5. Test the application
python3 src/main.py --simulation

# 6. Install as system service (auto-start on boot)
sudo cp not-a-gotchi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable not-a-gotchi.service
sudo systemctl start not-a-gotchi.service

# 7. Check status
sudo systemctl status not-a-gotchi
```

### Updating the Application

```bash
# Pull latest changes
cd ~/not-a-gotchi
git pull

# Restart the service
sudo systemctl restart not-a-gotchi
```

## Usage

### Controls

| Action | Input |
|--------|-------|
| Navigate menu | Rotate encoder |
| Select / Add character | Short press button |
| Back / Cancel | Long press button (hold > 0.5s) |
| Open menu | Press button on home screen |

### Care Actions

- **Feed** - Reduces hunger, small happiness boost
- **Play** - Increases happiness significantly
- **Clean** - Improves health and mood
- **Sleep** - Restores health, increases hunger
- **Reset Pet** - Start over with a new pet (requires confirmation)

### Pet Stats

Your pet has three main stats that change over time:

- **Hunger** (0-100): Increases +1 per minute. Feed your pet to reduce it.
- **Happiness** (0-100): Decreases -0.5 per minute. Play with your pet to increase it.
- **Health** (0-100): Degrades when hungry (>80) or sad (<20). Recovers when well-fed and happy.

⚠️ **Warning**: If health reaches 0, your pet dies! Take good care of it!

### Evolution Stages

| Stage | Name | Age (Testing) | Age (Production) |
|-------|------|---------------|------------------|
| 0 | Egg | 0-5 min | 0-1 day |
| 1 | Baby | 5-60 min | 1-3 days |
| 2 | Child | 1-24 hours | 3-7 days |
| 3 | Teen | 1-3 days | 7-14 days |
| 4 | Adult | 3+ days | 14+ days |

*Note: Testing uses accelerated timings. Edit `config.py` to change stage thresholds.*

## Customization

### Changing Pet Sprites

See [README_SPRITES.md](./README_SPRITES.md) for complete sprite customization guide.

**Quick version:**
1. Create 100×100, 1-bit BMP images
2. Name them according to emotion/stage (e.g., `happy.bmp`, `egg.bmp`)
3. Copy to `src/resources/sprites/`
4. No restart needed!

### Configuration

Edit `src/modules/config.py` to customize:
- Evolution stage timings
- Stat degradation rates
- Care action effects
- Display refresh intervals
- GPIO pin assignments

## System Management

### Service Commands

```bash
# Start the service
sudo systemctl start not-a-gotchi

# Stop the service
sudo systemctl stop not-a-gotchi

# Restart the service
sudo systemctl restart not-a-gotchi

# View status
sudo systemctl status not-a-gotchi

# View logs
sudo journalctl -u not-a-gotchi -f

# Disable auto-start
sudo systemctl disable not-a-gotchi

# Enable auto-start
sudo systemctl enable not-a-gotchi
```

### Data Management

Pet data is stored in `~/data/not-a-gotchi.db` (SQLite database).

```bash
# Backup pet data
cp ~/data/not-a-gotchi.db ~/backup-$(date +%Y%m%d).db

# Reset pet (delete database)
sudo systemctl stop not-a-gotchi
rm ~/data/not-a-gotchi.db
sudo systemctl start not-a-gotchi
```

## Project Structure

```
not-a-gotchi/
├── src/
│   ├── main.py                      # Main application entry point
│   ├── create_placeholder_sprites.py # Sprite generator utility
│   ├── modules/
│   │   ├── __init__.py              # Package initialization
│   │   ├── config.py                # Configuration constants
│   │   ├── persistence.py           # SQLite database management
│   │   ├── pet.py                   # Pet logic and stats
│   │   ├── sprite_manager.py        # Sprite loading and caching
│   │   ├── display.py               # E-ink display rendering
│   │   ├── input_handler.py         # Rotary encoder input
│   │   └── screen_manager.py        # Screen state management
│   └── resources/
│       ├── sprites/                 # Pet sprite BMP files (13 files)
│       └── waveshare_epd/           # Waveshare display library
├── docs/                            # Documentation
├── tests/                           # Hardware test scripts
├── not-a-gotchi.service             # Systemd service file
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── README_SPRITES.md                # Sprite customization guide
```

## Development

### Running in Simulation Mode

Test without hardware:

```bash
python3 src/main.py --simulation
```

This runs the application without initializing GPIO or the display.

### Testing Individual Components

```bash
# Test database
python3 -c "from modules.persistence import DatabaseManager; db = DatabaseManager(); print('DB OK')"

# Test sprite loading
python3 -c "from modules.sprite_manager import SpriteManager; sm = SpriteManager(); sm.preload_all_sprites()"

# Test display (hardware required)
cd tests
python3 test_encoder_display.py

# Test encoder (hardware required)
cd tests
python3 test_encoder.py
```

## Troubleshooting

### Display Not Working

```bash
# Check SPI is enabled
lsmod | grep spi

# Test display directly
cd ~/not-a-gotchi/src/resources/waveshare_epd
python3 epd2in13_V4_test.py
```

### Input Not Working

```bash
# Test GPIO pins
python3 tests/test_encoder.py
```

### Service Won't Start

```bash
# Check logs
sudo journalctl -u not-a-gotchi -n 50

# Check permissions
ls -la /home/pi/not-a-gotchi/src/main.py

# Make sure script is executable
chmod +x /home/pi/not-a-gotchi/src/main.py
```

### Sprite Not Loading

- Check filename exactly matches required name
- Verify it's a 1-bit BMP, not PNG/JPG
- Confirm it's 100×100 pixels
- Check it's in `src/resources/sprites/` directory

## Technical Details

### Database Schema

- **pet_state**: Current pet data (name, stats, age, evolution stage)
- **pet_history**: Event log (care actions, stat updates, recoveries)
- **system_config**: Key-value configuration store

### Power Loss Protection

- SQLite WAL (Write-Ahead Logging) mode
- Auto-save every 60 seconds
- Save after every care action
- Recovery on startup with capped degradation (max 8 hours)

### Display Optimization

- Partial refresh for normal updates (0.6s)
- Full refresh every 10 updates to prevent ghosting
- Update throttling (1 second minimum between renders)

## Contributing

Contributions welcome! Areas for improvement:
- Mini-games
- WiFi connectivity for multiple devices
- More sprite sets
- Sound effects
- Additional care actions
- Achievement system

## License

[Your chosen license here]

## Acknowledgments

- Waveshare for e-Paper display libraries
- Bjorn project for reference architecture
- Tamagotchi for the original inspiration

## Support

- 📖 Documentation: See `docs/` directory
- 🎨 Sprite Guide: See `README_SPRITES.md`
- 🐛 Issues: [GitHub Issues](your-repo-url/issues)

---

**Enjoy raising your Not-A-Gotchi!** 🐾✨
