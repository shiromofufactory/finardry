import pyxel as px
import util
import copy

msg_list = util.load_json("data/messages")


class Window:
    def __init__(self, key, x1, y1, x2, y2, texts, transparent=False):
        self.key = key
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.has_cur = False
        self.start_cur = False
        self.cur_x = None
        self.cur_y = None
        self.scr_y = 0
        self.sub_cur_x = None
        self.sub_cur_y = None
        self.texts = texts
        self.parm = None
        self.values = None
        self.btn = None
        self.transparent = transparent

    @property
    def cur_value(self):
        return self.values[self.cur_y * len(self.cur_pos_x) + self.cur_x]

    def draw(self, members):
        x1 = self.x1 * 8
        y1 = self.y1 * 12 + 8
        x2 = self.x2 * 8 + 8
        y2 = self.y2 * 12 + 16
        w = x2 - x1
        h = y2 - y1
        if not self.transparent:
            px.blt(x1 - 8, y1 - 8, 0, 16, 96, 8, 8, 3)
            px.blt(x2, y1 - 8, 0, 24, 96, 8, 8, 3)
            px.blt(x1 - 8, y2, 0, 16, 104, 8, 8, 3)
            px.blt(x2, y2, 0, 24, 104, 8, 8, 3)
            x = x1
            while x < x2:
                px.blt(x, y1 - 8, 0, 22, 96, 4, 8, 3)
                px.blt(x, y2, 0, 22, 104, 4, 8, 3)
                x += 4
            y = y1
            while y < y2:
                px.blt(x1 - 8, y, 0, 16, 102, 8, 4, 3)
                px.blt(x2, y, 0, 24, 102, 8, 4, 3)
                y += 4
            px.rect(x1, y1, w, h, 1)
        for i, text in enumerate(self.texts):
            pos = i - self.scr_y
            if pos >= 0 and pos <= self.y2 - self.y1:
                self.text(self.x1, self.y1 + pos, text)
        # スクロールインジケータ
        if len(self.texts) > self.y2 - self.y1 + 1 and self.has_cur:
            c = 7 if not self.btn is None and self.btn["u"] else 13
            self.text(self.x2, self.y1, "▲", c)
            c = 7 if not self.btn is None and self.btn["d"] else 13
            self.text(self.x2, self.y2, "▼", c)
        # メンバー
        if self.key == "menu_members":
            for i, member in enumerate(members):
                x = 8 if member.pos == 0 else 16
                self.draw_member(x, 18 + i * 48, member)
        elif self.key in ("select_members", "treasure_members"):
            for i, member in enumerate(members):
                x = 8 if member.pos == 0 else 16
                self.draw_member(x, 6 + i * 36, member)
        elif self.key in ["menu_detail", "training_new_member", "training_job_changed"]:
            mb = members[self.parm] if self.key == "menu_detail" else self.parm
            self.draw_member(8, 6, mb)
        elif self.key == "menu_spells":
            self.draw_member(8, 6, members[self.parm])
        elif self.key == "menu_equips":
            self.draw_member(8, 6, members[self.parm])
        if self.key == "shop_msg" and not self.parm is None:
            item = self.parm
            for i, member in enumerate(members):
                motion = 6 if member.can_equip(item) and px.frame_count % 30 < 15 else 0
                self.draw_member(4 + i * 48, 6, member, motion)
                if item.id in member.equips:
                    add_y = 1 if member.health < 4 else 0
                    self.text(self.x1 + i * 6 + 3, self.y1 + add_y, "E")
        elif self.key == "training_new":
            for idx in range(4):
                x = self.x1 * 8 + idx * 56 + 16
                u, v = util.job_uv(idx, 0)
                px.blt(x, self.y1 * 12 + 48, 1, u, v, 16, 24, 0)
        elif self.key == "training_job_old":
            self.draw_member(8, 6, self.parm)
        # 宝箱
        if self.key == "treasure_img":
            u, v = 208, self.parm * 48
            px.blt(self.x1 * 8 + 16, self.y1 * 12 + 16, 1, u, v, 48, 48, 0)
        # カーソル
        if self.has_cur:
            # メニューの「ならびかえ」カーソル
            if self.key == "menu_members" and not self.sub_cur_y is None:
                cx = self.cur_pos_x[self.sub_cur_x] * 8 + 4
                cy = (self.cur_pos_y[self.sub_cur_y] - self.scr_y) * 12
                px.blt(x1 + cx - 8, y1 + cy - 2, 0, 0, 96, 16, 16, 3)
            cx = self.cur_pos_x[self.cur_x] * 8
            cy = (self.cur_pos_y[self.cur_y] - self.scr_y) * 12
            px.blt(x1 + cx - 8, y1 + cy - 2, 0, 0, 96, 16, 16, 3)

    # キャラクタ表示
    def draw_member(self, x, y, mb, motion=0):
        if mb.poison or mb.health in (1, 2) or mb.hp <= mb.mhp // 4:
            motion = 5
        if mb.health > 2:
            motion = 0
        util.draw_member(self.x1 * 8 + x, self.y1 * 12 + y, mb, motion)

    def text(self, x, y, t, c1=7, c2=None):
        tz = util.zen(t)
        Window.bdf.draw_text(x * 8, y * 12 + 6, tz, c1, c2)

    def add_cursol(self, pos_y=None, pos_x=None):
        if pos_y:
            self.cur_pos_y = pos_y
        else:
            self.cur_pos_y = [i for i in range(len(self.texts))]
        if pos_x:
            self.cur_pos_x = pos_x
        else:
            self.cur_pos_x = [0]
        if self.cur_y is None:
            self.cur_y = 0
        if self.cur_x is None:
            self.cur_x = 0
        self.cur_y = min(self.cur_y, len(self.cur_pos_y) - 1)
        self.cur_x = min(self.cur_x, len(self.cur_pos_x) - 1)
        self.has_cur = True
        self.start_cur = False
        return self

    def init_cursol(self):
        self.cur_y = 0
        self.cur_x = 0
        self.scr_y = 0

    def update_cursol(self, btn):
        (mx, my) = (0, 0)
        self.btn = btn
        if not btn["u_"] and not btn["d_"]:
            self.start_cur = True
        if self.start_cur:
            if btn["u"]:
                my = -1
            elif btn["d"]:
                my = 1
            if btn["l"]:
                mx = -1
            elif btn["r"]:
                mx = 1
            self.move_cursol(my, mx)
        if btn["s"]:
            util.beep()
        return self

    def move_cursol(self, my=0, mx=0):
        self.cur_y += my
        height = self.y2 - self.y1
        if self.cur_y > len(self.cur_pos_y) - 1:
            self.cur_y = 0
            self.scr_y = 0
        elif self.cur_y < 0:
            self.cur_y = len(self.cur_pos_y) - 1
        # 戦闘時呪文ウィンドウ MPを見えるようにするための個別調整
        adjust = 1 if self.key == "battle_spells" else 0
        if self.cur_y + adjust > self.scr_y + height:
            self.scr_y = self.cur_y + adjust - height
        elif self.cur_y < self.scr_y:
            self.scr_y = self.cur_y
        self.cur_x = util.loop(self.cur_x, mx, len(self.cur_pos_x))

    @classmethod
    def get(cls, key):
        return cls.all[key] if key in cls.all else None

    @classmethod
    def open(cls, key, x1, y1, x2, y2, texts_in=[], transparent=False):
        texts = texts_in if type(texts_in) is list else [texts_in]
        if key in cls.all:
            cls.all[key].texts = texts
        else:
            cls.all[key] = cls(key, x1, y1, x2, y2, texts, transparent)
        return cls.all[key]

    @classmethod
    def close(cls, target=None):
        if target is None:
            windows_copy = copy.deepcopy(cls.all)
            for key in windows_copy:
                del cls.all[key]
            return
        if type(target) is list:
            targets = target
        else:
            targets = [target]
        for target in targets:
            if type(target) is str:
                if target in cls.all:
                    del cls.all[target]
            else:
                del cls.all[target.key]

    # ポップアップウィンドウ
    @classmethod
    def popup(cls, mes):
        width = len(mes)
        if width % 2 == 1:
            width += 1
        return cls.open("popup", 16 - width // 2, 9, 15 + width // 2, 9, mes)

    # メッセージウィンドウ
    @classmethod
    def message(cls, msg):
        if type(msg) == list:
            texts = msg
        else:
            texts = msg_list[msg]
        return cls.open("message", 1, 0, 30, 4, texts)

    # セレクタウィンドウ
    @classmethod
    def selector(cls, kind, parm=None, x=27, y=6):
        if kind == "yn":
            texts = [" はい", " いいえ"]
            values = None
            x1, y1, x2, y2 = x, y, x + 3, y + 1
        elif kind == "ev":
            if parm == "1":
                texts = [" ちか1かい", " ちか2かい", " ちか3かい", " ちか4かい"]
                values = [0, 1, 2, 3]
            elif parm == "2":
                texts = [" ちか4かい", " ちか5かい"]
                values = [3, 4]
            x1, y1, x2, y2 = x - 2, y, x + 3, y + len(texts) - 1
        elif kind == "friendly":
            texts = [" たたかう", " たちさる"]
            values = None
            x1, y1, x2, y2 = x - 3, y - 3, x + 2, y - 2
        elif kind == "reward":
            texts = [" もっていく", " たちさる"]
            values = None
            x1, y1, x2, y2 = x - 3, y - 2, x + 3, y - 1
        elif kind == "opening":
            texts = [" New Game", " Continue", " Config"]
            values = None
            x1, y1, x2, y2 = x - 6, y - 4, x + 3, y - 2
        win = cls.open(kind, x1, y1, x2, y2, texts).add_cursol()
        win.values = values
        win.parm = parm
        return win


Window.all = {}
