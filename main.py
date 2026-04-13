"""
main.py — doom-ascii entry point.

Play Doom yourself in the terminal or graphics window.

Usage:

    python main.py                               # interactive startup menu
    python main.py --renderer ascii              # play in the terminal
    python main.py --renderer graphics           # play in graphics window

Options:
    --renderer  {graphics,ascii}                   Renderer (default: graphics)
    --episodes  N     Stop after N episodes (0 = infinite)
    --tics      N     ViZDoom tics per step (default: 2)
    --fps       N     Target FPS for both modes (default: 35)
    --scale     N     Graphics window scale (default: 3 → 960×720)
    --width     N     ASCII column override
    --height    N     ASCII row override
    --scenario  PATH  Path to a .wad file (default: auto-detect)
"""
import argparse
import math
import sys
import time

from game import (setup_game, read_stats, read_position,
                  read_inventory, restore_inventory,
                  change_level, get_level_sequence)
from agent import HumanAgent


# ---------------------------------------------------------------------------
# Startup menu
# ---------------------------------------------------------------------------

def _pick(options: list, default: int = 1) -> str:
    for i, opt in enumerate(options, 1):
        tag = "  [default]" if i == default else ""
        print(f"    {i}. {opt}{tag}")
    while True:
        raw = input("  > ").strip()
        if raw == "":
            return options[default - 1]
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  Please enter 1–{len(options)}.")


def _show_controls():
    """Print control scheme, then wait for Enter."""
    print()
    print("  ── Human Player ─────────────────────────────────────")
    print("  W / S           Move forward / backward")
    print("  A / D           Turn left / right")
    print("  Q / E           Strafe left / right")
    print("  Space           Fire weapon")
    print("  F               Use / open doors")
    print("  C / Ctrl+C      Quit")
    print("  R               Restart episode")
    print()
    input("  Press Enter to return to menu... ")


def show_startup_menu(args):
    """Fill in args.renderer interactively if not set."""
    if args.renderer:
        return

    print()
    print("=" * 52)
    print("  DOOM ASCII")
    print("=" * 52)

    print("\n  Renderer:")
    args.renderer = _pick(["graphics", "ascii"], default=1)

    if args.renderer == "ascii":
        print("\n  Enable TrueColor? (requires terminal support)")
        color_choice = _pick(["yes", "no"], default=2)
        args.color = (color_choice == "yes")

    print()


# ---------------------------------------------------------------------------
# Renderer factory
# ---------------------------------------------------------------------------

