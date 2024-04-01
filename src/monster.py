import pyxel as px
import util

monsters_dict = {monster["id"]: monster for monster in util.load_json("data/monsters")}
monster_images = util.load_texts("data/monster.dat")


class Monster:
    def __init__(self, id, idx=None):
        monster = monsters_dict[id]
        self.__dict__.update(monster)
        if 11 in self.resist:
            self.hp = self.mhp
        else:
            self.hp = int(self.mhp * px.rndf(0.8, 1.0))
        self.sleeping = 0
        self.silent = False
        self.spelled = []
        self.idx = idx
        self.fade = 0
        self.show = True
        self.blink = None
        if not idx is None:
            self.slide = [8, 8, 7, 7, 5][idx]
            img_no = self.id - 1
            u = (img_no % 4) * 64
            v = (img_no // 4) * 64
            img = [monster_images[v + y][u : u + 64] for y in range(64)]
            px.images[2].set((idx % 4) * 64, (idx // 4) * 64, img)

    @classmethod
    def all(cls):
        return [Monster(id) for id in monsters_dict.keys()]

    @property
    def is_live(self):
        return self.hp > 0

    def draw(self):
        if not self.show:
            return None, None
        mx = (8, 28, 64, 84, 120)[self.idx] - self.slide * 24
        self.slide = max(self.slide - 1, 0)
        my = (40, 112, 32, 104, 48)[self.idx]
        u = (self.idx % 4) * 64
        v = (self.idx // 4) * 64
        w = -64 if self.reverse else 64
        # 描画と点滅
        if not self.blink or self.blink % 6 < 3:
            px.blt(mx, my, 2, u, v, w, 64, 0)
        if self.blink:
            self.blink = max(self.blink - 1, 0)
        # 消滅（死亡）アニメーション
        length = self.fade * 2
        for y in range(8):
            for x in range(8):
                dist = y + 7 - x
                (u, v) = (None, None)
                if dist == length - 1:
                    (u, v) = (2, 14)
                elif dist == length - 2:
                    (u, v) = (4, 14)
                elif dist < length - 2:
                    (u, v) = (6, 14)
                if not u is None:
                    px.blt(mx + x * 8, my + y * 8, 0, u * 8, v * 8, 8, 8, 3)
        if self.fade:
            self.fade += 1
            if self.fade > 8:
                self.show = False
        return mx, my

    def is_vanguard(self, monsters):
        living_ms = [ms.idx for ms in monsters if ms.is_live]
        max_idx = max(living_ms)
        return self.idx > max_idx - 3
