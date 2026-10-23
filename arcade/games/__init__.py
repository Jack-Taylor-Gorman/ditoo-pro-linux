"""Every module here that defines GAMES (a list of game classes) joins the menu.

Order on the menu is ORDER below, then anything else alphabetically, so a new
game file shows up without editing this one.
"""
import importlib
import pkgutil

ORDER = ["hexagon", "snake", "tetris", "breakout", "flappy", "stacker", "invaders",
         "racer", "dodge", "pong", "frogger", "simon", "helicopter", "asteroids", "minesweep"]


def load():
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        if hasattr(module, "GAMES"):
            found[info.name] = module.GAMES
    names = [n for n in ORDER if n in found] + sorted(n for n in found if n not in ORDER)
    return [cls for n in names for cls in found[n]]
