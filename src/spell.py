import pyxel as px
import util

spells_dict = {spell["id"]: spell for spell in util.load_json("data/spells")}
const = util.load_json("data/const")


class Spell:
    def __init__(self, id=None):
        spell = spells_dict.get(id)
        if spell is not None:
            self.__dict__.update(spell)
        else:
            self.id = None

    @classmethod
    def all(cls):
        return [Spell(spell_id) for spell_id in spells_dict.keys()]

    @classmethod
    def get_cur_spell(cls, spells, cur_y, cur_x):
        spell_type = cur_y % 2 + 1
        spell_lv = cur_y // 2
        spell_x = 0
        for spell in Spell.all():
            if spell.id in spells and spell.lv == spell_lv and spell.type == spell_type:
                if spell_x == cur_x:
                    return spell
                else:
                    spell_x += 1

    @property
    def guide(self):
        if self is not None:
            return self.description.split("\n")
        else:
            return []

    def damage(self, target):
        dmg = 0
        count = self.intensity
        if self.attr in target.resist:
            print(f"{target.name}は{const['attr'][self.attr]}に強い")
            count = (count + 1) // 2
        for _ in range(count):
            dmg += px.rndi(2, 6)
        return dmg

    def cure(self):
        val = 0
        for _ in range(self.intensity):
            val += px.rndi(3, 6)
        return val

    def success(self, me, you):
        is_undead = you.tribe == 3
        base_rate = max(10 + (me.lv - you.lv), 1)
        if self.id in (2, 23, 32):  # カティノ、モンティノ、マバディ
            rate = base_rate
        elif self.id == 12:  # マカニトはレベル依存＋アンデットには効かない
            rate = 20 if you.lv <= 7 and not is_undead else 0
        elif self.id in (17, 29):  # ラカニトはアンデットには効かない
            rate = base_rate if not is_undead else 0
        elif self.id == 15:  # ジルワンはアンデットのみ高確率
            rate = base_rate + 10 if is_undead else 0
        else:  # ディルト系
            rate = 20
        if self.attr in you.resist:  # 耐性判定
            if self.attr == 5:  # 睡眠だけは弱点扱い
                rate += 10
            else:
                rate = 0
        success = rate > px.rndi(0, 19)
        print(f"{self.name} 耐性:{self.attr in you.resist} 成功確率:{rate} 結果:{success}")
        return success
