"""The arcade's runtime: a 16x16 canvas, input, sound and the game loop.

Frames go to the Ditoo as single images (0x44) the moment they change; the
speaker takes ~50 a second, so the screen is never the bottleneck. A pygame
window mirrors the screen at 30x and owns the keyboard, so input only reaches
the game while its window is focused and can never leak into anything else.

A game is a class with:
    name, colour            menu label and icon accent
    __init__(self, ctx)     ctx.sfx(name), ctx.rng, ctx.music(name)
    update(self, inp, dt)   inp.pressed(B) on the frame a button goes down,
                            inp.held(B) while it is down; dt in seconds
    draw(self, c)           paint the Canvas
    score, over             over=True ends the round
    icon(c) (classmethod)   optional 16x16 menu picture
"""
import json, math, os, random, select, time

import numpy as np

N = 16
OFF = (0, 0, 0)
ORANGE = (255, 90, 0)
WHITE = (255, 255, 255)
PEACH = (255, 170, 100)
EMBER = (70, 18, 0)
RED = (255, 20, 30)
GREEN = (40, 220, 60)
BLUE = (30, 110, 255)
CYAN = (0, 220, 230)
YELLOW = (255, 220, 0)
PURPLE = (170, 40, 255)
PINK = (255, 60, 160)
GREY = (70, 70, 70)

LEFT, RIGHT, UP, DOWN, A, B, START, QUIT = "left right up down a b start quit".split()

SCORES = os.path.expanduser("~/.local/share/ditoo/scores.json")

# 3x5 digits for scores, one string per row.
DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}


class Canvas:
    def __init__(self):
        self.px = np.zeros((N, N, 3), dtype=np.uint8)

    def clear(self, colour=OFF):
        self.px[:] = colour

    def set(self, x, y, colour):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < N and 0 <= y < N:
            self.px[y, x] = colour

    def get(self, x, y):
        return tuple(int(v) for v in self.px[int(y), int(x)])

    def rect(self, x, y, w, h, colour):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(N, int(x + w)), min(N, int(y + h))
        if x1 > x0 and y1 > y0:
            self.px[y0:y1, x0:x1] = colour

    def number(self, value, x, y, colour=WHITE):
        """Draw digits 3x5 with a 1px gap, left-aligned at x."""
        for i, ch in enumerate(str(value)):
            for row, bits in enumerate(DIGITS[ch]):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        self.set(x + i * 4 + col, y + row, colour)

    def number_width(self, value):
        return len(str(value)) * 4 - 1

    def fade(self, k):
        self.px[:] = (self.px.astype(np.float32) * k).astype(np.uint8)

    def image(self):
        return self.px


def dim(colour, k):
    return tuple(int(c * k) for c in colour)


class Input:
    def __init__(self):
        self.down, self.edge = set(), set()

    def held(self, b):
        return b in self.down

    def pressed(self, b):
        return b in self.edge

    def any_pressed(self):
        return bool(self.edge - {QUIT})


class Scores:
    def __init__(self):
        try:
            self.data = json.load(open(SCORES))
        except (OSError, ValueError):
            self.data = {}

    def best(self, name):
        return self.data.get(name, 0)

    def submit(self, name, score):
        new = score > self.best(name)
        if new:
            self.data[name] = score
            os.makedirs(os.path.dirname(SCORES), exist_ok=True)
            json.dump(self.data, open(SCORES, "w"), indent=1)
        return new


class Context:
    def __init__(self, sound, seed=None):
        self.sound = sound
        self.rng = random.Random(seed)

    def sfx(self, name):
        self.sound.play(name)

    def music(self, name):
        self.sound.music(name)


