# doom-ascii

Terminal-based Doom using ViZDoom + ASCII rendering.

## Install

Requires **Python 3.10+**

```bash
pip install vizdoom pygame
python main.py
```

## Usage

| Command | Mode |
|---------|------|
| `python main.py` | Graphics (default) |
| `python main.py --renderer ascii` | ASCII terminal |
| `python main.py --renderer ascii --color` | ASCII with colors |

**Controls:** W/S = move, A/D = turn, Q/E = strafe, Space = fire, F = use, R = restart

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "vizdoom not found" | `pip install vizdoom` |
| Black/crashed window | Use `--renderer ascii` |
| Permission errors | Run as Admin or use virtualenv |
