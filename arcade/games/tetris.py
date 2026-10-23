"""Tetris: a 10x16 well, seven pieces, lines clear, gravity climbs with level.

Left/right have DAS (repeat after 0.17 s, then every 0.05 s), DOWN soft drops,
UP hard drops, A rotates clockwise and B anticlockwise with wall kicks. The
right-hand six columns hold the next piece, the level digit and a progress bar.
"""
from arcade.engine import (A, B, BLUE, CYAN, DOWN, EMBER, GREEN, GREY, LEFT, N, ORANGE,
                           PURPLE, RED, RIGHT, UP, WHITE, YELLOW, dim)

W, H = 10, 16
SHAPES = {  # (box size, cells)
    "I": (4, [(0, 1), (1, 1), (2, 1), (3, 1)]),
    "O": (2, [(0, 0), (1, 0), (0, 1), (1, 1)]),
    "T": (3, [(1, 0), (0, 1), (1, 1), (2, 1)]),
    "S": (3, [(1, 0), (2, 0), (0, 1), (1, 1)]),
    "Z": (3, [(0, 0), (1, 0), (1, 1), (2, 1)]),
    "J": (3, [(0, 0), (0, 1), (1, 1), (2, 1)]),
    "L": (3, [(2, 0), (0, 1), (1, 1), (2, 1)]),
}
COLOURS = {"I": CYAN, "O": YELLOW, "T": PURPLE, "S": GREEN, "Z": RED, "J": BLUE, "L": ORANGE}
KICKS = [(0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0), (-1, -1), (1, -1)]
DAS_FIRST, DAS_REPEAT, LOCK_DELAY, CLEAR_TIME, DEATH_TIME = 0.17, 0.05, 0.5, 0.18, 0.9
LINE_POINTS = [0, 100, 300, 500, 800]


def rotate(cells, n, cw):
    if cw:
        return [(n - 1 - y, x) for x, y in cells]
    return [(y, n - 1 - x) for x, y in cells]


