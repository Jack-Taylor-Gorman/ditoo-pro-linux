"""Dodge: meteors rain down; slip between them and dash through the worst.

Move freely left and right, and up and down within the lower band. A dashes a
few pixels in the direction held and makes you untouchable for a moment; the
pixel in the bottom-left corner glows green when the dash is ready. Score for
time survived, near misses and daring dashes through a rock.
"""
import math

from arcade.engine import (A, CYAN, DOWN, GREEN, LEFT, N, ORANGE, PEACH, RED, RIGHT,
                           UP, WHITE, YELLOW, dim)

BAND_TOP = 9
SPEED_X = 15.0
SPEED_Y = 11.0
DASH_TIME = 0.12
DASH_SPEED = 55.0
INVULN = 0.45
COOLDOWN = 1.6
# (width, height, min speed, max speed, colour)
KINDS = [(1, 1, 11, 16, YELLOW), (2, 2, 6, 10, ORANGE), (3, 2, 4, 6.5, RED)]


class Dodge:
    name = "Dodge"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        c.rect(3, 1, 3, 2, RED)
        c.rect(9, 4, 2, 2, ORANGE)
        c.set(13, 2, YELLOW)
        c.set(5, 7, YELLOW)
        c.rect(1, 6, 2, 2, ORANGE)
        c.set(7, 9, dim(WHITE, 0.4))
        c.set(7, 10, dim(WHITE, 0.4))
        c.set(7, 13, WHITE)
        c.rect(10, 13, 3, 1, dim(CYAN, 0.5))
        c.set(0, 15, GREEN)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.t = 0.0
        self.x, self.y = 7.5, 14.0
        self.face = (1, 0)
        self.dash_t = 0.0
        self.dash_dir = (1, 0)
        self.inv = 0.0
        self.cool = 0.0
        self.rocks = []  # [x, y, w, h, vy, colour, near, passed]
        self.spawn_t = 0.8
        self.bonus = 0
        self.level = 0
        self.flash = 0.0
        self.tick_cd = 0.0
        self.last_cell = (7, 14)
        ctx.music("chase")

    def die(self):
        self.dying = 0.8
        self.ctx.sfx("explode")
        self.ctx.sfx("die")
        self.ctx.music(None)

    def spawn(self):
        rng = self.rng
        weights = [4, 3 + self.t / 20, max(0.0, self.t / 12 - 0.5)]
        w, h, lo, hi, colour = rng.choices(KINDS, weights)[0]
        scale = 1 + min(0.6, self.t * 0.008)
        x = round(self.x) - rng.randint(0, w) if rng.random() < 0.4 else rng.randint(0, N - w)
        self.rocks.append([max(0, min(N - w, x)), -float(h), w, h, rng.uniform(lo, hi) * scale, colour, False, False])

    def move(self, dx, dy, speed_x, speed_y, dt):
        self.x = max(0.0, min(N - 1.0, self.x + dx * speed_x * dt))
        self.y = max(float(BAND_TOP), min(N - 1.0, self.y + dy * speed_y * dt))

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2)
        self.inv = max(0.0, self.inv - dt)
        self.cool = max(0.0, self.cool - dt)
        self.tick_cd = max(0.0, self.tick_cd - dt)

        dx = inp.held(RIGHT) - inp.held(LEFT)
        dy = inp.held(DOWN) - inp.held(UP)
        if dx or dy:
            self.face = (dx or self.face[0], dy)
        if inp.pressed(A) and self.cool == 0:
            d = (dx, dy) if (dx or dy) else (self.face[0], 0)
            n = math.hypot(*d)
            self.dash_dir = (d[0] / n, d[1] / n)
            self.dash_t = DASH_TIME
            self.inv = INVULN
            self.cool = COOLDOWN
            self.ctx.sfx("power")
        elif inp.pressed(A):
            self.ctx.sfx("bounce")  # not ready yet
        if self.dash_t > 0:
            self.dash_t -= dt
            self.move(*self.dash_dir, DASH_SPEED, DASH_SPEED, dt)
        else:
            self.move(dx, dy, SPEED_X, SPEED_Y, dt)
        cell = (int(round(self.x)), int(round(self.y)))
        if cell != self.last_cell:
            self.last_cell = cell
            if self.tick_cd == 0:
                self.ctx.sfx("tick")
                self.tick_cd = 0.09

        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn()
            self.spawn_t = max(0.12, 0.55 - self.t * 0.006) * self.rng.uniform(0.6, 1.3)
        for r in self.rocks:
            r[1] += r[4] * dt
        self.rocks = [r for r in self.rocks if r[1] < N]

        level = int(self.t // 10)
        if level > self.level:
            self.level = level
            self.flash = 1.0
            self.ctx.sfx("level")

        px, py = cell
        for r in self.rocks:
            rx, ry, w, h = int(r[0]), int(round(r[1])), r[2], r[3]
            gx = max(rx - px, 0, px - (rx + w - 1))
            gy = max(ry - py, 0, py - (ry + h - 1))
            if gx == 0 and gy == 0:
                if self.inv > 0:
                    if not r[7]:
                        r[7] = True
                        self.bonus += 5
                        self.ctx.sfx("coin")
                else:
                    self.die()
                    return
            elif max(gx, gy) <= 2 and not r[6]:
                r[6] = True
                self.bonus += 1
                self.ctx.sfx("near")
        self.score = int(self.t * 1.5) + self.bonus

    def draw(self, c):
        c.clear(dim(ORANGE, 0.3 * self.flash) if self.flash else (0, 0, 0))
        for x, y, w, h, vy, colour, _, _ in self.rocks:
            ry = int(round(y))
            c.rect(int(x), ry, w, h, colour)
            if vy > 10:  # fast ones leave a streak
                c.set(int(x), ry - 1, dim(colour, 0.4))
        px, py = int(round(self.x)), int(round(self.y))
        if self.dying:
            if int(self.dying * 14) % 2:
                c.rect(px - 1, py - 1, 3, 3, WHITE)
        else:
            if self.dash_t > 0 or self.inv > 0:
                c.set(px - self.dash_dir[0] * 1.4, py - self.dash_dir[1] * 1.4, dim(CYAN, 0.5))
            c.set(px, py, CYAN if self.inv > 0 and int(self.t * 20) % 2 else WHITE)
        if self.cool == 0:
            c.set(0, 15, GREEN)
        else:
            c.set(0, 15, dim(RED, 0.2 + 0.5 * (1 - self.cool / COOLDOWN)))


GAMES = [Dodge]
