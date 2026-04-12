"""
ascii_renderer.py — Convert ViZDoom GRAY8 frame buffers to ASCII art.
"""
import os
import sys

import numpy as np

_RAMP       = " `.-_':,;^=+!|/\\1tfilI?rjJFfxX2YV3nuvczUCL0OZmwqpdbkhao*#M&8%B@"
_RAMP_LEN   = len(_RAMP)
_RAMP_ARRAY = np.array(list(_RAMP), dtype='U1')

_CURSOR_HOME  = "\033[H"
_CURSOR_HIDE  = "\033[?25l"
_CURSOR_SHOW  = "\033[?25h"
_CLEAR_SCREEN = "\033[2J"
_RESET        = "\033[0m"

_HP_FULL  = "#"
_HP_EMPTY = "-"
_HP_BAR   = 20


def _terminal_size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        return 80, 24


def _compute_dims(term_cols, term_rows):
    available_rows = max(5, term_rows - 4)
    cols_from_rows = int(available_rows * 8 / 3)
    cols = min(term_cols, cols_from_rows)
    rows = int(cols * 3 / 8)
    rows = min(rows, available_rows)
    return max(20, cols), max(5, rows)


class AsciiRenderer:

    def __init__(self, width=None, height=None, color=False):
        self._fixed_w  = width
        self._fixed_h  = height
        self._color    = color  # Enable TrueColor ANSI output
        self._last_tw  = self._last_th = 0
        self._cols     = self._rows = 0
        self._last_health = 100
        self._damage_flash = 0  # frames to show damage flash

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, screen_buf, health=100, ammo=50, kills=0, episode=1):
        tw, th = self._terminal_dims()
        if tw != self._last_tw or th != self._last_th:
            self._cols, self._rows = _compute_dims(tw, th)
            self._last_tw, self._last_th = tw, th

        # Detect damage taken
        if health < self._last_health:
            self._damage_flash = 5  # Show flash for 5 frames
        self._last_health = health
        
        # Apply damage flash effect
        if self._damage_flash > 0:
            self._damage_flash -= 1
        
        if self._color and screen_buf.ndim == 3:
            frame_str = self._frame_to_ascii_color(screen_buf, self._damage_flash > 0)
        else:
            frame_str = self._frame_to_ascii(screen_buf, self._damage_flash > 0)
        
        hud_str   = self._build_hud(health, ammo, kills, episode, self._cols, self._damage_flash > 0)
        sys.stdout.write(_CURSOR_HOME + frame_str + "\n" + hud_str)
        sys.stdout.flush()

    def render_episode_end(self, episode, kills, total_kills, duration,
                           map_name=None, completed=False, next_map=None, player_died=False):
        tw, _ = self._terminal_dims()
        mins, secs = divmod(int(duration), 60)
        
        if self._color:
            red = "\033[38;2;255;0;0m"
            green = "\033[38;2;0;255;0m"
            yellow = "\033[38;2;255;255;0m"
            reset = "\033[0m"
        else:
            red = green = yellow = reset = ""
        
        if completed and next_map:
            status = f"{green}{map_name} cleared! → {next_map}{reset}"
        elif completed:
            status = f"{green}{map_name} cleared!{reset}"
        elif player_died:
            status = f"{red}YOU DIED on {map_name}!{reset}"
        elif map_name:
            status = f"Died on {map_name}"
        else:
            status = f"Episode {episode} ended"
        
        line = (f"  [ {status} | "
                f"Kills: {kills}  Total: {total_kills}  "
                f"Time: {mins:02d}:{secs:02d} ]")
        sys.stdout.write("\n" + line[:tw])
        
        # Show helpful message when player dies
        if player_died:
            tip = f"\n  {yellow}TIP: Use cover, strafe (Q/E), and watch your HP!{reset}"
            sys.stdout.write(tip[:tw*2])
        
        sys.stdout.flush()

    def show_loading(self):
        sys.stdout.write(_CLEAR_SCREEN + _CURSOR_HOME +
                         "  Loading ViZDoom engine...\n")
        sys.stdout.flush()

    def show_banner(self, name: str):
        tw, _ = self._terminal_dims()
        from agent import HumanAgent
        banner = (f"  PLAYER MODE  |  {HumanAgent.CONTROLS}"
                  f"  |  Ctrl+C to quit")
        sys.stdout.write(_CLEAR_SCREEN + _CURSOR_HOME + banner[:tw] + "\n")
        sys.stdout.flush()

    def hide_cursor(self):
        sys.stdout.write(_CURSOR_HIDE)
        sys.stdout.flush()

    def show_cursor(self):
        sys.stdout.write(_CURSOR_SHOW + _RESET + "\n")
        sys.stdout.flush()

    def close(self):
        pass

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _terminal_dims(self):
        if self._fixed_w and self._fixed_h:
            return self._fixed_w, self._fixed_h
        tw, th = _terminal_size()
        if self._fixed_w: tw = self._fixed_w
        if self._fixed_h: th = self._fixed_h
        return tw, th

    def _frame_to_ascii(self, buf, damage_flash=False):
        """Convert grayscale buffer to ASCII (no color)."""
        orig_h, orig_w = buf.shape
        rows, cols = self._rows, self._cols
        row_idx = np.linspace(0, orig_h - 1, rows, dtype=int)
        col_idx = np.linspace(0, orig_w - 1, cols, dtype=int)
        small   = buf[np.ix_(row_idx, col_idx)]
        
        # Darken screen if taking damage
        if damage_flash:
            small = small * 0.5
        
        indices = (small.astype(np.float32) / 255.0 * (_RAMP_LEN - 1)).astype(int)
        return "\n".join("".join(_RAMP_ARRAY[indices[r]]) for r in range(rows))

    def _frame_to_ascii_color(self, buf, damage_flash=False):
        """Convert RGB buffer to colored ASCII using TrueColor ANSI codes."""
        # buf shape: (H, W, 3) for RGB24
        orig_h, orig_w = buf.shape[:2]
        rows, cols = self._rows, self._cols
        row_idx = np.linspace(0, orig_h - 1, rows, dtype=int)
        col_idx = np.linspace(0, orig_w - 1, cols, dtype=int)
        
        # Sample the buffer
        small = buf[np.ix_(row_idx, col_idx)]  # shape: (rows, cols, 3)
        
        # Apply damage flash (tint red)
        if damage_flash:
            small = small.copy()
            small[:,:,0] = np.clip(small[:,:,0] * 1.2, 0, 255)  # Boost red
            small[:,:,1] = small[:,:,1] * 0.5  # Reduce green
            small[:,:,2] = small[:,:,2] * 0.5  # Reduce blue
        
        # Convert to grayscale for character selection (luminance)
        if small.shape[2] == 3:
            gray = (0.299 * small[:,:,0] + 0.587 * small[:,:,1] + 0.114 * small[:,:,2])
        else:
            gray = small[:,:,0]
        
        indices = (gray.astype(np.float32) / 255.0 * (_RAMP_LEN - 1)).astype(int)
        
        # Build colored output
        lines = []
        for r in range(rows):
            line_parts = []
            for c in range(cols):
                char = _RAMP_ARRAY[indices[r, c]]
                # Get RGB values for this pixel
                r_val = int(small[r, c, 0])
                g_val = int(small[r, c, 1]) if small.shape[2] > 1 else r_val
                b_val = int(small[r, c, 2]) if small.shape[2] > 2 else r_val
                # Apply TrueColor ANSI
                colored_char = f"\033[38;2;{r_val};{g_val};{b_val}m{char}\033[0m"
                line_parts.append(colored_char)
            lines.append("".join(line_parts))
        return "\n".join(lines)

    def _build_hud(self, health, ammo, kills, episode, width, damage_flash=False):
        hp_filled = int(max(0, min(health, 100)) / 100 * _HP_BAR)
        hp_empty = _HP_BAR - hp_filled
        
        # Damage indicator
        dmg_indicator = " "
        if damage_flash:
            dmg_indicator = "!"
        
        # Color codes for HUD
        if self._color:
            # HP color based on level
            if health > 75:
                hp_color = "\033[38;2;0;255;0m"  # Green
            elif health > 25:
                hp_color = "\033[38;2;255;255;0m"  # Yellow
            else:
                hp_color = "\033[38;2;255;0;0m"  # Red
            
            red = "\033[38;2;255;0;0m"
            cyan = "\033[38;2;0;255;255m"
            yellow = "\033[38;2;255;255;0m"
            white = "\033[38;2;255;255;255m"
            reset = "\033[0m"
            
            hp_bar_str = f"{hp_color}{_HP_FULL * hp_filled}{white}{_HP_EMPTY * hp_empty}{reset}"
            
            # Show damage warning
            dmg_str = f"{red}DAMAGED!{reset}" if damage_flash else ""
            
            hud = (f"{cyan} EP:{episode:3d}{reset}  "
                   f"{hp_color}HP:[{hp_bar_str}]{health:3d}{reset}{dmg_str}  "
                   f"{yellow}AMMO:{ammo:3d}{reset}  "
                   f"{cyan}KILLS:{kills:3d}{reset}")
        else:
            hp_bar_str = (_HP_FULL * hp_filled).ljust(_HP_BAR, _HP_EMPTY)
            dmg_str = " DAMAGED!" if damage_flash else ""
            hud = (f" EP:{episode:3d}  "
                   f"HP:[{hp_bar_str}]{health:3d}{dmg_str}  "
                   f"AMMO:{ammo:3d}  "
                   f"KILLS:{kills:3d}")
        return hud[:width]
