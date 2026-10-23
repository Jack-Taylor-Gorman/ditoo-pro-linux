"""Frogger: hop across seven lanes of traffic and six of river to the far bank.

One press is one hop, instantly. Cars kill; on the river you must ride logs,
which carry you sideways, and drifting off the screen or into water kills.
Each crossing scores one and makes every lane faster and busier. Three lives.
"""
from arcade.engine import (BLUE, CYAN, DOWN, GREEN, LEFT, N, ORANGE, PINK, RED, RIGHT, UP,
                           WHITE, YELLOW, dim)

GOAL, START = 0, 15
RIVER = range(1, 7)
MEDIAN = 7
ROAD = range(8, 15)
BANK = (40, 10, 70)
WATER = (0, 15, 80)
ROADBG = (14, 14, 14)
LOG = (150, 80, 20)
CARS = [RED, YELLOW, PINK, CYAN, WHITE]


class Frogger:
    name = "Frogger"
    colour = GREEN

    @classmethod
    def icon(cls, c):
        c.rect(0, 0, N, 5, WATER)
        c.rect(0, 5, N, 2, BANK)
        c.rect(0, 7, N, 5, ROADBG)
        c.rect(0, 12, N, 4, BANK)
        c.rect(1, 2, 5, 1, LOG)
        c.rect(9, 3, 5, 1, LOG)
        c.rect(2, 8, 2, 1, RED)
        c.rect(10, 9, 2, 1, YELLOW)
        c.rect(5, 10, 2, 1, CYAN)
        c.rect(7, 13, 2, 2, GREEN)
        c.set(7, 13, WHITE)
        c.set(8, 13, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.lives = 3
        self.level = 0
        self.t = 0.0
        self.flash = 0.0
        self.dying = 0.0
        self.final = False
        self.build()
        self.respawn()
        ctx.music("chase")

    def build(self):
        """Lanes for the current level: row -> (direction, speed, length, offsets, colours)."""
        rng = self.rng
        k = min(1.0 + self.level * 0.12, 2.2)
        self.lanes = {}
        for i, row in enumerate(ROAD):
            n = min(4, 1 + (self.level + i) // 3 + rng.randrange(2))
            length = rng.choice((1, 1, 2))
            self.lanes[row] = self.lane(row, rng.uniform(2.0, 4.0) * k, length, n, True)
        for i, row in enumerate(RIVER):
            length = rng.choice((3, 4, 4)) if self.level < 4 else rng.choice((2, 3, 3))
            n = 2 if length > 2 or self.level < 6 else 3
            self.lanes[row] = self.lane(row, rng.uniform(1.5, 3.0) * min(k, 1.7), length, n, False)

    def lane(self, row, speed, length, n, cars):
        d = 1 if row % 2 else -1
        slot = N / n
        # Evenly spread objects, jittered so lanes don't line up.
        base = self.rng.uniform(0, N)
        offs = [(base + i * slot + self.rng.uniform(-0.5, 0.5)) % N for i in range(n)]
        cols = [self.rng.choice(CARS) for _ in offs] if cars else [LOG] * n
        return (d, speed, length, offs, cols)

    def respawn(self):
        self.fx, self.fy = 7.0, float(START)

    def occupied(self, row, cx):
        """The object covering x=cx in a lane's row, as its colour, else None."""
        d, speed, length, offs, cols = self.lanes[row]
        for o, col in zip(offs, cols):
            x = (o + d * speed * self.t) % N
            if (cx - x) % N < length:
                return col
        return None

    def die(self):
        self.lives -= 1
        self.dying = 0.7 if self.lives > 0 else 1.0
        self.flash = 1.0
        self.ctx.sfx("explode" if self.lives > 0 else "die")
        if self.lives <= 0:
            self.final = True
            self.ctx.music(None)

    def update(self, inp, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                if self.final:
                    self.over = True
                else:
                    self.dying = 0.0
                    self.respawn()
            return

        fy = int(self.fy)
        hopped = True
        if inp.pressed(UP):
            self.fy -= 1
            self.ctx.sfx("jump")
        elif inp.pressed(DOWN) and fy < START:
            self.fy += 1
            self.ctx.sfx("move")
        elif inp.pressed(LEFT) and self.fx > 0:
            self.fx = round(self.fx) - 1
            self.ctx.sfx("move")
        elif inp.pressed(RIGHT) and self.fx < N - 1:
            self.fx = round(self.fx) + 1
            self.ctx.sfx("move")
        else:
            hopped = False
        if hopped:
            self.fx = float(round(self.fx))
        row = int(self.fy)

        if row == GOAL:
            self.score += 1
            self.level += 1
            self.flash = 1.0
            self.ctx.sfx("coin")
            self.ctx.sfx("level")
            self.build()
            self.respawn()
            return

        if row in self.lanes:
            cx = self.fx + 0.5
            hit = self.occupied(row, cx)
            if row in ROAD:
                if hit is not None:
                    self.die()
                    return
            else:
                if hit is None:
                    self.die()
                    return
                d, speed = self.lanes[row][:2]
                self.fx += d * speed * dt
                if self.fx < -0.5 or self.fx > N - 0.5:
                    self.die()

    def draw(self, c):
        c.rect(0, GOAL, N, 1, dim(GREEN, 0.35))
        c.rect(0, RIVER[0], N, len(RIVER), WATER)
        c.rect(0, MEDIAN, N, 1, BANK)
        c.rect(0, ROAD[0], N, len(ROAD), ROADBG)
        c.rect(0, START, N, 1, BANK)
        for row in self.lanes:
            for x in range(N):
                col = self.occupied(row, x + 0.5)
                if col is not None:
                    c.set(x, row, col)
        for i in range(self.lives):
            c.set(1 + i * 2, GOAL, WHITE)
        if self.dying:
            if int(self.dying * 12) % 2:
                c.set(self.fx, self.fy, RED)
                for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                    c.set(self.fx + dx, self.fy + dy, ORANGE)
        else:
            c.set(self.fx, self.fy, (60, 255, 60))
        if self.flash > 0.3 and not self.dying:
            c.rect(0, 0, N, 1, dim(WHITE, self.flash))


GAMES = [Frogger]
