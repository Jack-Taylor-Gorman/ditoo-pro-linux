"""Snake: eat apples, don't hit the walls or yourself.

Walls kill. Up to two turns are queued so quick double-taps register, and a
turn made late in a tick steps immediately instead of waiting. Every three
apples the snake speeds up; every fifth apple a gold one appears for a few
seconds and is worth five.
"""
from arcade.engine import (DOWN, LEFT, N, ORANGE, PEACH, RED, RIGHT, UP,
                           WHITE, YELLOW, GREY, dim)

DIRS = {LEFT: (-1, 0), RIGHT: (1, 0), UP: (0, -1), DOWN: (0, 1)}
DEATH_TIME = 0.8
GOLD_TIME = 6.0


class Snake:
    name = "Snake"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        path = [(2, 12), (3, 12), (4, 12), (5, 12), (6, 12), (6, 11), (6, 10), (6, 9), (7, 9),
                (8, 9), (9, 9), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5)]
        for x, y in path:
            c.set(x, y, ORANGE)
        c.set(10, 5, WHITE)
        c.set(12, 5, RED)
        c.set(12, 4, YELLOW)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.body = [(7, 8), (6, 8), (5, 8)]  # head first
        self.dir = (1, 0)
        self.queue = []
        self.acc = 0.0
        self.apples = 0
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.flash = 0.0
        self.t = 0.0
        self.gold = None  # [x, y, time left]
        self.apple = self.free_cell()
        ctx.music("chase")

    @property
    def level(self):
        return self.apples // 3

    @property
    def interval(self):
        return max(0.07, 0.20 - 0.012 * self.level)

    def free_cell(self):
        taken = set(self.body)
        if self.gold:
            taken.add((self.gold[0], self.gold[1]))
        cells = [(x, y) for x in range(N) for y in range(N) if (x, y) not in taken]
        return self.rng.choice(cells) if cells else None

    def turn(self, d):
        last = self.queue[-1] if self.queue else self.dir
        if d == last or (d[0] == -last[0] and d[1] == -last[1]):
            return
        if len(self.queue) >= 2:
            return
        self.queue.append(d)
        self.ctx.sfx("turn")
        # A turn late in the tick doesn't wait for the next one.
        if len(self.queue) == 1 and self.acc >= self.interval * 0.5:
            self.step()
            self.acc = 0.0

    def die(self):
        self.dying = DEATH_TIME
        self.ctx.sfx("explode")
        self.ctx.sfx("die")
        self.ctx.music(None)

    def step(self):
        if self.queue:
            self.dir = self.queue.pop(0)
        hx, hy = self.body[0]
        nx, ny = hx + self.dir[0], hy + self.dir[1]
        eating = (nx, ny) == self.apple
        gold = self.gold is not None and (nx, ny) == (self.gold[0], self.gold[1])
        grow = eating or gold
        solid = self.body if grow else self.body[:-1]
        if not (0 <= nx < N and 0 <= ny < N) or (nx, ny) in solid:
            self.die()
            return
        self.body.insert(0, (nx, ny))
        if not grow:
            self.body.pop()
            return
        if eating:
            self.apples += 1
            self.score += 1
            self.ctx.sfx("eat")
            self.apple = self.free_cell()
            if self.apples % 5 == 0 and not self.gold:
                cell = self.free_cell()
                if cell:
                    self.gold = [cell[0], cell[1], GOLD_TIME]
            if self.apples % 3 == 0:
                self.flash = 1.0
                self.ctx.sfx("level")
        else:
            self.score += 5
            self.gold = None
            self.ctx.sfx("coin")
        if self.apple is None:  # board full: you win, effectively
            self.over = True

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 3)
        if self.gold:
            self.gold[2] -= dt
            if self.gold[2] <= 0:
                self.gold = None
        for b, d in DIRS.items():
            if inp.pressed(b):
                self.turn(d)
                if self.dying:
                    return
        self.acc += dt
        while self.acc >= self.interval and not self.dying:
            self.acc -= self.interval
            self.step()

    def draw(self, c):
        if self.flash:
            c.clear(dim(ORANGE, 0.25 * self.flash))
        if self.dying:
            k = self.dying / DEATH_TIME
            if k > 0.5:  # blink, then crumble from the tail
                colour = WHITE if int(k * 14) % 2 else RED
                for x, y in self.body:
                    c.set(x, y, colour)
            else:
                alive = int(len(self.body) * k * 2)
                for i, (x, y) in enumerate(self.body[:alive]):
                    if self.rng.random() < 0.8:
                        c.set(x, y, PEACH if i % 2 else GREY)
            return
        if self.apple:
            c.set(*self.apple, RED)
        if self.gold:
            left = self.gold[2]
            if left > 2 or int(self.t * 10) % 2:
                c.set(self.gold[0], self.gold[1], YELLOW)
        for i, (x, y) in enumerate(self.body):
            c.set(x, y, ORANGE if i else WHITE)


GAMES = [Snake]
