# SPEC.md — doom-ascii

Doom running in terminal via ViZDoom + ASCII art.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Game loop, input handling |
| `ascii_renderer.py` | Frame → ASCII conversion (grayscale + TrueColor) |
| `graphics_renderer.py` | Pygame window renderer |
| `game.py` | ViZDoom setup, scenarios |
| `agent.py` | Human player input |

## Features

- **ASCII Mode**: Terminal rendering with TrueColor support (`--color`)
- **Graphics Mode**: Pygame window (`--renderer graphics`)
- **Controls**: W/S move, A/D turn, Q/E strafe, Space fire, F use, R restart
- **HUD**: Health bar (color-coded), ammo, kills, episode counter

## Technical

- **Engine**: ViZDoom (headless, 320×240)
- **Format**: GRAY8 (fast) or RGB24 (colored)
- **FPS**: 30 (smooth terminal rendering)
- **Deps**: `vizdoom`, `pygame`, `numpy`
