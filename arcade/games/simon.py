"""Simon: watch the lights, then repeat the pattern with the d-pad.

The screen is cut into four wedges that point along the d-pad: UP green,
RIGHT red, DOWN yellow, LEFT blue. Each round adds one step and the playback
gets quicker. One wrong press ends the game; score is the longest sequence
you completed.
"""
from arcade.engine import (BLUE, DOWN, GREEN, LEFT, N, ORANGE, RED, RIGHT, UP, WHITE,
                           YELLOW, dim)

PADS = [UP, RIGHT, DOWN, LEFT]
COLOURS = {UP: GREEN, RIGHT: RED, DOWN: YELLOW, LEFT: BLUE}
# Stand-ins for real tones: four existing effects at different pitches.
TONES = {UP: "tone0", RIGHT: "tone1", DOWN: "tone2", LEFT: "tone3"}  # the toy's own four notes


def wedge(x, y):
    """Which pad owns pixel (x, y); None on the diagonal seams and the centre."""
    dx, dy = x - 7.5, y - 7.5
    if max(abs(dx), abs(dy)) <= 1.5 or abs(dx) == abs(dy):
        return None
    if abs(dy) > abs(dx):
        return UP if dy < 0 else DOWN
    return LEFT if dx < 0 else RIGHT


class Simon:
    name = "Simon"
    colour = YELLOW

    @classmethod
    def icon(cls, c):
        for y in range(N):
            for x in range(N):
                p = wedge(x, y)
                if p:
                    c.set(x, y, COLOURS[p] if p in (UP, LEFT) else dim(COLOURS[p], 0.3))
        c.rect(6, 6, 4, 4, ORANGE)

    def __init__(self, ctx):
        self.ctx = ctx
        self.rng = ctx.rng
        self.seq = []
        self.score = 0
        self.over = False
        self.lit = None
        self.lit_for = 0.0
        self.flash = 0.0
        self.state = "pause"
        self.timer = 0.6
        self.step = 0
        self.fail = 0.0
        self.grow()
        ctx.music("puzzle")

    @property
    def beat(self):
        """Seconds per playback step; shrinks every round, with a floor."""
        return max(0.16, 0.55 - 0.03 * len(self.seq))

    def grow(self):
        self.seq.append(self.rng.choice(PADS))
        self.step = 0

    def light(self, pad, secs):
        self.lit, self.lit_for = pad, secs
        self.ctx.sfx(TONES[pad])

    def update(self, inp, dt):
        self.flash = max(0.0, self.flash - dt * 2)
        self.lit_for -= dt
        if self.lit_for <= 0:
            self.lit = None

        if self.state == "dead":
            self.fail -= dt
            if self.fail <= 0:
                self.over = True
            return

        if self.state == "pause":
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.step, self.timer = "show", 0, 0.0
        elif self.state == "show":
            self.timer -= dt
            if self.timer <= 0:
                if self.step < len(self.seq):
                    self.light(self.seq[self.step], self.beat * 0.8)
                    self.step += 1
                    self.timer = self.beat
                else:
                    self.state, self.step = "input", 0
        elif self.state == "input":
            for pad in PADS:
                if inp.pressed(pad):
                    self.light(pad, 0.25)
                    if pad != self.seq[self.step]:
                        self.state, self.fail, self.flash = "dead", 0.9, 1.0
                        self.ctx.sfx("hit")
                        self.ctx.sfx("die")
                        self.ctx.music(None)
                        return
                    self.step += 1
                    if self.step == len(self.seq):
                        self.score = len(self.seq)
                        self.ctx.sfx("line")
                        if self.score % 4 == 0:
                            self.ctx.sfx("level")
                            self.flash = 1.0
                        self.grow()
                        self.state, self.timer = "pause", 0.8
                    break

    def draw(self, c):
        dead = self.state == "dead"
        for y in range(N):
            for x in range(N):
                p = wedge(x, y)
                if p is None:
                    continue
                col = COLOURS[p]
                if dead:
                    # Wrong-button buzz: everything strobes red.
                    c.set(x, y, RED if int(self.fail * 10) % 2 else dim(RED, 0.15))
                elif p == self.lit:
                    c.set(x, y, WHITE if self.lit_for > 0.1 and self.state == "input" else col)
                else:
                    c.set(x, y, dim(col, 0.18))
        centre = ORANGE if self.state == "input" else WHITE if self.state == "show" else dim(ORANGE, 0.3)
        if self.flash > 0:
            centre = WHITE
        if not dead:
            c.rect(6, 6, 4, 4, centre)
            for i in range(min(self.step, 8) if self.state == "input" else 0):
                c.set(6 + i % 4, 7 + i // 4, (120, 40, 0))


GAMES = [Simon]
