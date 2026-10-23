"""Asteroids: a ship in the middle of a wrap-around sky full of rocks.

LEFT/RIGHT turn the nose through eight directions, UP thrusts, A fires. A
2x2 rock splits into two 1x1 rocks, which die to one shot. Each wave brings
more and faster rocks; three lives, and a short shield after each respawn.
"""
import math

from arcade.engine import (A, CYAN, EMBER, LEFT, N, ORANGE, PEACH, RED, RIGHT, UP,
                           WHITE, YELLOW, dim)

DIRS = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
NORM = [(dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)) for dx, dy in DIRS]
MAX_BULLETS = 4


class Rock:
    def __init__(self, x, y, vx, vy, size):
        self.x, self.y, self.vx, self.vy, self.size = x, y, vx, vy, size

    def cells(self):
        x, y = int(math.floor(self.x)), int(math.floor(self.y))
        return {((x + i) % N, (y + j) % N) for i in range(self.size) for j in range(self.size)}

    def covers(self, px, py):
        return (int(round(px)) % N, int(round(py)) % N) in self.cells()


class Asteroids:
    name = "Asteroids"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        c.rect(2, 2, 2, 2, PEACH)
        c.rect(11, 3, 2, 2, PEACH)
        c.rect(3, 11, 2, 2, PEACH)
        c.set(12, 11, PEACH)
        c.set(13, 9, PEACH)
        c.set(7, 7, WHITE)
        c.set(8, 6, ORANGE)
        c.set(6, 8, ORANGE)
        c.set(7, 8, ORANGE)
        for i in range(3):
            c.set(9 + i, 5 - i, dim(CYAN, 1 - i * 0.3))

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.lives = 3
        self.wave = 0
        self.flash = 0.0
        self.dying = 0.0
        self.final = False
        self.wave_wait = 0.0
        self.rocks, self.bullets, self.debris = [], [], []
        self.respawn()
        self.spawn_wave()
        ctx.music("chase")

    def respawn(self):
        self.x, self.y = 7.5, 7.5
        self.vx = self.vy = 0.0
        self.heading = 0
        self.shield = 2.0
        self.cool = 0.0
        self.turn_hold = 0.0
        self.thrusting = False

    def spawn_wave(self):
        self.wave += 1
        n = min(8, 2 + self.wave)
        speed = min(5.0, 1.6 + 0.35 * self.wave)
        for _ in range(n):
            while True:
                x, y = self.rng.uniform(0, N), self.rng.uniform(0, N)
                if math.hypot(x - self.x, y - self.y) > 5:
                    break
            a = self.rng.uniform(0, 2 * math.pi)
            s = speed * self.rng.uniform(0.7, 1.2)
            self.rocks.append(Rock(x, y, math.cos(a) * s, math.sin(a) * s, 2))

    def fire(self):
        if len(self.bullets) >= MAX_BULLETS:
            return
        nx, ny = NORM[self.heading]
        self.bullets.append([self.x + nx, self.y + ny, nx * 22 + self.vx, ny * 22 + self.vy, 0.65])
        self.cool = 0.22
        self.ctx.sfx("shoot")

    def burst(self, x, y, n, colour):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            s = self.rng.uniform(3, 9)
            self.debris.append([x, y, math.cos(a) * s, math.sin(a) * s, 0.5, colour])

    def hit_rock(self, rock):
        self.rocks.remove(rock)
        self.burst(rock.x + rock.size / 2, rock.y + rock.size / 2, 5, PEACH)
        if rock.size == 2:
            self.score += 20
            self.ctx.sfx("hit")
            for sgn in (1, -1):
                a = math.atan2(rock.vy, rock.vx) + sgn * self.rng.uniform(0.6, 1.2)
                s = math.hypot(rock.vx, rock.vy) * 1.4 + 1
                self.rocks.append(Rock(rock.x + 0.5, rock.y + 0.5, math.cos(a) * s, math.sin(a) * s, 1))
        else:
            self.score += 10
            self.ctx.sfx("explode")

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 2)
        for r in self.rocks:
            r.x = (r.x + r.vx * dt) % N
            r.y = (r.y + r.vy * dt) % N
        for d in self.debris:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[4] -= dt
        self.debris = [d for d in self.debris if d[4] > 0]

        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                if self.final:
                    self.over = True
                else:
                    self.dying = 0.0
                    self.respawn()
            return

        # Turning: instant on press, then repeats while held.
        turn = (inp.pressed(RIGHT) or 0) - (inp.pressed(LEFT) or 0)
        if inp.held(LEFT) or inp.held(RIGHT):
            self.turn_hold += dt
            if self.turn_hold > 0.18:
                self.turn_hold -= 0.07
                turn = inp.held(RIGHT) - inp.held(LEFT)
        else:
            self.turn_hold = 0.0
        if turn:
            self.heading = (self.heading + (1 if turn > 0 else -1)) % 8
            self.ctx.sfx("turn")

        self.thrusting = inp.held(UP)
        if self.thrusting:
            nx, ny = NORM[self.heading]
            self.vx += nx * 22 * dt
            self.vy += ny * 22 * dt
            sp = math.hypot(self.vx, self.vy)
            if sp > 12:
                self.vx, self.vy = self.vx * 12 / sp, self.vy * 12 / sp
            if inp.pressed(UP):
                self.ctx.sfx("flap")
        drag = 0.5 ** dt  # halves speed every second
        self.vx *= drag
        self.vy *= drag
        self.x = (self.x + self.vx * dt) % N
        self.y = (self.y + self.vy * dt) % N

        self.cool -= dt
        if inp.pressed(A) or (inp.held(A) and self.cool <= 0):
            if self.cool <= 0 or inp.pressed(A):
                self.fire()

        self.shield = max(0.0, self.shield - dt)

        for b in self.bullets:
            b[0] = (b[0] + b[2] * dt) % N
            b[1] = (b[1] + b[3] * dt) % N
            b[4] -= dt
            for r in self.rocks:
                if r.covers(b[0], b[1]) or r.covers(b[0] - b[2] * dt / 2, b[1] - b[3] * dt / 2):
                    b[4] = 0
                    self.hit_rock(r)
                    break
        self.bullets = [b for b in self.bullets if b[4] > 0]

        if not self.shield:
            for r in self.rocks:
                if r.covers(self.x, self.y):
                    self.lives -= 1
                    self.burst(self.x, self.y, 14, WHITE)
                    self.flash = 1.0
                    self.ctx.sfx("explode")
                    self.final = self.lives <= 0
                    self.dying = 1.0 if self.final else 0.8
                    if self.final:
                        self.ctx.sfx("die")
                        self.ctx.music(None)
                    return

        if not self.rocks:
            if not self.wave_wait:
                self.wave_wait = 1.0
                self.flash = 1.0
                self.ctx.sfx("level")
            self.wave_wait -= dt
            if self.wave_wait <= 0:
                self.wave_wait = 0.0
                self.spawn_wave()

    def draw(self, c):
        if self.flash:
            c.rect(0, 0, N, N, dim(ORANGE, 0.25 * self.flash))
        for r in self.rocks:
            for cx, cy in r.cells():
                c.set(cx, cy, PEACH)
        for b in self.bullets:
            c.set(b[0], b[1], CYAN)
        for d in self.debris:
            c.set(d[0], d[1], dim(d[5], d[4] * 2))
        if not self.dying and (not self.shield or int(self.shield * 10) % 2 == 0):
            nx, ny = DIRS[self.heading]
            c.set(self.x, self.y, WHITE)
            c.set(self.x + nx, self.y + ny, ORANGE)
            if self.thrusting:
                c.set(self.x - nx, self.y - ny, YELLOW)
        for i in range(self.lives):
            c.set(i, N - 1, RED)


GAMES = [Asteroids]
