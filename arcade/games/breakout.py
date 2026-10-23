"""Breakout: bounce the ball off the paddle and clear the wall.

A launches the ball. Where it meets the paddle sets the angle. The ball speeds
up each time a whole brick row is cleared. A cleared wall is replaced by a
tougher one: from level 2 the top rows take two hits (white, then their own
colour). Three lives, shown as dots in the top-left corner.
"""
import math

from arcade.engine import (A, CYAN, EMBER, GREEN, LEFT, N, ORANGE, RED,
                           RIGHT, WHITE, YELLOW, dim)

ROW_COLOURS = [RED, ORANGE, YELLOW, GREEN, CYAN]
TOP = 2  # first brick row
PADDLE_Y = 15
PADDLE_SPEED = 24.0
DEATH_TIME = 0.8


class Breakout:
    name = "Breakout"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        for row, col in enumerate(ROW_COLOURS[:4]):
            for x in range(2, 14):
                if (x + row) % 6:
                    c.set(x, 2 + row, col)
        c.set(9, 9, WHITE)
        c.set(8, 10, EMBER)
        c.rect(5, 13, 5, 1, ORANGE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.flash = 0.0
        self.lives = 3
        self.level = 1
        self.width = 4
        self.px = 6.0
        self.base = 6.5
        self.speed = self.base
        self.new_wall()
        self.reset_ball()
        ctx.music("chase")

    def new_wall(self):
        rows = min(5, 3 + self.level)
        tough = min(rows, self.level - 1)  # top rows take two hits
        self.bricks = {}
        for r in range(rows):
            for x in range(N):
                self.bricks[(x, TOP + r)] = 2 if r < tough else 1
        self.row_open = {TOP + r: N for r in range(rows)}

    def reset_ball(self):
        self.stuck = True
        self.bx, self.by = self.px + self.width / 2, PADDLE_Y - 0.5
        self.vx = self.vy = 0.0

    def launch(self):
        self.stuck = False
        a = self.rng.uniform(-0.35, 0.35)
        self.vx, self.vy = self.speed * math.sin(a), -self.speed * math.cos(a)
        self.ctx.sfx("jump")

    def set_velocity(self, angle):
        self.vx, self.vy = self.speed * math.sin(angle), -self.speed * math.cos(angle)

    def solid(self, x, y):
        cx, cy = int(math.floor(x)), int(math.floor(y))
        return cx < 0 or cx >= N or cy < 0 or (cx, cy) in self.bricks

    def hit_brick(self, x, y):
        cell = (int(math.floor(x)), int(math.floor(y)))
        if cell not in self.bricks:
            self.ctx.sfx("bounce")
            return
        self.bricks[cell] -= 1
        if self.bricks[cell] > 0:
            self.ctx.sfx("hit")
            return
        del self.bricks[cell]
        self.score += self.level
        self.ctx.sfx("coin")
        row = cell[1]
        self.row_open[row] -= 1
        if self.row_open[row] == 0:
            self.speed = min(15.0, self.speed + 0.7)
            self.score += 5 * self.level
            self.flash = 1.0
            self.ctx.sfx("level")

    def step_ball(self, dt):
        dist = math.hypot(self.vx, self.vy) * dt
        n = max(1, int(dist / 0.4) + 1)
        for _ in range(n):
            ox, oy = self.bx, self.by
            self.bx += self.vx * dt / n
            if self.solid(self.bx, self.by):
                self.hit_brick(self.bx, self.by)
                self.bx = ox
                self.vx = -self.vx
            self.by += self.vy * dt / n
            if self.solid(self.bx, self.by):
                self.hit_brick(self.bx, self.by)
                self.by = oy
                self.vy = -self.vy
            pr = round(self.px)
            if self.vy > 0 and oy < PADDLE_Y <= self.by and pr - 0.5 <= self.bx <= pr + self.width + 0.5:
                rel = (self.bx - (pr + self.width / 2)) / (self.width / 2 + 0.5)
                self.by = PADDLE_Y - 0.01
                self.set_velocity(max(-1, min(1, rel)) * 1.15)
                self.ctx.sfx("bounce")
            if not self.bricks:
                return
            if self.by >= N:
                self.lose_ball()
                return
        # Never let the ball go flat; it would take forever to come down.
        if abs(self.vy) < self.speed * 0.25:
            self.vy = math.copysign(self.speed * 0.25, self.vy or -1)

    def lose_ball(self):
        self.lives -= 1
        if self.lives <= 0:
            self.dying = DEATH_TIME
            self.ctx.sfx("explode")
            self.ctx.sfx("die")
            self.ctx.music(None)
        else:
            self.ctx.sfx("hit")
            self.flash = 0.6
            self.speed = max(self.base, self.speed - 0.5)
            self.reset_ball()

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        move = inp.held(RIGHT) - inp.held(LEFT)
        if inp.pressed(LEFT):
            self.px -= 1
            self.ctx.sfx("move")
        if inp.pressed(RIGHT):
            self.px += 1
            self.ctx.sfx("move")
        self.px = max(0.0, min(N - self.width, self.px + move * PADDLE_SPEED * dt))
        if self.stuck:
            self.bx = self.px + self.width / 2
            if inp.pressed(A):
                self.launch()
            return
        self.step_ball(dt)
        if not self.bricks and not self.dying:
            self.level += 1
            self.base = min(10.0, self.base + 0.5)
            self.speed = self.base
            self.flash = 1.0
            self.ctx.sfx("level")
            self.new_wall()
            self.reset_ball()

    def draw(self, c):
        if self.flash:
            c.clear(dim(ORANGE, 0.2 * self.flash))
        if self.dying:
            k = self.dying / DEATH_TIME
            for (x, y), hp in self.bricks.items():
                if self.rng.random() < k:
                    c.set(x, y + int((1 - k) * 6), dim(ROW_COLOURS[(y - TOP) % 5], 0.6))
            if int(k * 14) % 2:
                c.rect(int(round(self.px)), PADDLE_Y, self.width, 1, RED)
            return
        for (x, y), hp in self.bricks.items():
            c.set(x, y, WHITE if hp > 1 else ROW_COLOURS[(y - TOP) % 5])
        c.rect(int(round(self.px)), PADDLE_Y, self.width, 1, ORANGE)
        for i in range(self.lives - 1):
            c.set(i, 0, dim(WHITE, 0.4))
        c.set(math.floor(self.bx), math.floor(self.by), WHITE)


GAMES = [Breakout]