class Display:
    """Where frames go: the Ditoo, the mirror window, or nowhere (tests)."""

    def __init__(self, ditoo=True, window=True):
        self.ditoo = None
        self.last = None
        if ditoo:
            from importlib.machinery import SourceFileLoader
            screen = SourceFileLoader("ditoo_screen", os.path.expanduser("~/.local/bin/ditoo-screen")).load_module()
            self.encode = screen.encode_frame
            self.ditoo = screen.Ditoo()
        self.window = None
        if window:
            import pygame
            self.pg = pygame
            self.window = pygame.display.set_mode((N * 30, N * 30))
            pygame.display.set_caption("Ditoo Arcade")

    def show(self, canvas):
        px = canvas.image()
        if self.last is not None and np.array_equal(px, self.last):
            return
        self.last = px.copy()
        if self.ditoo:
            from PIL import Image
            img = Image.fromarray(px, "RGB")
            frame = self.encode(img, None)
            self.ditoo.send(0x44, [0x00, 0x0A, 0x0A, 0x04] + frame)
            # Drop the speaker's chatter so its receive buffer never fills.
            while select.select([self.ditoo.sock], [], [], 0)[0]:
                if not self.ditoo.sock.recv(4096):
                    break
        if self.window:
            surf = self.pg.surfarray.make_surface(px.swapaxes(0, 1))
            self.pg.transform.scale(surf, (N * 30, N * 30), self.window)
            # Thin grid so the mirror reads as LEDs, like the real thing.
            for i in range(1, N):
                self.pg.draw.line(self.window, (12, 12, 12), (i * 30, 0), (i * 30, N * 30))
                self.pg.draw.line(self.window, (12, 12, 12), (0, i * 30), (N * 30, i * 30))
            self.pg.display.flip()

    def close(self):
        if self.ditoo:
            self.ditoo.close()


KEYMAP = {
    "left": LEFT, "a": LEFT, "right": RIGHT, "d": RIGHT, "up": UP, "w": UP,
    "down": DOWN, "s": DOWN, "space": A, "z": A, "j": A, "x": B, "k": B,
    "return": START, "escape": QUIT, "backspace": QUIT,
}


class PygameInput:
    """Keyboard (window focus only) and any gamepad."""

    def __init__(self):
        import pygame
        self.pg = pygame
        pygame.joystick.init()
        self.pads = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.state = Input()
        self.axis = set()

    def poll(self):
        pg = self.pg
        self.state.edge = set()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self._press(QUIT)
            elif e.type == pg.KEYDOWN and pg.key.name(e.key) in KEYMAP:
                self._press(KEYMAP[pg.key.name(e.key)])
            elif e.type == pg.KEYUP and pg.key.name(e.key) in KEYMAP:
                self.state.down.discard(KEYMAP[pg.key.name(e.key)])
            elif e.type == pg.JOYBUTTONDOWN:
                self._press({0: A, 1: B, 7: START, 6: QUIT}.get(e.button, A))
            elif e.type == pg.JOYBUTTONUP:
                self.state.down.discard({0: A, 1: B, 7: START, 6: QUIT}.get(e.button, A))
            elif e.type == pg.JOYHATMOTION:
                hx, hy = e.value
                self._axis({LEFT: hx < 0, RIGHT: hx > 0, UP: hy > 0, DOWN: hy < 0})
            elif e.type == pg.JOYAXISMOTION and e.axis in (0, 1):
                v = e.value
                if e.axis == 0:
                    self._axis({LEFT: v < -0.5, RIGHT: v > 0.5})
                else:
                    self._axis({UP: v < -0.5, DOWN: v > 0.5})
        return self.state

    def _press(self, b):
        if b not in self.state.down:
            self.state.edge.add(b)
        self.state.down.add(b)

    def _axis(self, wanted):
        for b, on in wanted.items():
            if on:
                self._press(b)
            else:
                self.state.down.discard(b)


