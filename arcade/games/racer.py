"""Racer: top-down road, four lanes, weave through traffic.

LEFT and RIGHT change lane instantly. Traffic comes in rows that always leave
one lane open; rows come closer together and the road scrolls faster as you go.
Yellow pickups are bonus points, and brushing past a car in the next lane is a
near miss.
"""
from arcade.engine import (BLUE, CYAN, GREY, LEFT, ORANGE, PEACH, PINK, PURPLE, RIGHT,
                           WHITE, YELLOW, dim)

LANES = 4
CAR_H = 3
PLAYER_Y = 12
TRAFFIC = [BLUE, CYAN, PURPLE, PINK, (40, 200, 60)]


def lane_x(lane):
    return 2 + 3 * lane


class Racer:
    name = "Racer"
    colour = ORANGE

    @classmethod
    def icon(cls, c):
        c.rect(1, 0, 1, 16, WHITE)
        c.rect(14, 0, 1, 16, WHITE)
        for y in (1, 5, 9, 13):
            c.rect(7, y, 1, 2, GREY)
            c.rect(4, y, 1, 2, GREY)
            c.rect(10, y, 1, 2, GREY)
        c.rect(5, 2, 2, 3, BLUE)
        c.rect(11, 5, 2, 3, PURPLE)
        c.rect(8, 11, 2, 3, ORANGE)
        c.rect(8, 12, 2, 1, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.t = 0.0
        self.lane = 1
        self.cars = []   # [lane, y, colour, near_flagged]
        self.coins = []  # [lane, y]
        self.since = 99.0
        self.coin_at = None
        self.last_free = 1
        self.distance = 0.0
        self.bonus = 0
        self.scroll = 0.0
        self.level = 0
        self.flash = 0.0
        self.dies_at = 0
        ctx.music("chase")

    @property
    def speed(self):
        return 7.0 + min(10.0, self.t * 0.13)

    def spawn_row(self):
        rng = self.rng
        reach = 3 if self.t < 15 else 2
        free = rng.choice([l for l in range(LANES) if abs(l - self.last_free) <= reach])
        n = 1 if self.t < 8 else rng.choice((1, 2)) if self.t < 25 else rng.choice((2, 2, 3))
        others = [l for l in range(LANES) if l != free]
        for lane in rng.sample(others, n):
            self.cars.append([lane, -float(CAR_H), rng.choice(TRAFFIC), False])
        self.last_free = free
        if rng.random() < 0.35:
            self.coin_at = self.gap() / 2

    def gap(self):
        return max(5.5, 10 - self.t * 0.07)

    def die(self):
        self.dying = 0.8
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
        new = self.lane + (inp.pressed(RIGHT) - inp.pressed(LEFT))
        new = max(0, min(LANES - 1, new))
        if new != self.lane:
            self.lane = new
            self.ctx.sfx("turn")

        step = self.speed * dt
        self.distance += step
        self.scroll += step
        self.since += step
        for car in self.cars:
            car[1] += step
        for coin in self.coins:
            coin[1] += step
        self.cars = [c for c in self.cars if c[1] < 16]
        self.coins = [c for c in self.coins if c[1] < 16]
        if self.since >= self.gap():
            self.since = 0.0
            self.spawn_row()
        if self.coin_at is not None and self.since >= self.coin_at:
            self.coins.append([self.last_free, -1.0])
            self.coin_at = None
        self.score = int(self.distance / 4) + self.bonus

        level = int(self.t // 12)
        if level > self.level:
            self.level = level
            self.flash = 1.0
            self.ctx.sfx("level")

        for car in self.cars:
            y = int(round(car[1]))
            if y + CAR_H <= PLAYER_Y or y >= PLAYER_Y + CAR_H:
                continue
            if car[0] == self.lane:
                self.die()
                return
            if abs(car[0] - self.lane) == 1 and not car[3]:
                car[3] = True
                self.bonus += 2
                self.ctx.sfx("near")
        for coin in self.coins[:]:
            y = int(round(coin[1]))
            if coin[0] == self.lane and PLAYER_Y - 1 <= y < PLAYER_Y + CAR_H:
                self.coins.remove(coin)
                self.bonus += 10
                self.ctx.sfx("coin")

    def draw(self, c):
        c.clear(dim(ORANGE, 0.25 * self.flash) if self.flash else (0, 0, 0))
        off = int(self.scroll) % 4
        for y in range(16):
            dash = (y - off) % 4 < 2
            c.set(1, y, WHITE if dash else GREY)
            c.set(14, y, WHITE if dash else GREY)
            if dash:
                for x in (4, 7, 10):
                    c.set(x, y, dim(GREY, 0.8))
        for lane, y in self.coins:
            c.rect(lane_x(lane), int(round(y)), 2, 1, YELLOW if int(self.t * 8) % 2 else PEACH)
        for lane, y, colour, _ in self.cars:
            ry = int(round(y))
            c.rect(lane_x(lane), ry, 2, CAR_H, colour)
            c.rect(lane_x(lane), ry + 1, 2, 1, dim(colour, 0.45))
        x = lane_x(self.lane)
        if self.dying:
            if int(self.dying * 14) % 2:
                c.rect(x - 1, PLAYER_Y - 1, 4, 5, WHITE)
            return
        c.rect(x, PLAYER_Y, 2, CAR_H, ORANGE)
        c.rect(x, PLAYER_Y + 1, 2, 1, WHITE)


GAMES = [Racer]