def build_renderer(args):
    if args.renderer == "graphics":
        from graphics_renderer import GraphicsRenderer
        return GraphicsRenderer(scale=args.scale)
    from ascii_renderer import AsciiRenderer
    return AsciiRenderer(width=args.width, height=args.height, color=getattr(args, 'color', False))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="doom-ascii")
    p.add_argument("--renderer", default=None, choices=["graphics", "ascii"])
    p.add_argument("--episodes", type=int, default=0)
    p.add_argument("--tics",     type=int, default=2)
    p.add_argument("--fps",      type=int, default=35)
    p.add_argument("--scale",    type=int, default=3)
    p.add_argument("--width",    type=int, default=None)
    p.add_argument("--height",   type=int, default=None)
    p.add_argument("--scenario", type=str, default=None)
    p.add_argument("--color",    action="store_true",
                   help="Enable TrueColor ANSI output for ASCII renderer")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    show_startup_menu(args)

    # Apply defaults for anything the menu didn't fill.
    if not args.renderer: args.renderer = "graphics"

    renderer = build_renderer(args)
    renderer.show_loading()

    color = (args.renderer == "graphics")
    ascii_color = getattr(args, 'color', False) and args.renderer == "ascii"

    # Build level sequence before starting the game so we can pass the
    # first level's WAD to setup_game explicitly.
    level_sequence = get_level_sequence(args.scenario)
    level_idx      = 0

    try:
        if level_sequence and not args.scenario:
            first_wad, first_map, *_ = level_sequence[0]
            game = setup_game(scenario_path=first_wad, map_name=first_map, color=color, force_rgb24=ascii_color)
        else:
            game = setup_game(scenario_path=args.scenario, color=color, force_rgb24=ascii_color)
    except Exception as exc:
        renderer.close()
        sys.stdout.write(f"\nFailed to start ViZDoom: {exc}\n")
        sys.stdout.write("Install with:  pip install vizdoom\n")
        sys.exit(1)

    agent = HumanAgent(renderer_type=args.renderer)

    renderer.hide_cursor()
    renderer.show_banner("human")
    time.sleep(1.5)

    # Seconds of no new kills required to declare a level cleared.
    # Scales with FPS so timing is consistent across modes.
    _CLEAR_SECONDS = 10.0

    frame_duration   = 1.0 / max(1, args.fps)
    episode_num      = 0
    total_kills      = 0
    carried_weapons  = set()   # weapon slots that persist across levels
    carried_ammo     = {}      # ammo counts that persist across levels

    try:
        while True:
            episode_num += 1
            if args.episodes and episode_num > args.episodes:
                break

            game.new_episode()
            # Restore weapons/ammo carried from the previous level.
            if carried_weapons:
                restore_inventory(game, carried_weapons, carried_ammo)
                carried_weapons = set()
                carried_ammo    = {}
            agent.reset()

            kill_threshold = (level_sequence[level_idx][3]
                              if level_sequence else 0)
            ep_start            = time.monotonic()
            ep_kills            = 0
            prev_kills          = 0
            last_valid_state    = None
            running             = True
            restarting          = False
            all_cleared         = False
            last_kills          = 0
            no_kills_change_t   = 0

            while not game.is_episode_finished() and running:
                t0 = time.monotonic()

                try:
                    state = game.get_state()
                    if state is not None:
                        last_valid_state = state
                    health, ammo, kills = read_stats(state)
                    ep_kills = kills

                    # Level-clear detection.
                    # Threshold levels (continuous-spawn): advance once the
                    # player racks up kill_threshold kills.
                    # Stagnation levels (finite enemies): advance once the kill
                    # count hasn't risen for _CLEAR_FRAMES consecutive steps.
                    if kill_threshold > 0:
                        if kills >= kill_threshold:
                            all_cleared = True
                            break
                    else:
                        if kills > last_kills:
                            last_kills        = kills
                            no_kills_change_t = 0
                        elif kills > 0:
                            no_kills_change_t += 1
                            if no_kills_change_t >= int(_CLEAR_SECONDS * args.fps):
                                all_cleared = True
                                break

                    action = agent.act(state, health, ammo, kills)

                    # Check quit — human pressing c/ESC
                    if agent.quit_requested:
                        running = False
                        break

                    # Check restart — r key
                    if agent.restart_requested:
                        restarting = True
                        break

                    game.make_action(action, args.tics)

                    if state is not None and state.screen_buffer is not None:
                        result = renderer.render(
                            state.screen_buffer,
                            health=health,
                            ammo=ammo,
                            kills=kills,
                            episode=episode_num,

                        )
                        if result is False:   # pygame window closed / ESC
                            running = False

                except Exception as exc:
                    sys.stdout.write(f"\n[episode {episode_num}] error: {exc}\n")
                    break

                # Frame rate control for consistent timing in both modes
                elapsed = time.monotonic() - t0
                wait = frame_duration - elapsed
                if wait > 0:
                    time.sleep(wait)

            if restarting:
                episode_num -= 1   # don't count the restarted episode
                continue

            if not running:
                break

            player_died = game.is_player_dead()
            # Reaching the exit (episode finished, player alive) is a valid
            # completion — advance the level just like kill-all does.
            if game.is_episode_finished() and not player_died:
                all_cleared = True

            ep_time  = time.monotonic() - ep_start
            cur_name = level_sequence[level_idx][2] if level_sequence else None

            if player_died:
                # Wipe inventory — death means starting over from scratch.
                carried_weapons = set()
                carried_ammo    = {}
                total_kills += ep_kills
                restart_name = level_sequence[0][2] if level_sequence else None
                renderer.render_episode_end(
                    episode=episode_num,
                    kills=ep_kills,
                    total_kills=total_kills,
                    duration=ep_time,
                    map_name=cur_name,
                    completed=False,
                    next_map=restart_name,
                    player_died=True,
                )
                time.sleep(2.0)
                if level_sequence and level_idx != 0:
                    level_idx = 0
                    change_level(game, level_sequence[0][0], level_sequence[0][1])
                episode_num -= 1
                continue

            if not all_cleared:
                # Unexpected end — silent restart of same level.
                episode_num -= 1
                continue

            # Level cleared — save inventory then advance to the next level.
            carried_weapons, carried_ammo = read_inventory(last_valid_state)
            total_kills += ep_kills
            next_wad = next_map_id = next_name = None
            if level_sequence:
                level_idx = (level_idx + 1) % len(level_sequence)
                next_wad, next_map_id, next_name, _ = level_sequence[level_idx]

            renderer.render_episode_end(
                episode=episode_num,
                kills=ep_kills,
                total_kills=total_kills,
                duration=ep_time,
                map_name=cur_name,
                completed=True,
                next_map=next_name,
            )
            time.sleep(2.0)

            if next_wad:
                change_level(game, next_wad, next_map_id)

    except KeyboardInterrupt:
        pass
    finally:
        agent.stop()
        renderer.show_cursor()
        renderer.close()
        game.close()
        print(f"\ndoom-ascii exited.  Episodes: {episode_num}  "
              f"Total kills: {total_kills}")


if __name__ == "__main__":
    main()
