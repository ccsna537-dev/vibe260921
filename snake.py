import random
import tkinter as tk
from collections import deque

CELL = 20
COLS = 30
ROWS = 20
DELAY = 120  # ms per move (lower is faster)
FOOD_COUNT = 3  # apples on the board at once

BG = "#1e1e1e"
GRID = "#262626"
FOOD = "#e53935"

PLAYER_HEAD, PLAYER_BODY = "#4caf50", "#81c784"
AI_HEAD, AI_BODY = "#2196f3", "#64b5f6"

DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
KEYS = {
    "Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0),
    "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0),
}


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


class Snake:
    def __init__(self, head, direction, head_color, body_color):
        dx, dy = direction
        self.body = [(head[0] - dx * i, head[1] - dy * i) for i in range(3)]
        self.direction = direction
        self.pending = direction
        self.score = 0
        self.head_color = head_color
        self.body_color = body_color
        self.new_head = None
        self.eating = False
        self.dead = False


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("Snake: You vs AI")
        root.resizable(False, False)

        bar = tk.Frame(root, bg=BG)
        bar.pack(fill="x")
        self.player_var = tk.StringVar()
        self.ai_var = tk.StringVar()
        tk.Label(bar, textvariable=self.player_var, font=("Consolas", 14),
                 bg=BG, fg=PLAYER_HEAD).pack(side="left", padx=10)
        tk.Label(bar, textvariable=self.ai_var, font=("Consolas", 14),
                 bg=BG, fg=AI_HEAD).pack(side="right", padx=10)

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        root.bind("<Key>", self.on_key)
        self.wins = {"player": 0, "ai": 0}
        self.reset()

    # ---------- setup ----------
    def reset(self):
        self.player = Snake((COLS // 4, ROWS // 2 - 3), (1, 0),
                            PLAYER_HEAD, PLAYER_BODY)
        self.ai = Snake((COLS * 3 // 4, ROWS // 2 + 3), (-1, 0),
                        AI_HEAD, AI_BODY)
        self.foods = []
        self.fill_food()
        self.game_over = False
        self.paused = False
        self.update_score()
        self.tick()

    def fill_food(self):
        taken = set(self.player.body) | set(self.ai.body) | set(self.foods)
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in taken]
        random.shuffle(free)
        while len(self.foods) < FOOD_COUNT and free:
            self.foods.append(free.pop())

    def update_score(self):
        self.player_var.set(
            f"YOU {self.player.score}  (wins {self.wins['player']})")
        self.ai_var.set(f"AI {self.ai.score}  (wins {self.wins['ai']})")

    # ---------- input ----------
    def on_key(self, event):
        key = event.keysym
        if key in ("r", "R"):
            if self.game_over:
                self.reset()
            return
        if key == "space":
            if not self.game_over:
                self.paused = not self.paused
                self.draw()
            return
        if key in KEYS and not self.paused:
            dx, dy = KEYS[key]
            cur = self.player.direction
            if (dx, dy) != (-cur[0], -cur[1]):  # no reversing into itself
                self.player.pending = (dx, dy)

    # ---------- AI ----------
    def scan(self, start, blocked):
        """BFS from start: (reachable cell count, distance to nearest apple)."""
        seen = {start}
        queue = deque([(start, 0)])
        dist_food = None
        while queue:
            (x, y), d = queue.popleft()
            if dist_food is None and (x, y) in self.foods:
                dist_food = d
            for dx, dy in DIRS:
                n = (x + dx, y + dy)
                if in_bounds(*n) and n not in blocked and n not in seen:
                    seen.add(n)
                    queue.append((n, d + 1))
        return len(seen), dist_food

    def ai_choose(self):
        me, opp = self.ai, self.player
        hx, hy = me.body[0]
        blocked = set(me.body[:-1]) | set(opp.body[:-1])  # tails move away
        ohx, ohy = opp.body[0]
        danger = {(ohx + dx, ohy + dy) for dx, dy in DIRS}  # possible head-on

        options = []
        for dx, dy in DIRS:
            if (dx, dy) == (-me.direction[0], -me.direction[1]):
                continue
            n = (hx + dx, hy + dy)
            if not in_bounds(*n) or n in blocked:
                continue
            space, dist = self.scan(n, blocked | {n})
            key = (
                n in danger,                    # avoid head-on collisions
                space < len(me.body) + 2,       # avoid trapping itself
                dist if dist is not None else 10 ** 6,  # nearest apple
                -space,                         # prefer roomy areas
            )
            options.append((key, (dx, dy)))

        if not options:
            return me.direction  # no way out
        return min(options)[1]

    # ---------- game loop ----------
    def tick(self):
        if self.game_over:
            return
        if not self.paused:
            self.step()
        if not self.game_over:
            self.draw()
            self.root.after(DELAY, self.tick)

    def step(self):
        p, a = self.player, self.ai
        p.direction = p.pending
        a.direction = self.ai_choose()

        for s in (p, a):
            hx, hy = s.body[0]
            s.new_head = (hx + s.direction[0], hy + s.direction[1])
            s.eating = s.new_head in self.foods

        def body_after(s):  # tail moves away unless the snake is growing
            return s.body if s.eating else s.body[:-1]

        for s, o in ((p, a), (a, p)):
            s.dead = (not in_bounds(*s.new_head)
                      or s.new_head in body_after(s)
                      or s.new_head in body_after(o)
                      or s.new_head == o.new_head)

        for s in (p, a):
            if s.dead:
                continue
            s.body.insert(0, s.new_head)
            if s.eating:
                s.score += 1
                self.foods.remove(s.new_head)
            else:
                s.body.pop()

        self.fill_food()
        self.update_score()

        if p.dead or a.dead:
            self.end_game()

    def end_game(self):
        p, a = self.player, self.ai
        if p.dead and a.dead:
            if p.score > a.score:
                winner = "player"
            elif a.score > p.score:
                winner = "ai"
            else:
                winner = None
        else:
            winner = "ai" if p.dead else "player"

        if winner:
            self.wins[winner] += 1
        self.game_over = True
        self.update_score()
        self.draw()

        text = {"player": "You win!", "ai": "AI wins!", None: "Draw"}[winner]
        self.canvas.create_text(COLS * CELL // 2, ROWS * CELL // 2 - 15,
                                text=text, fill="white",
                                font=("Consolas", 32, "bold"))
        self.canvas.create_text(COLS * CELL // 2, ROWS * CELL // 2 + 25,
                                text="Press R to restart", fill="#bbbbbb",
                                font=("Consolas", 14))

    # ---------- drawing ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        for x in range(COLS + 1):
            c.create_line(x * CELL, 0, x * CELL, ROWS * CELL, fill=GRID)
        for y in range(ROWS + 1):
            c.create_line(0, y * CELL, COLS * CELL, y * CELL, fill=GRID)

        for fx, fy in self.foods:
            c.create_oval(fx * CELL + 2, fy * CELL + 2,
                          (fx + 1) * CELL - 2, (fy + 1) * CELL - 2,
                          fill=FOOD, outline="")

        for s in (self.player, self.ai):
            for i, (x, y) in enumerate(s.body):
                c.create_rectangle(x * CELL + 1, y * CELL + 1,
                                   (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                                   fill=s.head_color if i == 0 else s.body_color,
                                   outline="")

        if self.paused:
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2, text="Paused",
                          fill="white", font=("Consolas", 32, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
