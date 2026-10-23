"""Invaders: rows of aliens march and drop; slide, shoot, survive the bombs.

Aliens are two pixels wide. They speed up as the formation thins out, and
each wave starts lower, faster and with another row. Two shots may be in
flight at once; a purple UFO crosses the top now and then for a bonus.
"""
from arcade.engine import (A, CYAN, GREEN, LEFT, N, ORANGE, PEACH, PINK, PURPLE, RED,
                           RIGHT, WHITE, YELLOW, dim)

COLS = 4
SPACING_X = 3
ROW_COLOURS = [PINK, YELLOW, GREEN, CYAN, PEACH]
PLAYER_Y = 15
SHOT_SPEED = 28.0


class Invaders:
    name = "Invaders"
    colour = GREEN

    @classmethod
    def icon(cls, c):
        for r, col in enumerate((PINK, YELLOW, GREEN)):
            for k in range(3):
                c.rect(2 + k * 4, 3 + r * 3, 2, 1, col)
                c.set(2 + k * 4 + (r % 2), 4 + r * 3, col)
        c.rect(6, 14, 3, 1, ORANGE)
        c.set(7, 13, ORANGE)
        c.set(7, 11, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.dying = 0.0
        self.wave = 0
        self.px = 7
        self.rep = 0.0
        self.shots = []   # [x, y]
        self.bombs = []   # [x, y, near_flagged]
        self.ufo = None   # [x, dir, points]
        self.ufo_in = self.rng.uniform(8, 14)
        self.flash = 0.0
        self.pause = 0.0
        self.fire_cd = 0.0
        self.sparks = []
        self.new_wave()
        ctx.music("chase")

    def new_wave(self):
        self.wave += 1
        self.rows = min(2 + self.wave, 5)
        self.alive = [[True] * COLS for _ in range(self.rows)]
        self.total = self.rows * COLS
        self.ox = 2
        self.oy = 1 + min(self.wave - 1, 2)
        self.dir = 1
        self.step_t = 0.0
        self.bomb_t = 1.0
        self.shots, self.bombs = [], []
        self.flash = 1.0 if self.wave > 1 else 0.0

    def count(self):
        return sum(row.count(True) for row in self.alive)

    def alien_pos(self, r, c):
        return self.ox + c * SPACING_X, self.oy + r * 2

    def aliens(self):
        for r, row in enumerate(self.alive):
            for c, a in enumerate(row):
                if a:
                    yield r, c, *self.alien_pos(r, c)

    def interval(self):
        base = max(0.3, 0.55 - 0.04 * (self.wave - 1))
        return 0.05 + (base - 0.05) * self.count() / self.total

    def die(self):
        self.dying = 0.9
        self.ctx.sfx("explode")
        self.ctx.sfx("die")
        self.ctx.music(None)
        self.sparks = [(self.px + self.rng.uniform(-1, 1), PLAYER_Y - 1,
                        self.rng.uniform(-6, 6), self.rng.uniform(-9, -2)) for _ in range(10)]

    def move_player(self, inp, dt):
        d = inp.held(RIGHT) - inp.held(LEFT)
        if inp.pressed(LEFT) or inp.pressed(RIGHT):
            d = inp.pressed(RIGHT) - inp.pressed(LEFT) or d
            self.px = max(1, min(N - 2, self.px + d))
            self.rep = 0.13
            self.ctx.sfx("move")
        elif d:
            self.rep -= dt
            while self.rep <= 0:
                nx = max(1, min(N - 2, self.px + d))
                if nx != self.px:
                    self.px = nx
                    self.ctx.sfx("tick")
                self.rep += 0.045
        else:
            self.rep = 0.0

    def hit_alien(self, x, y):
        for r, c, ax, ay in self.aliens():
            if y == ay and ax <= x < ax + 2:
                self.alive[r][c] = False
                self.score += 10 + 5 * (self.rows - 1 - r)
                self.ctx.sfx("explode")
                return True
        return False

    def update(self, inp, dt):
        if self.dying:
            self.dying -= dt
            self.sparks = [(x + vx * dt, y + vy * dt, vx, vy + 25 * dt) for x, y, vx, vy in self.sparks]
            if self.dying <= 0:
                self.over = True
            return
        self.flash = max(0.0, self.flash - dt * 2)
        self.fire_cd = max(0.0, self.fire_cd - dt)
        self.move_player(inp, dt)

        if inp.pressed(A) and len(self.shots) < 2 and self.fire_cd == 0:
            self.shots.append([self.px, PLAYER_Y - 2.0])
            self.fire_cd = 0.12
            self.ctx.sfx("shoot")

        # Shots sweep every row they cross so a fast shot can't skip an alien.
        for s in self.shots:
            y0, s[1] = s[1], s[1] - SHOT_SPEED * dt
            for row in range(int(round(y0)), int(round(s[1])) - 1, -1):
                if self.ufo and row == 0 and self.ufo[0] <= s[0] < self.ufo[0] + 2:
                    self.score += self.ufo[2]
                    self.ufo = None
                    self.ctx.sfx("power")
                    s[1] = -9
                    break
                if self.hit_alien(s[0], row):
                    s[1] = -9
                    break
        self.shots = [s for s in self.shots if s[1] >= 0]

        if self.pause > 0:
            self.pause -= dt
            if self.pause <= 0:
                self.new_wave()
            return
        if self.count() == 0:
            self.pause = 0.9
            self.flash = 1.0
            self.bombs = []
            self.ctx.sfx("level")
            return

        self.step_t += dt
        if self.step_t >= self.interval():
            self.step_t = 0.0
            xs = [x for _, _, x, _ in self.aliens()]
            if (self.dir > 0 and max(xs) + 1 >= N - 1) or (self.dir < 0 and min(xs) <= 0):
                self.oy += 1
                self.dir = -self.dir
                self.ctx.sfx("turn")
            else:
                self.ox += self.dir
                self.ctx.sfx("tick")
        if any(y >= PLAYER_Y - 1 for _, _, _, y in self.aliens()):
            self.die()
            return

        self.bomb_t -= dt
        if self.bomb_t <= 0:
            self.bomb_t = max(0.3, 1.3 - 0.1 * self.wave - (1 - self.count() / self.total) * 0.5) * self.rng.uniform(0.6, 1.4)
            if len(self.bombs) < 2 + self.wave:
                lowest = {}
                for r, c, x, y in self.aliens():
                    lowest[c] = (x, y)
                x, y = self.rng.choice(list(lowest.values()))
                self.bombs.append([x + self.rng.randint(0, 1), y + 1.0, False])
                self.ctx.sfx("laser")

        speed = 6 + self.wave * 0.8
        for b in self.bombs:
            b[1] += speed * dt
            by = int(round(b[1]))
            for s in self.shots:
                if s[0] == b[0] and abs(s[1] - b[1]) < 1.2:
                    s[1], b[1] = -9, 99
                    self.score += 2
                    self.ctx.sfx("hit")
            if by == PLAYER_Y and abs(b[0] - self.px) <= 1 or by == PLAYER_Y - 1 and b[0] == self.px:
                self.die()
                return
            if by >= PLAYER_Y - 1 and not b[2] and abs(b[0] - self.px) == 2:
                b[2] = True
                self.score += 1
                self.ctx.sfx("near")
        self.shots = [s for s in self.shots if s[1] >= 0]
        self.bombs = [b for b in self.bombs if b[1] < N]

        self.ufo_in -= dt
        if self.ufo is None and self.ufo_in <= 0:
            left = self.rng.random() < 0.5
            self.ufo = [-2.0 if left else float(N), 1 if left else -1, self.rng.choice((50, 100, 150))]
            self.ufo_in = self.rng.uniform(10, 18)
            self.ctx.sfx("power")
        if self.ufo:
            self.ufo[0] += self.ufo[1] * 5.5 * dt
            if self.ufo[0] < -3 or self.ufo[0] > N + 1:
                self.ufo = None

    def draw(self, c):
        c.clear(dim(ORANGE, 0.25 * self.flash) if self.flash else (0, 0, 0))
        for r, col, x, y in self.aliens():
            colour = ROW_COLOURS[r]
            c.rect(x, y, 2, 1, colour)
            c.set(x + (self.ox + y) % 2, y + 1, dim(colour, 0.5))  # legs wiggle
        for x, y, _ in self.bombs:
            c.set(x, y, RED)
        for x, y in self.shots:
            c.set(x, y, WHITE)
        if self.ufo:
            c.rect(int(round(self.ufo[0])), 0, 2, 1, PURPLE)
        if self.dying:
            for x, y, _, _ in self.sparks:
                c.set(x, y, WHITE if int(self.dying * 12) % 2 else ORANGE)
            return
        c.rect(self.px - 1, PLAYER_Y, 3, 1, ORANGE)
        c.set(self.px, PLAYER_Y - 1, WHITE)


GAMES = [Invaders]
