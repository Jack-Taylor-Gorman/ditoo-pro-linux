"""Minesweeper on the full 16x16 screen, numbers shown as colours.

A reveals, B flags (or unflags). A on a revealed number whose flags already
match it reveals the rest of its neighbours. Zeros flood open. The first
reveal is always safe. Clear the board for a bigger minefield; hit a mine
and it's over. Score is the safe cells cleared in total.

Colours: 1 blue, 2 green, 3 red, 4 purple, 5 yellow, 6 cyan, 7 pink, 8 white.
"""
import math

from arcade.engine import (A, B, BLUE, CYAN, DOWN, GREEN, GREY, LEFT, N, ORANGE, PINK,
                           PURPLE, RED, RIGHT, UP, WHITE, YELLOW, dim)

NUMBERS = [None, BLUE, GREEN, RED, PURPLE, YELLOW, CYAN, PINK, WHITE]
HIDDEN = (60, 60, 70)
START_MINES = 40


def neighbours(x, y):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < N and 0 <= y + dy < N:
                yield x + dx, y + dy


class Minesweep:
    name = "Minesweep"
    colour = BLUE

    @classmethod
    def icon(cls, c):
        c.rect(2, 2, 12, 12, HIDDEN)
        c.rect(3, 3, 4, 4, (0, 0, 0))
        c.set(7, 3, BLUE)
        c.set(7, 4, GREEN)
        c.set(7, 5, BLUE)
        c.set(3, 7, BLUE)
        c.set(4, 7, RED)
        c.set(5, 7, BLUE)
        c.rect(9, 9, 3, 3, RED)
        c.set(10, 10, WHITE)
        c.set(12, 4, ORANGE)
        c.set(11, 3, ORANGE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.score = 0
        self.over = False
        self.wins = 0
        self.cx = self.cy = 8
        self.t = 0.0
        self.hold = {}
        self.anim = None  # ("win"|"lose", seconds elapsed, origin)
        self.flash = 0.0
        self.new_board()
        ctx.music("puzzle")

    @property
    def mines(self):
        return min(70, START_MINES + 8 * self.wins)

    def new_board(self):
        self.mine = [[False] * N for _ in range(N)]
        self.shown = [[False] * N for _ in range(N)]
        self.flag = [[False] * N for _ in range(N)]
        self.count = [[0] * N for _ in range(N)]
        self.placed = False
        self.anim = None

    def place_mines(self, sx, sy):
        safe = {(sx, sy), *neighbours(sx, sy)}
        cells = [(x, y) for y in range(N) for x in range(N) if (x, y) not in safe]
        for x, y in self.rng.sample(cells, min(self.mines, len(cells))):
            self.mine[y][x] = True
        for y in range(N):
            for x in range(N):
                self.count[y][x] = sum(self.mine[ny][nx] for nx, ny in neighbours(x, y))
        self.placed = True

    def reveal(self, x, y):
        """Open a cell (flood on zero). Returns cells opened, or -1 on a mine."""
        if self.shown[y][x] or self.flag[y][x]:
            return 0
        if self.mine[y][x]:
            return -1
        opened, stack = 0, [(x, y)]
        while stack:
            px, py = stack.pop()
            if self.shown[py][px] or self.flag[py][px] or self.mine[py][px]:
                continue
            self.shown[py][px] = True
            opened += 1
            if self.count[py][px] == 0:
                stack.extend(neighbours(px, py))
        return opened

    def lose(self, x, y):
        self.anim = ("lose", 0.0, (x, y))
        self.ctx.sfx("explode")
        self.ctx.music(None)

    def cleared(self):
        return all(self.shown[y][x] or self.mine[y][x] for y in range(N) for x in range(N))

    def after_open(self, n, x, y):
        if n < 0:
            self.lose(x, y)
            return
        if n == 0:
            self.ctx.sfx("hit")  # nothing happened: already open or flagged
            return
        self.score += n
        self.ctx.sfx("eat" if n == 1 else "power" if n > 12 else "coin")
        if self.cleared():
            self.anim = ("win", 0.0, (x, y))
            self.ctx.sfx("level")
            self.ctx.sfx("record")

    def update(self, inp, dt):
        self.t += dt
        if self.anim:
            kind, el, origin = self.anim
            self.anim = (kind, el + dt, origin)
            if el + dt >= (0.9 if kind == "lose" else 0.8):
                if kind == "lose":
                    self.over = True
                else:
                    self.wins += 1
                    self.new_board()
                    self.flash = 1.0
            return
        self.flash = max(0.0, self.flash - dt * 2)

        # Cursor: instant move on press, then auto-repeat while held.
        for b, (dx, dy) in {LEFT: (-1, 0), RIGHT: (1, 0), UP: (0, -1), DOWN: (0, 1)}.items():
            moved = False
            if inp.pressed(b):
                self.hold[b] = 0.0
                moved = True
            elif inp.held(b) and b in self.hold:
                self.hold[b] += dt
                if self.hold[b] > 0.22:
                    self.hold[b] -= 0.07
                    moved = True
            else:
                self.hold.pop(b, None)
            if moved:
                nx, ny = self.cx + dx, self.cy + dy
                if 0 <= nx < N and 0 <= ny < N:
                    self.cx, self.cy = nx, ny
                    self.ctx.sfx("move")
                else:
                    self.ctx.sfx("tick")

        x, y = self.cx, self.cy
        if inp.pressed(B):
            if not self.shown[y][x]:
                self.flag[y][x] = not self.flag[y][x]
                self.ctx.sfx("select" if self.flag[y][x] else "turn")
            else:
                self.ctx.sfx("hit")
        elif inp.pressed(A):
            if not self.placed:
                self.place_mines(x, y)
            if self.shown[y][x]:
                around = list(neighbours(x, y))
                if self.count[y][x] and sum(self.flag[ny][nx] for nx, ny in around) == self.count[y][x]:
                    total = 0
                    for nx, ny in around:
                        n = self.reveal(nx, ny)
                        if n < 0:
                            self.lose(nx, ny)
                            return
                        total += n
                    self.after_open(total, x, y)
                else:
                    self.ctx.sfx("hit")
            else:
                self.after_open(self.reveal(x, y), x, y)

    def cell_colour(self, x, y):
        if self.shown[y][x]:
            n = self.count[y][x]
            return NUMBERS[n] if n else (0, 0, 0)
        return ORANGE if self.flag[y][x] else HIDDEN

    def draw(self, c):
        el = self.anim[1] if self.anim else 0.0
        kind = self.anim[0] if self.anim else None
        ox, oy = self.anim[2] if self.anim else (0, 0)
        for y in range(N):
            for x in range(N):
                col = self.cell_colour(x, y)
                if kind == "lose":
                    if math.hypot(x - ox, y - oy) < el * 28 and self.mine[y][x]:
                        col = RED if int(el * 12) % 2 else ORANGE
                elif kind == "win":
                    # Rainbow wave rolling out from the last click.
                    d = math.hypot(x - ox, y - oy) / 22
                    if d < el / 0.8:
                        col = [GREEN, CYAN, YELLOW, PINK][(x + y + int(el * 20)) % 4]
                elif self.flash:
                    col = tuple(max(a, int(255 * self.flash * 0.4)) for a in col)
                c.set(x, y, col)
        if not self.anim and int(self.t * 4) % 2 == 0:
            c.set(self.cx, self.cy, WHITE)
        elif not self.anim:
            c.set(self.cx, self.cy, dim(self.cell_colour(self.cx, self.cy), 0.5) if self.shown[self.cy][self.cx] else (140, 140, 160))


GAMES = [Minesweep]
