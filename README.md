# doom-ascii

Doom running in your terminal. No GPU required.

![ASCII Doom](https://img.shields.io/badge/ASCII-Doom-red)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![ViZDoom](https://img.shields.io/badge/ViZDoom-powered-green)

## What is this?

A lightweight Doom experience that renders the game as ASCII art in real-time. Uses ViZDoom as the engine but displays everything in your terminal.

## Quick Start

```bash
pip install vizdoom pygame
python main.py
```

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| Graphics | `python main.py` | Pygame window (960×720) |
| ASCII | `python main.py --renderer ascii` | Terminal ASCII art |
| Color ASCII | `python main.py --renderer ascii --color` | Terminal with TrueColor |

## Controls

- **W/S** — Move forward/backward
- **A/D** — Turn left/right
- **Q/E** — Strafe left/right
- **Space** — Fire
- **F** — Use (doors, switches)
- **R** — Restart level
- **C/Esc** — Quit

## Requirements

- Python 3.10+
- Terminal with TrueColor support (for `--color` mode)

## Files

| File | What it does |
|------|--------------|
| `main.py` | Entry point, game loop |
| `ascii_renderer.py` | Terminal rendering (grayscale + colors) |
| `graphics_renderer.py` | Pygame window rendering |
| `game.py` | ViZDoom setup, scenarios |
| `agent.py` | Human player input handling |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Game won't start | `pip install vizdoom pygame` |
| Black/crashed window | Use `--renderer ascii` |
| Permission denied | Run terminal as Administrator |

## License

MIT — Doom is © id Software, this is just a fun terminal renderer.
