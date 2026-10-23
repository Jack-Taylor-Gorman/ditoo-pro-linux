"""Helicopter: hold A or UP to climb, let go to sink, don't touch the cave.

The cave scrolls left one column at a time. Over time it gets faster, the gap
narrows and the ceiling/floor wiggle harder; pillars appear that always leave
at least four or five pixels to squeeze past.
"""
from arcade.engine import (A, ORANGE, PEACH, N, UP, WHITE, YELLOW, dim)

HELI_X = 3  # body covers HELI_X and HELI_X + 1
WALL = (120, 38, 0)


class Helicopter:
    name = "Helicopter"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        for x in range(16):
            c.rect(x, 0, 1, 2 + (x * 3 // 8) % 3, WALL)
            h = 2 + (x * 3 // 8) % 3
            c.set(x, h, ORANGE)
            c.rect(x, 14 - (x * 5 // 8) % 3, 1, 3, WALL)
            c.set(x, 14 - (x * 5 // 8) % 3, ORANGE)
        c.rect(6, 7, 3, 2, WHITE)
        c.rect(5, 6, 5, 1, PEACH)
        c.set(4, 7, PEACH)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.t = 0.0
        self.y = 7.0
        self.vy = 0.0
        self.scroll = 0.0
        self.distance = 0
        self.center = 8.0
        self.slope = 0.0
        self.since_pillar = 0
        self.pillar_left = 0
        self.pillar = (0, 0)
        self.cols = [(2, 14, None) for _ in range(N)]  # (top, bottom, pillar rows)
        self.level = 0
        self.flash = 0.0
        self.rotor = 0.0
        self.chop = 0.0
        self.near_cd = 0.0
        self.death_at = (HELI_X, 7)
        ctx.music("chase")

    @property
    def cols_per_sec(self):
        return 6.0 + min(6.0, self.t * 0.07)

    def new_column(self):
        rng = self.rng
        gap = max(6, round(12 - self.t * 0.1))
        max_slope = min(0.6, 0.15 + self.t * 0.01)
        if rng.random() < 0.12 + min(0.2, self.t * 0.003):
            self.slope = rng.uniform(-max_slope, max_slope)
        self.center += self.slope
        lo, hi = 1 + gap / 2, N - 1 - gap / 2
        if not lo <= self.center <= hi:
            self.center = min(hi, max(lo, self.center))
            self.slope = -self.slope
        top = int(round(self.center - gap / 2))
        top = max(1, min(N - 1 - gap, top))
        bottom = top + gap
        pillar = None
        self.since_pillar += 1
        if self.pillar_left:
            self.pillar_left -= 1
            pillar = self.pillar
            # Keep the pillar inside the cave as the walls drift.
            pillar = (max(pillar[0], top), min(pillar[1], bottom))
        elif self.t > 8 and self.since_pillar > 9 and rng.random() < 0.15:
            length = max(2, gap - rng.choice((5, 6) if self.t < 40 else (4, 5)))
            if rng.random() < 0.5:
                self.pillar = (top, top + length)
            else:
                self.pillar = (bottom - length, bottom)
            self.pillar_left = 1  # two columns wide
            self.since_pillar = 0
            pillar = self.pillar
        self.cols.append((top, bottom, pillar))

    def blocked(self, x, row):
        top, bottom, pillar = self.cols[x]
        return row < top or row >= bottom or (pillar is not None and pillar[0] <= row < pillar[1])

    def die(self):
        self.dying = 0.8
        self.death_at = (HELI_X + 0.5, self.y)
        self.ctx.sfx("explode")
        self.ctx.sfx("die")
        self.ctx.music(None)

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2)
        self.rotor += dt * 20
        self.near_cd = max(0.0, self.near_cd - dt)

        up = inp.held(A) or inp.held(UP)
        if inp.pressed(A) or inp.pressed(UP):
            self.ctx.sfx("flap")
            self.chop = 0.2
        if up:
            self.chop -= dt
            if self.chop <= 0:
                self.ctx.sfx("tick")
                self.chop = 0.2
            self.vy = max(-8.0, self.vy - 90 * dt)
        else:
            self.vy = min(8.0, self.vy + 65 * dt)
        self.y += self.vy * dt

        self.scroll += self.cols_per_sec * dt
        while self.scroll >= 1:
            self.scroll -= 1
            self.cols.pop(0)
            self.new_column()
            self.distance += 1
            self.score = self.distance // 2

        level = int(self.t // 12)
        if level > self.level:
            self.level = level
            self.flash = 1.0
            self.ctx.sfx("level")

        ry = int(round(self.y))
        if ry < 0 or ry >= N or any(self.blocked(x, ry) for x in (HELI_X, HELI_X + 1)):
            self.die()
            return
        if self.near_cd == 0 and any(self.blocked(x, ry + d) for x in (HELI_X, HELI_X + 1) for d in (-1, 1)):
            self.ctx.sfx("near")
            self.near_cd = 0.4

    def draw(self, c):
        c.clear(dim(ORANGE, 0.3 * self.flash) if self.flash else (0, 0, 0))
        for x, (top, bottom, pillar) in enumerate(self.cols):
            if top:
                c.rect(x, 0, 1, top, WALL)
                c.set(x, top - 1, ORANGE)
            c.rect(x, bottom, 1, N, WALL)
            c.set(x, bottom, ORANGE)
            if pillar:
                c.rect(x, pillar[0], 1, pillar[1] - pillar[0], ORANGE)
                c.set(x, pillar[1] - 1 if pillar[0] == top else pillar[0], PEACH)
        if self.dying:
            if int(self.dying * 14) % 2:
                c.set(self.death_at[0], self.death_at[1], WHITE)
                c.set(self.death_at[0] + 1, self.death_at[1], YELLOW)
            return
        ry = self.y
        c.set(HELI_X - 1, ry, dim(WHITE, 0.5))  # tail
        c.set(HELI_X, ry, WHITE)
        c.set(HELI_X + 1, ry, WHITE)
        c.set(HELI_X + int(self.rotor) % 2, ry - 1, PEACH)  # rotor blade flickers


GAMES = [Helicopter]