class Arcade:
    """Menu → game → score screen, forever, until QUIT on the menu."""

    def __init__(self, games, display, inputs, sound, fps=30):
        self.games, self.display, self.inputs, self.sound = games, display, inputs, sound
        self.fps = fps
        self.scores = Scores()
        self.canvas = Canvas()
        self.choice = 0

    def run(self, start=None):
        if start is not None:
            self.choice = start
            if not self.play(self.games[self.choice]):
                return
        while self.menu():
            if not self.play(self.games[self.choice]):
                return

    def _tick(self, last):
        now = time.perf_counter()
        wait = 1 / self.fps - (now - last)
        if wait > 0:
            time.sleep(wait)
        now = time.perf_counter()
        return now, min(0.1, now - last)

    def menu(self):
        """Returns False to quit the arcade."""
        last, t, slide = time.perf_counter(), 0.0, 0.0
        self.sound.music(None)
        while True:
            inp = self.inputs.poll()
            last, dt = self._tick(last)
            t += dt
            if inp.pressed(QUIT):
                return False
            if inp.pressed(LEFT) or inp.pressed(UP):
                self.choice = (self.choice - 1) % len(self.games)
                slide = -1.0
                self.sound.play("move")
            if inp.pressed(RIGHT) or inp.pressed(DOWN):
                self.choice = (self.choice + 1) % len(self.games)
                slide = 1.0
                self.sound.play("move")
            if inp.pressed(A) or inp.pressed(START):
                self.sound.play("start")
                return True
            slide *= 0.6
            c = self.canvas
            c.clear()
            game = self.games[self.choice]
            if hasattr(game, "icon"):
                game.icon(c)
            else:
                c.rect(3, 3, 10, 10, getattr(game, "colour", ORANGE))
            if abs(slide) > 0.05:
                shift = int(slide * 6)
                c.px[:] = np.roll(c.px, -shift, axis=1)
            # Arrows pulse at the edges so it's obvious there's more.
            k = 0.4 + 0.6 * (math.sin(t * 6) + 1) / 2
            for y in (7, 8):
                c.set(0, y, dim(WHITE, k))
                c.set(15, y, dim(WHITE, k))
            # Page dots along the bottom.
            n = len(self.games)
            for i in range(n):
                x = 8 - n // 2 + i
                if 0 <= x < N:
                    c.set(x, 15, ORANGE if i == self.choice else EMBER)
            self.display.show(c)

    def play(self, cls):
        """One round, then the score screen. Returns False to quit the arcade."""
        while True:
            ctx = Context(self.sound)
            game = cls(ctx)
            last = time.perf_counter()
            paused = False
            while not game.over:
                inp = self.inputs.poll()
                last, dt = self._tick(last)
                if inp.pressed(QUIT):
                    self.sound.music(None)
                    return True
                if inp.pressed(START):
                    paused = not paused
                    self.sound.play("select")
                if paused:
                    self.canvas.fade(0.97)
                    self.display.show(self.canvas)
                    continue
                game.update(inp, dt)
                self.canvas.clear()
                game.draw(self.canvas)
                self.display.show(self.canvas)
            self.sound.music(None)
            again = self.score_screen(cls, game.score)
            if again is None:
                return False
            if not again:
                return True

    def score_screen(self, cls, score):
        """True = play again, False = back to menu, None = quit."""
        best_before = self.scores.best(cls.name)
        record = self.scores.submit(cls.name, score)
        self.sound.play("record" if record else "die")
        last, t = time.perf_counter(), 0.0
        while True:
            inp = self.inputs.poll()
            last, dt = self._tick(last)
            t += dt
            if inp.pressed(QUIT):
                return False
            # Ignore presses for a moment so a held fire button doesn't skip it.
            if t > 0.8 and (inp.pressed(A) or inp.pressed(START)):
                self.sound.play("start")
                return True
            c = self.canvas
            c.clear()
            colour = YELLOW if record and int(t * 4) % 2 else ORANGE
            w = c.number_width(score)
            if w <= N:
                c.number(score, (N - w) // 2, 2, colour)
            else:  # long scores scroll
                off = int(t * 8) % (w + N)
                c.number(score, N - off, 2, colour)
            best = max(best_before, score)
            bw = c.number_width(best)
            c.rect(0, 8, N, 1, EMBER)
            if bw <= N:
                c.number(best, (N - bw) // 2, 10, PEACH)
            else:
                c.number(best, N - int(t * 8) % (bw + N), 10, PEACH)
            self.display.show(c)
