import random
import tkinter as tk

WIDTH, HEIGHT = 640, 480
PADDLE_W, PADDLE_H = 90, 12
PADDLE_SPEED = 9
BALL_R = 7
BRICK_ROWS, BRICK_COLS = 6, 10
BRICK_H = 22
BRICK_GAP = 3
BRICK_TOP = 50
FPS_DELAY = 16  # ms
ROW_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
START_LIVES = 3


class Breakout:
    def __init__(self, root):
        self.root = root
        root.title("블럭깨기")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#111")
        self.canvas.pack()

        self.left = self.right = False
        root.bind("<KeyPress-Left>", lambda e: self._set_key("left", True))
        root.bind("<KeyRelease-Left>", lambda e: self._set_key("left", False))
        root.bind("<KeyPress-Right>", lambda e: self._set_key("right", True))
        root.bind("<KeyRelease-Right>", lambda e: self._set_key("right", False))
        root.bind("<space>", self._on_space)
        root.bind("<r>", lambda e: self.new_game())
        self.canvas.bind("<Motion>", self._on_mouse)

        self.new_game()
        self._tick()

    # ---------- 게임 상태 ----------
    def new_game(self):
        self.canvas.delete("all")
        self.score = 0
        self.lives = START_LIVES
        self.state = "ready"  # ready / playing / over / win
        self.bricks = {}
        self._build_bricks()

        self.paddle_x = (WIDTH - PADDLE_W) / 2
        self.paddle = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#ecf0f1", outline="")
        self.ball = self.canvas.create_oval(0, 0, 0, 0, fill="#fff", outline="")
        self.hud = self.canvas.create_text(
            10, 10, anchor="nw", fill="#ddd", font=("Malgun Gothic", 12))
        self.message = self.canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 60, fill="#fff", justify="center",
            font=("Malgun Gothic", 16, "bold"))

        self._reset_ball()
        self._draw()

    def _build_bricks(self):
        total_gap = BRICK_GAP * (BRICK_COLS + 1)
        bw = (WIDTH - total_gap) / BRICK_COLS
        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                x1 = BRICK_GAP + c * (bw + BRICK_GAP)
                y1 = BRICK_TOP + r * (BRICK_H + BRICK_GAP)
                item = self.canvas.create_rectangle(
                    x1, y1, x1 + bw, y1 + BRICK_H,
                    fill=ROW_COLORS[r % len(ROW_COLORS)], outline="")
                self.bricks[item] = (x1, y1, x1 + bw, y1 + BRICK_H)

    def _reset_ball(self):
        self.bx = WIDTH / 2
        self.by = HEIGHT - 60
        angle = random.choice([-1, 1]) * random.uniform(0.3, 0.7)
        self.speed = 5.0
        self.vx = self.speed * angle
        self.vy = -self.speed * (1 - abs(angle) * 0.3)
        self.state = "ready"

    # ---------- 입력 ----------
    def _set_key(self, name, pressed):
        setattr(self, name, pressed)

    def _on_mouse(self, event):
        self.paddle_x = event.x - PADDLE_W / 2
        self._clamp_paddle()

    def _on_space(self, _event):
        if self.state == "ready":
            self.state = "playing"
        elif self.state in ("over", "win"):
            self.new_game()

    def _clamp_paddle(self):
        self.paddle_x = max(0, min(WIDTH - PADDLE_W, self.paddle_x))

    # ---------- 메인 루프 ----------
    def _tick(self):
        if self.left:
            self.paddle_x -= PADDLE_SPEED
        if self.right:
            self.paddle_x += PADDLE_SPEED
        self._clamp_paddle()

        if self.state == "playing":
            self._update_ball()
        elif self.state == "ready":
            self.bx = self.paddle_x + PADDLE_W / 2
            self.by = HEIGHT - 40 - BALL_R - 1

        self._draw()
        self.root.after(FPS_DELAY, self._tick)

    def _update_ball(self):
        self.bx += self.vx
        self.by += self.vy

        # 벽 충돌
        if self.bx - BALL_R <= 0:
            self.bx = BALL_R
            self.vx = abs(self.vx)
        elif self.bx + BALL_R >= WIDTH:
            self.bx = WIDTH - BALL_R
            self.vx = -abs(self.vx)
        if self.by - BALL_R <= 0:
            self.by = BALL_R
            self.vy = abs(self.vy)

        # 패들 충돌 (맞은 위치에 따라 반사각 변화)
        py = HEIGHT - 40
        if (self.vy > 0 and py <= self.by + BALL_R <= py + PADDLE_H + abs(self.vy)
                and self.paddle_x - BALL_R <= self.bx <= self.paddle_x + PADDLE_W + BALL_R):
            offset = (self.bx - (self.paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)
            offset = max(-1, min(1, offset))
            angle = offset * 1.05  # 최대 약 60도
            self.vx = self.speed * angle
            self.vy = -self.speed * max(0.4, (1 - abs(offset) * 0.6))
            self.by = py - BALL_R

        # 블록 충돌
        for item, (x1, y1, x2, y2) in list(self.bricks.items()):
            if (x1 - BALL_R < self.bx < x2 + BALL_R
                    and y1 - BALL_R < self.by < y2 + BALL_R):
                # 어느 면에 맞았는지 겹침이 작은 축으로 판단
                overlap_x = min(self.bx + BALL_R - x1, x2 - (self.bx - BALL_R))
                overlap_y = min(self.by + BALL_R - y1, y2 - (self.by - BALL_R))
                if overlap_x < overlap_y:
                    self.vx = -self.vx
                else:
                    self.vy = -self.vy
                self.canvas.delete(item)
                del self.bricks[item]
                self.score += 10
                self._speed_up()
                break

        if not self.bricks:
            self.state = "win"
            return

        # 바닥으로 떨어짐
        if self.by - BALL_R > HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "over"
            else:
                self._reset_ball()

    def _speed_up(self):
        # 블록을 깰수록 조금씩 빨라짐
        if self.speed < 9:
            factor = 1.01
            self.speed *= factor
            self.vx *= factor
            self.vy *= factor

    # ---------- 그리기 ----------
    def _draw(self):
        py = HEIGHT - 40
        self.canvas.coords(self.paddle, self.paddle_x, py,
                           self.paddle_x + PADDLE_W, py + PADDLE_H)
        self.canvas.coords(self.ball, self.bx - BALL_R, self.by - BALL_R,
                           self.bx + BALL_R, self.by + BALL_R)
        self.canvas.itemconfigure(
            self.hud, text=f"점수: {self.score}    목숨: {'♥' * self.lives}")

        texts = {
            "ready": "스페이스바: 시작\n← → 키 또는 마우스로 이동",
            "over": f"게임 오버!  점수: {self.score}\n스페이스바: 다시 시작",
            "win": f"클리어!  점수: {self.score}\n스페이스바: 다시 시작",
        }
        self.canvas.itemconfigure(self.message, text=texts.get(self.state, ""))


if __name__ == "__main__":
    root = tk.Tk()
    Breakout(root)
    root.mainloop()
