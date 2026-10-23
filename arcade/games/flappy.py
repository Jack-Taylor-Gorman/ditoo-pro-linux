"""Flappy: tap to flap through the gaps between pipes.

The bird is one pixel with a sub-pixel position, drawn rounded. Pipes speed up,
come closer together and the gaps narrow as the score climbs. The bird waits
for the first flap so the round never starts before you do.
"""
import math

from arcade.engine import (A, GREEN, N, ORANGE, PEACH, UP, WHITE, YELLOW, dim)

GRAVITY = 42.0
FLAP = -11.5
MAX_FALL = 15.0
BIRD_X = 4
PIPE_W = 2


class Flappy:
    name = "Flappy"
    colour = YELLOW

    @classmethod
    def icon(cls, c):
        c.rect(11, 0, 3, 5, GREEN)
        c.rect(11, 11, 3, 5, GREEN)
        c.rect(10, 4, 5, 1, dim(GREEN, 0.6))
        c.rect(10, 11, 5, 1, dim(GREEN, 0.6))
        c.rect(3, 7, 3, 2, ORANGE)
        c.set(5, 7, WHITE)
        c.set(6, 8, YELLOW)
        c.set(2, 9, PEACH)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.y = 7.0
        self.vy = 0.0
        self.started = False
        self.t = 0.0
        self.pipes = []  # [x, gap_top, gap_h, scored]
        self.next_x = 17.0
        self.last_top = 5
        self.flash = 0.0
        self.wing = 0.0
        self.death_at = (BIRD_X, 7)
        ctx.music("chase")

    @property
    def speed(self):
        return min(11.0, 5.5 + self.score * 0.2)

    @property
    def gap(self):
        return max(3, 6 - self.score // 10)

    def spawn(self):
        gap = self.gap
        # A new gap is never so far from the last that it can't be reached.
        lo = max(1, self.last_top - 4)
        hi = min(N - 1 - gap, self.last_top + 4)
        top = self.rng.randint(lo, hi)
        self.last_top = top
        self.pipes.append([self.next_x, top, gap, False])
        self.next_x += PIPE_W + max(5, 7 - self.score // 12)

    def die(self):
        self.dying = 0.8
        self.flash = 0.0
        self.death_at = (BIRD_X, self.y)
        self.ctx.sfx("hit")
        self.ctx.sfx("die")
        self.ctx.music(None)

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
            self.y = min(N + 2, self.y + self.vy * dt)
            if self.dying <= 0:
                self.over = True
            return
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2)
        self.wing = max(0.0, self.wing - dt)
        flap = inp.pressed(A) or inp.pressed(UP)
        if flap:
            self.started = True
            self.vy = FLAP
            self.wing = 0.12
            self.ctx.sfx("flap")
        if not self.started:
            self.y = 7 + math.sin(self.t * 5) * 1.2
            return

        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        self.y += self.vy * dt
        if self.y < 0:
            self.y, self.vy = 0.0, 0.0
        self.next_x -= self.speed * dt
        for p in self.pipes:
            p[0] -= self.speed * dt
        self.pipes = [p for p in self.pipes if p[0] > -PIPE_W - 1]
        while self.next_x < N + 1:
            self.spawn()

        by = int(round(self.y))
        if by >= N:
            self.die()
            return
        for p in self.pipes:
            px = int(round(p[0]))
            if px <= BIRD_X < px + PIPE_W and not p[1] <= by < p[1] + p[2]:
                self.die()
                return
            if not p[3] and px + PIPE_W <= BIRD_X:
                p[3] = True
                self.score += 1
                self.ctx.sfx("coin")
                if self.score % 5 == 0:
                    self.flash = 1.0
                    self.ctx.sfx("level")

    def draw(self, c):
        c.clear(dim(ORANGE, 0.3 * self.flash) if self.flash else (0, 0, 0))
        for p in self.pipes:
            px = int(round(p[0]))
            c.rect(px, 0, PIPE_W, p[1], GREEN)
            c.rect(px, p[1] + p[2], PIPE_W, N, GREEN)
            c.rect(px, p[1] - 1, PIPE_W, 1, dim(GREEN, 0.55))  # lips
            c.rect(px, p[1] + p[2], PIPE_W, 1, dim(GREEN, 0.55))
        if self.dying:
            if int(self.dying * 14) % 2:
                c.set(self.death_at[0], self.y, WHITE)
            return
        c.set(BIRD_X - 1, self.y - self.vy * 0.04, dim(ORANGE, 0.4))
        c.set(BIRD_X, self.y, WHITE if self.wing else ORANGE)


GAMES = [Flappy]
