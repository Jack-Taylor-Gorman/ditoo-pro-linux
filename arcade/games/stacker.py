"""Stacker: drop the sliding bar onto the tower; whatever overhangs is chopped off.

A drops the bar. It shrinks to the part that landed on the layer below, so the
tower narrows until you miss completely. The bar gets faster every floor, and
the view scrolls to keep the action in the top part of the screen.
"""
from arcade.engine import (A, EMBER, GREY, N, ORANGE, PEACH, RED, UP, WHITE, dim)

START_W = 6
KEEP_ROWS = 10  # the moving bar stays within this many rows of the bottom
DEATH_TIME = 0.9


class Stacker:
    name = "Stacker"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        for i, (x, w) in enumerate([(5, 6), (5, 5), (6, 4), (6, 3), (7, 2)]):
            c.rect(x, 14 - i * 2, w, 2, ORANGE if i % 2 == 0 else PEACH)
        c.rect(3, 2, 3, 1, WHITE)
        c.set(11, 3, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.layers = [(5, START_W)]  # (x, width), bottom first
        self.w = START_W
        self.mx = 0.0
        self.dir = 1
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.flash = 0.0
        self.glow = 0.0
        self.scroll = 0.0
        self.debris = []  # [x, row, fall speed]
        self.streak = 0
        ctx.music("chase")

    @property
    def floors(self):
        return len(self.layers) - 1

    @property
    def speed(self):
        return min(22.0, 6.0 + 0.45 * self.floors)

    def row_y(self, row):
        return 15 - (row - self.scroll)

    def drop(self):
        px, pw = self.layers[-1]
        pos = int(round(self.mx))
        left, right = max(pos, px), min(pos + self.w, px + pw)
        row = len(self.layers)
        self.ctx.sfx("drop")
        if right <= left:  # missed entirely
            for x in range(pos, pos + self.w):
                self.debris.append([x, float(row), 0.0])
            self.dying = DEATH_TIME
            self.ctx.sfx("explode")
            self.ctx.sfx("die")
            self.ctx.music(None)
            return
        for x in list(range(pos, left)) + list(range(right, pos + self.w)):
            self.debris.append([x, float(row), 0.0])
        if right - left == self.w:
            self.streak += 1
            self.score += 2
            self.glow = 0.25
            self.ctx.sfx("coin")
        else:
            self.streak = 0
            self.score += 1
            self.ctx.sfx("hit")
        self.layers.append((left, right - left))
        self.w = right - left
        if self.floors % 8 == 0:
            self.flash = 1.0
            self.ctx.sfx("level")
        self.mx = min(max(0.0, self.mx), N - self.w)

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.glow = max(0.0, self.glow - dt)
        target = max(0, len(self.layers) + 1 - KEEP_ROWS)
        self.scroll += (target - self.scroll) * min(1.0, dt * 8)
        for d in self.debris:
            d[2] += 40 * dt
            d[1] -= d[2] * dt
        self.debris = [d for d in self.debris if self.row_y(d[1]) < N + 1]
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        span = N - self.w
        self.mx += self.dir * self.speed * dt
        if self.mx >= span or self.mx <= 0:
            self.mx = max(0.0, min(span, self.mx))
            self.dir = -self.dir
        if inp.pressed(A) or inp.pressed(UP):
            self.drop()

    def draw(self, c):
        if self.flash:
            c.clear(dim(ORANGE, 0.25 * self.flash))
        blink = self.dying and int(self.dying * 12) % 2
        for i, (x, w) in enumerate(self.layers):
            y = int(round(self.row_y(i)))
            if not 0 <= y < N:
                continue
            col = ORANGE if i % 2 == 0 else PEACH
            if i % 8 == 0 and i:
                col = WHITE
            if i == len(self.layers) - 1 and self.glow:
                col = WHITE
            if blink:
                col = RED
            c.rect(x, y, w, 1, col)
        if not self.dying:
            y = int(round(self.row_y(len(self.layers))))
            px, pw = self.layers[-1]
            c.rect(px, y, pw, 1, EMBER)  # where it has to land
            c.rect(int(round(self.mx)), y, self.w, 1, WHITE)
        for x, row, _ in self.debris:
            c.set(x, int(round(self.row_y(row))), GREY if self.dying else PEACH)


GAMES = [Stacker]