class Tetris:
    name = "Tetris"
    colour = PURPLE

    @classmethod
    def icon(cls, c):
        for x, y, col in [(2, 13, CYAN), (3, 13, CYAN), (4, 13, CYAN), (5, 13, CYAN), (6, 13, RED),
                          (7, 13, RED), (6, 12, RED), (7, 12, YELLOW), (8, 12, YELLOW),
                          (7, 11, YELLOW), (8, 11, YELLOW), (9, 13, GREEN), (10, 13, GREEN),
                          (10, 12, GREEN), (11, 13, GREEN), (9, 12, ORANGE), (11, 12, ORANGE)]:
            c.set(x, y, col)
        for x, y in [(6, 4), (7, 4), (8, 4), (7, 5)]:
            c.set(x, y, PURPLE)
        c.set(7, 4, WHITE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.board = [[None] * W for _ in range(H)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.over = False
        self.dying = 0.0
        self.flash = 0.0
        self.clearing = 0.0
        self.clear_rows = []
        self.das_dir = None
        self.das_t = 0.0
        self.das_first = True
        self.next_kind = self.draw_kind()
        self.spawn()
        ctx.music("puzzle")

    @property
    def level(self):
        return self.lines // 10 + 1

    @property
    def gravity(self):
        return max(0.05, 0.8 * 0.82 ** (self.level - 1))

    def draw_kind(self):
        if not self.bag:
            self.bag = list(SHAPES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        self.kind, self.next_kind = self.next_kind, self.draw_kind()
        n, cells = SHAPES[self.kind]
        self.n, self.cells = n, list(cells)
        self.x, self.y = (W - n) // 2, 0
        self.fall = 0.0
        self.lock = 0.0
        self.resets = 0
        if self.collides(self.cells, self.x, self.y):
            self.dying = DEATH_TIME
            self.ctx.sfx("explode")
            self.ctx.sfx("die")
            self.ctx.music(None)

    def collides(self, cells, ox, oy):
        for cx, cy in cells:
            x, y = ox + cx, oy + cy
            if not (0 <= x < W) or y >= H or (y >= 0 and self.board[y][x]):
                return True
        return False

    def grounded(self):
        return self.collides(self.cells, self.x, self.y + 1)

    def touched(self):
        """A successful move or turn while resting restarts the lock timer."""
        if self.grounded() and self.resets < 15:
            self.lock = 0.0
            self.resets += 1

    def shift(self, d):
        if self.collides(self.cells, self.x + d, self.y):
            return False
        self.x += d
        self.ctx.sfx("move")
        self.touched()
        return True

    def turn(self, cw):
        cells = rotate(self.cells, self.n, cw)
        for kx, ky in KICKS:
            if not self.collides(cells, self.x + kx, self.y + ky):
                self.cells, self.x, self.y = cells, self.x + kx, self.y + ky
                self.ctx.sfx("turn")
                self.touched()
                return
        self.ctx.sfx("tick")  # nowhere to turn

    def ghost_y(self):
        y = self.y
        while not self.collides(self.cells, self.x, y + 1):
            y += 1
        return y

    def hard_drop(self):
        gy = self.ghost_y()
        self.score += gy - self.y
        self.y = gy
        self.ctx.sfx("drop")
        self.lock_piece(quiet=True)

    def lock_piece(self, quiet=False):
        for cx, cy in self.cells:
            if 0 <= self.y + cy < H:
                self.board[self.y + cy][self.x + cx] = COLOURS[self.kind]
        if not quiet:
            self.ctx.sfx("tick")
        rows = [y for y in range(H) if all(self.board[y])]
        if rows:
            self.clear_rows = rows
            self.clearing = CLEAR_TIME
            self.score += LINE_POINTS[len(rows)] * self.level
            self.ctx.sfx("line")
            if len(rows) == 4:
                self.ctx.sfx("power")
        else:
            self.spawn()

    def finish_clear(self):
        before = self.level
        for y in self.clear_rows:
            del self.board[y]
            self.board.insert(0, [None] * W)
        self.lines += len(self.clear_rows)
        self.clear_rows = []
        if self.level > before:
            self.flash = 1.0
            self.ctx.sfx("level")
        self.spawn()

    def handle_das(self, inp, dt):
        for d, b in ((-1, LEFT), (1, RIGHT)):
            if inp.pressed(b):
                self.shift(d)
                self.das_dir, self.das_t, self.das_first = d, 0.0, True
        if self.das_dir is None:
            return
        b = LEFT if self.das_dir < 0 else RIGHT
        if not inp.held(b):
            other = RIGHT if b == LEFT else LEFT
            if inp.held(other):
                self.das_dir, self.das_t, self.das_first = -self.das_dir, 0.0, True
            else:
                self.das_dir = None
            return
        self.das_t += dt
        limit = DAS_FIRST if self.das_first else DAS_REPEAT
        while self.das_t >= limit:
            self.das_t -= limit
            self.das_first = False
            limit = DAS_REPEAT
            if not self.shift(self.das_dir):
                self.das_t = 0.0
                break

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.dying:
            self.dying -= dt
            if self.dying <= 0:
                self.over = True
            return
        if self.clearing:
            self.clearing -= dt
            if self.clearing <= 0:
                self.clearing = 0.0
                self.finish_clear()
            return
        self.handle_das(inp, dt)
        if inp.pressed(A):
            self.turn(True)
        if inp.pressed(B):
            self.turn(False)
        if inp.pressed(UP):
            self.hard_drop()
            return
        soft = inp.held(DOWN)
        if self.grounded():
            self.lock += dt * (6 if soft else 1)
            if self.lock >= LOCK_DELAY:
                self.lock_piece()
            return
        self.fall += dt
        interval = min(self.gravity, 0.04) if soft else self.gravity
        while self.fall >= interval:
            self.fall -= interval
            if self.grounded():
                break
            self.y += 1
            if soft:
                self.score += 1
                self.ctx.sfx("tick")

    def draw(self, c):
        if self.flash:
            c.rect(0, 0, W, H, dim(ORANGE, 0.3 * self.flash))
        for y in range(H):
            for x in range(W):
                if self.board[y][x]:
                    c.set(x, y, self.board[y][x])
        if self.clearing:
            if int(self.clearing * 40) % 2 == 0:
                for y in self.clear_rows:
                    c.rect(0, y, W, 1, WHITE)
        elif self.dying:
            filled = int((1 - self.dying / DEATH_TIME) * H) + 1
            for y in range(H - min(H, filled), H):
                for x in range(W):
                    c.set(x, y, RED if (x + y + int(self.dying * 20)) % 2 else GREY)
        else:
            col = COLOURS[self.kind]
            gy = self.ghost_y()
            for cx, cy in self.cells:
                c.set(self.x + cx, gy + cy, dim(col, 0.3))
            for cx, cy in self.cells:
                c.set(self.x + cx, self.y + cy, col)
        c.rect(10, 0, 1, H, EMBER)
        # Next piece, centred in a 4x2 box.
        cells = SHAPES[self.next_kind][1]
        w = max(x for x, _ in cells) + 1
        h = max(y for _, y in cells) + 1
        ox, oy = 11 + (4 - w) // 2, 1 + (2 - h) // 2
        for cx, cy in cells:
            c.set(ox + cx, oy + cy, COLOURS[self.next_kind])
        c.number(self.level % 10, 12, 6, YELLOW if self.level >= 10 else WHITE)
        for i in range(min(self.level // 10, 5)):
            c.set(11 + i, 12, YELLOW)
        c.rect(11, 15, 4, 1, EMBER)  # progress to the next level
        c.rect(11, 15, 1 + (self.lines % 10) * 3 // 10, 1, ORANGE)


GAMES = [Tetris]
