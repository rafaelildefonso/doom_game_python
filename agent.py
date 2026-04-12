"""
agent.py — Human player input for doom-ascii.
"""
import sys
import threading
import time

from game import (
    make_no_op,
    BTN_MOVE_LEFT, BTN_MOVE_RIGHT, BTN_MOVE_FORWARD, BTN_MOVE_BACKWARD,
    BTN_TURN_LEFT, BTN_TURN_RIGHT, BTN_ATTACK, BTN_USE,
)


class _KeyboardReader:
    """Background thread that reads raw keystrokes from stdin."""

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def get(self):
        with self._lock:
            return self._queue.pop(0) if self._queue else (None, 0)

    def stop(self):
        self._stop = True
        self._thread.join()

    def _run(self):
        if sys.platform == "win32":
            self._run_windows()
        else:
            self._run_unix()

    def _run_windows(self):
        import msvcrt
        while not self._stop:
            if msvcrt.kbhit():
                raw = msvcrt.getch()
                if raw == b'\xe0':
                    raw += msvcrt.getch()
                with self._lock:
                    self._queue.append((raw, time.monotonic()))
            time.sleep(0.01)

    def _run_unix(self):
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while not self._stop:
                import select
                if select.select([fd], [], [], 0.01)[0]:
                    raw = sys.stdin.buffer.read(1)
                    with self._lock:
                        self._queue.append((raw, time.monotonic()))
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


class HumanAgent:
    """Passes keyboard input directly to ViZDoom as actions."""

    CONTROLS = "W/S:fwd/back  A/D:turn  Q/E:strafe  SPC:fire  F:use"
    _KEY_TTL = 0.12

    def __init__(self, renderer_type="graphics"):
        self._mode = renderer_type
        self.strategy = "PLAYER"
        self.quit_requested = False
        self.restart_requested = False
        self._kb = _KeyboardReader() if renderer_type == "ascii" else None

    def reset(self):
        self.quit_requested = False
        self.restart_requested = False

    def stop(self):
        if self._kb:
            self._kb.stop()

    def act(self, state, health, ammo, kills):
        if self._mode == "graphics":
            return self._act_pygame()
        return self._act_terminal()

    def _act_pygame(self):
        import pygame
        k = pygame.key.get_pressed()
        action = make_no_op()
        action[BTN_MOVE_FORWARD] = bool(k[pygame.K_w] or k[pygame.K_UP])
        action[BTN_MOVE_BACKWARD] = bool(k[pygame.K_s] or k[pygame.K_DOWN])
        action[BTN_TURN_LEFT] = bool(k[pygame.K_a] or k[pygame.K_LEFT])
        action[BTN_TURN_RIGHT] = bool(k[pygame.K_d] or k[pygame.K_RIGHT])
        action[BTN_MOVE_LEFT] = bool(k[pygame.K_q])
        action[BTN_MOVE_RIGHT] = bool(k[pygame.K_e])
        action[BTN_ATTACK] = bool(k[pygame.K_SPACE])
        action[BTN_USE] = bool(k[pygame.K_f])
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c or event.key == pygame.K_ESCAPE:
                    self.quit_requested = True
                if event.key == pygame.K_r:
                    self.restart_requested = True
        return action

    def _act_terminal(self):
        action = make_no_op()
        now = time.monotonic()
        
        # Process ALL keys in queue for this frame (accumulate movement)
        while True:
            raw, ts = self._kb.get()
            if raw is None:
                break
            
            # Check for quit commands
            if raw in (b'\x03', b'\x1b', b'c', b'C'):
                self.quit_requested = True
                return action
            
            # Skip expired keys
            if now - ts > self._KEY_TTL:
                continue
            
            k = raw.lower()
            if k == b'r':
                self.restart_requested = True
                return action
            elif k == b'w':
                action[BTN_MOVE_FORWARD] = True
            elif k == b's':
                action[BTN_MOVE_BACKWARD] = True
            elif k in (b'a', b'\xe0\x4b'):
                action[BTN_TURN_LEFT] = True
            elif k in (b'd', b'\xe0\x4d'):
                action[BTN_TURN_RIGHT] = True
            elif k == b'q':
                action[BTN_MOVE_LEFT] = True
            elif k == b'e':
                action[BTN_MOVE_RIGHT] = True
            elif k == b' ':
                action[BTN_ATTACK] = True
            elif k == b'f':
                action[BTN_USE] = True
        
        return action
