"""Super Hexagon: walls close in on the centre, find the gap.

Everything is measured in "hex distance", distance along the centre line of
the sector a point is in, so walls come out as hexagon edges rather than
circles. Touching a wall's side only blocks you, as in the original; meeting
its face is death.
"""
import math

import numpy as np

from arcade.engine import (A, B, EMBER, GREY, LEFT, N, OFF, ORANGE, PEACH, RIGHT,
                           WHITE, dim)

SIX = math.pi / 3
PLAYER_R = 3.2
SPAWN_R = 12.5
CORE_R = 1.7

# Stages as in the original, by seconds survived.
STAGES = [(0, "point"), (10, "line"), (20, "triangle"), (30, "square"),
          (45, "pentagon"), (60, "hexagon")]

ys, xs = np.mgrid[0:N, 0:N]
DX, DY = xs - 7.5, ys - 7.5
R = np.hypot(DX, DY)
ANG = np.arctan2(DY, DX) % (2 * math.pi)


def hex_space(rot):
    """Per-pixel sector index and hex distance for a world rotated by rot."""
    theta = (ANG - rot) % (2 * math.pi)
    sector = (theta // SIX).astype(int) % 6
    centre = sector * SIX + SIX / 2
    return sector, R * np.cos(theta - centre)


class Hexagon:
    name = "Hexagon"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        sector, h = hex_space(0.3)
        c.px[(h < 6.5) & (h > 5.3)] = WHITE
        c.px[(h < 6.5) & (h > 5.3) & (sector == 2)] = OFF
        c.px[h < 2.2] = ORANGE
        c.set(7, 4, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.time = 0.0
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.angle = SIX * 1.5  # player, in world space
        self.rot = 0.0
        self.spin = 1.2
        self.flip_at = 4.0
        self.walls = []  # [sector, distance, thickness]
        self.next_spawn = 0.6
        self.stage = 0
        self.flash = 0.0
        self.beat = 0.0
        self.last_sector = self.sector_of(self.angle)
        ctx.music("hexagon")

    # Difficulty: everything scales with time survived.
    @property
    def speed(self):
        return 5.0 + min(7.0, self.time * 0.09)

    def sector_of(self, angle):
        return int((angle % (2 * math.pi)) // SIX) % 6

    def blocked(self, sector):
        return any(s == sector and d - 0.2 <= PLAYER_R <= d + t + 0.2 for s, d, t in self.walls)

    def spawn(self):
        """Queue one pattern beyond the last wall; returns how far it extends."""
        rng = self.rng
        gap = 1.6 + max(0.0, 2.2 - self.time * 0.03)  # space between rows shrinks
        # Room to get from the last pattern's gap to this one's, or it's unwinnable.
        base = max([d + t + gap * 1.5 for _, d, t in self.walls] + [SPAWN_R])
        thick = 1.3
        kind = rng.choice(["c", "c", "triad", "spiral", "ladder", "double"] if self.time > 8 else ["c", "triad"])
        hole = rng.randrange(6)
        rows = []
        if kind == "c":
            rows = [[s for s in range(6) if s != hole]]
        elif kind == "triad":
            rows = [[s for s in range(6) if (s + hole) % 2 == 0], [s for s in range(6) if (s + hole) % 2 == 1]]
        elif kind == "double":
            rows = [[s for s in range(6) if s != hole], [s for s in range(6) if s != (hole + 3) % 6]]
        elif kind == "spiral":
            d = rng.choice((1, -1))
            rows = [[(hole + d * i) % 6, (hole + d * i + 3) % 6] for i in range(6)]
            gap *= 0.55
        elif kind == "ladder":
            rows = [[s for s in range(6) if s not in (hole, (hole + 3) % 6)], [hole, (hole + 3) % 6]] * 2
        for i, row in enumerate(rows):
            for s in row:
                self.walls.append([s, base + i * (gap + thick), thick])
        return base + len(rows) * (gap + thick)

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            self.rot += self.spin * dt * 0.3
            if self.dying <= 0:
                self.over = True
            return
        self.time += dt
        self.score = int(self.time)
        self.flash = max(0.0, self.flash - dt * 2)
        self.beat = (self.beat + dt * 168 / 60) % 1

        stage = sum(1 for t, _ in STAGES if self.time >= t) - 1
        if stage > self.stage:
            self.stage = stage
            self.flash = 1.0
            self.ctx.sfx("level")

        # The world turns, faster with time, and reverses now and then.
        self.flip_at -= dt
        if self.flip_at <= 0:
            self.spin = -math.copysign(1.0 + min(2.6, self.time * 0.04), self.spin) * self.rng.uniform(0.8, 1.2)
            self.flip_at = self.rng.uniform(2.5, 6.0)
        self.rot += self.spin * dt

        move = (inp.held(RIGHT) or inp.held(B)) - (inp.held(LEFT) or inp.held(A))
        if move:
            step = move * 9.0 * dt
            target = self.angle + step
            here = self.sector_of(self.angle)
            there = self.sector_of(target)
            if there != here and self.blocked(there):
                # Slide to the edge of our sector rather than through the wall.
                edge = (here + (1 if move > 0 else 0)) * SIX
                self.angle = edge - move * 0.001 + (self.angle - self.angle % (2 * math.pi))
            else:
                self.angle = target
        sector = self.sector_of(self.angle)
        if sector != self.last_sector:
            self.ctx.sfx("turn")
            self.last_sector = sector

        for w in self.walls:
            w[1] -= self.speed * dt
        self.walls = [w for w in self.walls if w[1] + w[2] > CORE_R]
        if max([d for _, d, _ in self.walls] + [0]) < SPAWN_R:
            self.spawn()

        for s, d, t in self.walls:
            if s == sector and d <= PLAYER_R <= d + t:
                self.dying = 0.9
                self.flash = 1.0
                self.ctx.sfx("explode")
                self.ctx.sfx("die")
                self.ctx.music(None)
                return

    def draw(self, c):
        sector, h = hex_space(self.rot)
        pulse = 0.15 * (1 - self.beat) ** 3  # the core thumps on the beat

        # Alternating sector background, as in the original.
        bg_a = dim(ORANGE, 0.22 + 0.25 * self.flash)
        bg_b = dim(ORANGE, 0.08 + 0.25 * self.flash)
        c.px[:] = OFF
        c.px[sector % 2 == 0] = bg_a
        c.px[sector % 2 == 1] = bg_b

        wall_colour = WHITE if not self.dying else PEACH
        for s, d, t in self.walls:
            c.px[(sector == s) & (h >= d) & (h < d + t)] = wall_colour

        core = CORE_R * (1 + pulse)
        c.px[h < core] = ORANGE
        c.px[h < core - 0.8] = dim(ORANGE, 0.5)

        if not self.dying or int(self.dying * 12) % 2:
            a = self.angle + self.rot
            c.set(7.5 + PLAYER_R * math.cos(a) - 0.5 + 0.5, 7.5 + PLAYER_R * math.sin(a) - 0.5 + 0.5,
                  WHITE if not self.dying else GREY)
GAMES = [Hexagon]
