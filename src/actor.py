import pyxel as px
import util
from sounds import Sounds

TRANSPARENT = 3
MOVE_SPEED = 4
MAP_SIZE = 40
STEP_XY = ((0, -1), (1, 0), (0, 1), (-1, 0))


class Actor:
    def __init__(self, actor):
        self.x = actor["x"]
        self.y = actor["y"]
        self.z = actor["z"]
        self.dir = actor["dir"]
        self.wait = 0
        self.motion = 0
        self.chr = None  # Noneは透明モード
        self.moved = False
        self.prev_dx = 0
        self.prev_dy = 0
        self.turn_cnt = 0
        self.backmoving = False
        self.timer = 0
        self.reset_move()
        self.map_cells = []
        for i in range(6):
            with open(f"./maps/b{i+1}.txt", "r") as fin:
                self.map_cells.append(fin.readlines())
        if "mapped" in actor and actor["mapped"]:
            self.mapped = self.unzip(actor["mapped"])
        else:
            self.mapped = [
                [[0 for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
                for _ in range(6)
            ]
        self.light = actor["light"] if "light" in actor else 0

    def zip(self):
        mapped = ""
        for z in range(len(self.mapped)):
            for y in range(len(self.mapped[z])):
                mapped += "".join(map(str, self.mapped[z][y]))
        return mapped

    def unzip(self, mapped):
        result = [[None for _ in range(MAP_SIZE)] for _ in range(6)]
        idx = 0
        while True:
            z = idx // (MAP_SIZE * MAP_SIZE)
            if z >= 6:
                break
            y = (idx - z * (MAP_SIZE * MAP_SIZE)) // MAP_SIZE
            result[z][y] = [int(char) for char in mapped[idx : idx + MAP_SIZE]]
            idx += MAP_SIZE
        return result

    def update(self, btn):
        if self.wait:
            self.wait -= 1
            return
        if self.turn_cnt:
            self.turn_right()
            if self.turn_cnt <= 0:
                x, y = STEP_XY[self.dir]
                self.start_move(x, y)
            return
        self.timer += 1
        if self.moving and self.is_real:  # 斜め予約移動
            reserve_dir = None
            if self.dy != 0:
                if btn["r_"]:
                    reserve_dir = 1
                elif btn["l_"]:
                    reserve_dir = 3
            elif self.dx != 0:
                if btn["u_"]:
                    reserve_dir = 0
                elif btn["d_"]:
                    reserve_dir = 2
            if reserve_dir is not None:
                x, y = STEP_XY[reserve_dir]
                if self.start_move(self.dx + x, self.dy + y, True):
                    self.reserve_dir = reserve_dir
                    (self.reserve_x, self.reserve_y) = x, y
        else:  # 実移動
            (dx, dy) = (0, 0)
            backmoving = False
            if self.on_door:
                (dx, dy) = (self.prev_dx, self.prev_dy)
                backmoving = self.backmoving
            else:
                if btn["u_"] or btn["d_"]:
                    dir = 0 if btn["u_"] else 2
                    (_, dy) = self.set_move(dir)
                    if not btn["r_"] and not btn["l_"]:
                        self.dir = dir
                arrow_side = (dy == 0 and dx == 0) or not self.is_real
                if btn["r_"] or btn["l_"] and arrow_side:
                    dir = 1 if btn["r_"] else 3
                    (dx, _) = self.set_move(dir)
                    if not btn["u_"] and not btn["d_"]:
                        self.dir = dir
            self.start_move(dx, dy, False, backmoving)
        if self.moving:
            self.timer = 0
            self.sx += self.dx * MOVE_SPEED
            self.sy += self.dy * MOVE_SPEED
            self.motion = util.loop(self.motion, 1, 8)
            if abs(self.sx) >= 16:
                x = 1 if self.sx > 0 else -1
                self.sx -= x * 16
                self.x = (self.x + x + MAP_SIZE) % MAP_SIZE
                self.moved = True
            if abs(self.sy) >= 16:
                y = 1 if self.sy > 0 else -1
                self.sy -= y * 16
                self.y = (self.y + y + MAP_SIZE) % MAP_SIZE
                self.moved = True
            if self.moved:
                if self.is_real:
                    self.mapped[self.z][self.y][self.x] = 2
                self.prev_dx = self.dx
                self.prev_dy = self.dy
                self.dx = 0
                self.dy = 0
                if self.reserve_dir is not None and not self.on_door:
                    self.start_move(self.reserve_x, self.reserve_y)
                    self.dir = self.reserve_dir
                    self.reserve_dir = None
                    self.reserve_x = 0
                    self.reserve_y = 0
        return

    def draw(self):
        map_cells = self.map_cells[self.z]
        mapped = self.mapped[self.z]
        size = MAP_SIZE
        vision_map = [[False for _ in range(size)] for _ in range(size)]
        # 視界チェック
        if self.is_real:
            cx = self.x + 0.5  # + self.sx / 16
            cy = self.y + 0.5  # + self.sy / 16
            deg_expand = 15 if self.light else 0
            deg_start = (180, 270, 0, 90)[self.dir] + 15 - deg_expand
            deg_end = deg_start + 150 + deg_expand * 2
            vision_length = 6 if self.light else 4
            vision_map[self.y][self.x] = True
            for deg in range(deg_start, deg_end, 2):
                dist = 1
                while True:
                    x = int(cx + px.cos(deg) * dist + size) % size
                    y = int(cy + px.sin(deg) * dist + size) % size
                    vision_map[y][x] = True
                    mapped[y][x] = max(mapped[y][x], 1)
                    if not (map_cells[y][x] in " !<>tpw") or dist > vision_length:
                        break
                    dist += 1
        # フィールド描画
        for y in range(size):
            for x in range(size):
                visible = vision_map[y][x]
                passed = mapped[y][x]
                if visible or passed:
                    dx = (((x + size / 2 - self.x) % size - size / 2)) * 16 - self.sx
                    dy = (((y + size / 2 - self.y) % size - size / 2)) * 16 - self.sy
                    cell = map_cells[y][x]
                    passing = abs(dx) < 16 and abs(dy) < 16 and self.is_real
                    u = 6
                    if cell in " 0ptw":
                        u = 0
                        if cell == "p" and passed == 2:
                            u = 4
                        elif cell in "tw" and passed == 2:
                            u = 5
                    elif cell == "!":
                        u = 1
                    elif cell == "<":
                        u = 2
                    elif cell == ">":
                        u = 3
                    elif cell in "+urdl¥" and passing:
                        u = 8
                    elif (
                        cell == "+"
                        or (cell == "u" and dy < 0 and visible)
                        or (cell == "r" and dx > 0 and visible)
                        or (cell == "d" and dy > 0 and visible)
                        or (cell == "l" and dx < 0 and visible)
                    ):
                        u = 7
                    elif cell == "¥":
                        near = (
                            (
                                (self.dir == 0 and dx == 0 and dy >= -16 and dy <= 0)
                                or (self.dir == 1 and dx <= 16 and dx >= 0 and dy == 0)
                                or (self.dir == 2 and dx == 0 and dy <= 16 and dy >= 0)
                                or (self.dir == 3 and dx >= -16 and dx <= 0 and dy == 0)
                            )
                            and px.frame_count % 30 < 3
                            and self.is_real
                        )
                        if self.light or not self.is_real or passed == 2 or near:
                            u = 7
                    v = 4 if self.z < 5 else 5
                    v_u = mapped[(y + size - 1) % size][x]
                    v_d = mapped[(y + 1) % size][x]
                    v_l = mapped[y][(x + size - 1) % size]
                    v_r = mapped[y][(x + 1) % size]
                    mask_u = (2 if v_l else 0) + (1 if v_r else 0)
                    mask_v = 8 + (2 if v_u else 0) + (1 if v_d else 0)
                    dx += 120
                    dy += 120
                    px.blt(dx, dy, 0, u * 16, v * 16, 16, 16)
                    if not visible:
                        px.blt(dx, dy, 0, 0 * 16, 7 * 16, 16, 16, 3)
                    px.blt(dx, dy, 0, mask_u * 16, mask_v * 16, 16, 16, 3)
        # プレイヤー
        if self.is_real:
            img_x = self.chr * 2 + self.motion // 4
            img_y = self.dir
            u = img_x * 16
            v = img_y * 16
            px.blt(120, 120, 0, u, v, 16, 16, 2)
        elif px.frame_count % 30 < 15:
            px.blt(120, 120, 0, 15 * 16, 4 * 16, 16, 16, 2)

    def reset_move(self):
        self.dx = 0
        self.dy = 0
        self.sx = 0
        self.sy = 0
        self.reserve_dir = None
        self.reserve_x = 0
        self.reserve_y = 0

    def set_move(self, dir):
        (dx, dy) = STEP_XY[dir]
        if self.dir == dir or self.chr is None:
            return (dx, dy)
        elif self.start_move(dx, dy, True):
            self.dir = dir
            self.wait = 2
        return (0, 0)

    def start_move(self, x, y, virtual=False, backmoving=False):
        if x == 0 and y == 0:
            return False
        self.backmoving = backmoving
        nx = (self.x + x + MAP_SIZE) % MAP_SIZE
        ny = (self.y + y + MAP_SIZE) % MAP_SIZE
        cell = self.map_cells[self.z][ny][nx]
        if self.is_real and (
            cell == "-"
            or (cell == "u" and (self.dir != 0))
            or (cell == "r" and (self.dir != 1))
            or (cell == "d" and (self.dir != 2))
            or (cell == "l" and (self.dir != 3))
        ):
            return False
        if not virtual:
            self.dx = x
            self.dy = y
            if cell in ("+¥udlr") and self.is_real:
                Sounds.sound(4)
        return True

    def turn_right(self):
        self.dir = (self.dir + 1) % 4
        self.turn_cnt -= 1
        self.wait = 1

    def backmove(self):
        self.set_move(util.loop(self.dir, 2, 4))
        dx, dy = self.set_move(self.dir)
        self.start_move(dx, dy, False, True)

    @property
    def moving(self):
        return self.dx != 0 or self.dy != 0

    @property
    def cell(self):
        return self.map_cells[self.z][self.y][self.x]

    @property
    def is_real(self):
        return not self.chr is None

    @property
    def on_door(self):
        if not self.is_real:
            return False
        map_cells = self.map_cells[self.z]
        return map_cells[self.y][self.x] in ("+¥udlr")
