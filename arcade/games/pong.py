"""Pong: you on the left, a CPU on the right that gets sharper every point you win.

The ball leaves a paddle at an angle set by where it hit (edges steer hard),
and speeds up every rally hit. Three missed balls ends the game; score is the
points you won.
"""
import math

from arcade.engine import DOWN, EMBER, N, ORANGE, PEACH, RED, UP, WHITE, dim

PH = 4  # paddle height
LIVES = 3


class Pong:
    name = "Pong"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        for y in range(1, 15, 2):
            c.set(7, y, EMBER)
            c.set(8, y, EMBER)
        c.rect(1, 2, 1, 5, WHITE)
        c.rect(14, 8, 1, 5, ORANGE)
        for i, (x, y) in enumerate([(4, 8), (6, 7), (8, 6), (10, 5)]):
            c.set(x, y, dim(ORANGE, 0.25 + i * 0.2))
        c.rect(11, 4, 2, 2, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.lives = LIVES
        self.py = 6.0
        self.cy = 6.0
        self.cpu_target = 6.0
        self.cpu_timer = 0.0
        self.hits = 0
        self.flash = 0.0
        self.flash_col = WHITE
        self.dying = 0.0
        self.serve_in = 0.0
        self.serve(1)
        ctx.music("chase")

    # CPU gets better with every point the player scores.
    @property
    def cpu_speed(self):
        return min(17.0, 6.5 + self.score * 1.3)

    @property
    def cpu_reaction(self):
        return max(0.05, 0.4 - self.score * 0.04)

    @property
    def cpu_error(self):
        return max(0.0, 2.6 - self.score * 0.3)

    def serve(self, direction):
        self.bx, self.by = 7.5, self.rng.uniform(4, 11)
        self.base = min(16.0, 7.0 + self.score * 0.5)
        self.speed = self.base
        ang = self.rng.uniform(-0.5, 0.5)
        self.vx = direction * math.cos(ang)
        self.vy = math.sin(ang)
        self.serve_in = 0.7
        self.hits = 0

    def move_paddle(self, y, d, dt, speed):
        return max(0.0, min(N - PH, y + d * speed * dt))

    def bounce_off(self, py, side):
        off = (self.by - (py + PH / 2)) / (PH / 2 + 0.5)
        off = max(-1.0, min(1.0, off))
        ang = off * 1.0  # radians, up to ~57 degrees
        self.speed = min(22.0, self.speed + 0.6)
        self.vx = -side * math.cos(ang)
        self.vy = math.sin(ang)

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 3)
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return

        # Player paddle responds on the frame of the press.
        d = inp.held(DOWN) - inp.held(UP)
        if inp.pressed(UP) or inp.pressed(DOWN):
            self.py = self.move_paddle(self.py, d, 1.0, 0.5)
        self.py = self.move_paddle(self.py, d, dt, 18.0)

        # CPU: re-aims on a timer, with an error that shrinks over time.
        self.cpu_timer -= dt
        if self.cpu_timer <= 0:
            self.cpu_timer = self.cpu_reaction
            if self.vx > 0:
                aim = self.by + self.rng.uniform(-1, 1) * self.cpu_error
            else:
                aim = 8.0
            self.cpu_target = aim - PH / 2
        gap = self.cpu_target - self.cy
        step = self.cpu_speed * dt
        self.cy = max(0.0, min(N - PH, self.cy + max(-step, min(step, gap))))

        if self.serve_in > 0:
            self.serve_in -= dt
            return

        self.bx += self.vx * self.speed * dt
        self.by += self.vy * self.speed * dt
        if self.by < 0.5:
            self.by, self.vy = 0.5, abs(self.vy)
            self.ctx.sfx("bounce")
        elif self.by > N - 0.5:
            self.by, self.vy = N - 0.5, -abs(self.vy)
            self.ctx.sfx("bounce")

        if self.vx < 0 and self.bx < 1.0:
            if self.py - 0.6 <= self.by <= self.py + PH + 0.6:
                self.bx = 1.0
                self.bounce_off(self.py, -1)
                self.hits += 1
                self.ctx.sfx("hit")
            elif self.bx < -0.5:
                self.lives -= 1
                self.flash, self.flash_col = 1.0, RED
                if self.lives <= 0:
                    self.dying = 0.9
                    self.ctx.sfx("explode")
                    self.ctx.sfx("die")
                    self.ctx.music(None)
                else:
                    self.ctx.sfx("drop")
                    self.serve(1)
        elif self.vx > 0 and self.bx > N - 2.0:
            if self.cy - 0.6 <= self.by <= self.cy + PH + 0.6:
                self.bx = N - 2.0
                self.bounce_off(self.cy, 1)
                self.hits += 1
                self.ctx.sfx("hit")
            elif self.bx > N + 0.5:
                self.score += 1
                self.flash, self.flash_col = 1.0, ORANGE
                self.ctx.sfx("coin")
                self.ctx.sfx("level")  # CPU just got better
                self.serve(-1)

    def draw(self, c):
        if self.dying:
            k = int(self.dying * 14) % 2
            c.clear()
            if k:
                c.rect(0, int(self.py), 1, PH, WHITE)
                c.rect(N - 1, int(self.cy), 1, PH, ORANGE)
            return
        c.rect(0, 0, N, N, dim(self.flash_col, 0.25 * self.flash))
        for y in range(0, N, 2):
            c.set(7, y, EMBER)
        c.rect(0, int(round(self.py)), 1, PH, WHITE)
        c.rect(N - 1, int(round(self.cy)), 1, PH, ORANGE)
        if self.serve_in <= 0 or int(self.serve_in * 10) % 2:
            c.set(self.bx, self.by - 0.5, PEACH if self.speed > 12 else WHITE)
        for i in range(self.lives):
            c.set(1 + i * 2, 0, RED)


GAMES = [Pong]
