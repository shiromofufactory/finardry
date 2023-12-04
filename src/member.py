import copy
import util
import pyxel as px
from job import Job
from item import Item
from spell import Spell

jobs = util.load_json("data/jobs")
const = util.load_json("data/const")


class Member:
    def __init__(self, member):
        is_new = not "mhp" in member
        self.name = member["name"]
        self.nature = member["nature"]
        self.job_id = member["job_id"]
        self.lv = member["lv"] if "lv" in member else 1
        self.exp = member["exp"] if "exp" in member else 0
        self.mhp = 1
        self.mmp = [0, 0, 0, 0, 0, 0]
        self.str = member["str"]
        self.spd = member["spd"]
        self.vit = member["vit"]
        self.int = member["int"]
        self.pie = member["pie"]
        self.imperial = member["imperial"] if "imperial" in member else False
        self.health = member["health"] if "health" in member else 0  # 1眠り、2麻痺、3石化、4死亡
        self.equips = member["equips"] if "equips" in member else []
        self.silent = False  # 沈黙
        self.poison = member["poison"] if "poison" in member else False
        self.tribe = 4
        self.ac_tmp = 0
        self.pos = 0
        self.fx = None
        if is_new:
            self.mhp = self.get_new_mhp(1, 0.95)
            self.mmp = self.get_new_mmp(1)
            self.hp = self.mhp
            self.mp = copy.deepcopy(self.mmp)
            if self.job_id == 3:
                self.spells = [i + 19 for i in range(self.mmp[0])]
            elif self.job_id == 4:
                self.spells = [i + 1 for i in range(self.mmp[0])]
            else:
                self.spells = []
        else:
            self.hp = member["hp"]
            self.mhp = member["mhp"]
            self.mmp = member["mmp"]
            self.mp = member["mp"]
            self.spells = member["spells"] if "spells" in member else []

    @property
    def zip(self):
        zip = {
            "name": self.name,
            "nature": self.nature,
            "job_id": self.job_id,
            "lv": self.lv,
            "exp": self.exp,
            "mhp": self.mhp,
            "hp": self.hp,
            "mmp": self.mmp,
            "mp": self.mp,
            "str": self.str,
            "spd": self.spd,
            "vit": self.vit,
            "int": self.int,
            "pie": self.pie,
            "imperial": self.imperial,
            "spells": self.spells,
            "equips": self.equips,
            "health": self.health,
            "poison": self.poison,
            "pos": self.pos,
        }
        return zip

    @property
    def img(self):
        job = Job.get_idx(self.job_id)
        if self.health == 4:
            return job * 24, 224
        elif self.health == 3:
            pat = 7
        else:
            pat = 0
        return util.job_uv(job, pat)

    @property
    def class_s(self):
        return f"{self.nature_s}-{self.job_s}"

    @property
    def nature_s(self):
        return ["G", "N", "E"][self.nature - 1]

    @property
    def job(self):
        return Job(self.job_id)

    @property
    def job_s(self):
        return self.job.name

    @property
    def next_exp(self):
        if self.lv >= 50:
            return 999999
        base = 20 * self.job.exp_to_lvup
        value = base
        fix_value = None
        for lv in range(self.lv):
            if fix_value:
                value += fix_value
            else:
                if lv >= 12:
                    fix_value = int(value * 0.4)
                value = int(value * 1.4)
        value -= base
        return value - self.exp

    @property
    def weapon(self):
        return self.equip(1)[0]

    @property
    def atc(self):
        return self.weapon.atc

    @property
    def ac(self):
        ac = 10
        for equip in self.equips:
            ac += Item(equip).ac
        if ac == 10 and self.job_id == 8:
            ac = 8 - ((self.lv - 1) // 2)
        return max(ac + self.ac_tmp, -10)

    @property
    def hit(self):
        hit = -(-((self.weapon.hit + self.lv * 2) * self.job.hit * self.str) // 20)
        return min(hit, 200)

    @property
    def ac_disp(self):
        ac = self.ac if self.ac > -10 else "LO"
        return util.pad(ac, 2)

    @property
    def atc_disp(self):
        atc = int(min(self.atc * self.hit / 20, 99))
        # max_blows = -(-self.hit // 20)
        # atc = int(min(self.atc * max_blows, 99))
        return util.pad(atc, 2)

    @property
    def healing(self):
        healing = 0
        for equip in self.equips:
            healing += Item(equip).healing
        return healing

    @property
    def resist(self):
        resist = []
        for equip in self.equips:
            resist += Item(equip).resist
        return resist

    @property
    def check_rate(self):
        return Job(self.job_id).check + self.spd * 3 + self.lv

    @property
    def selectable_jobs(self):
        return [
            job.id
            for job in Job.all()
            if (
                self.job_id != job.id
                and self.str >= job.str
                and self.spd >= job.spd
                and self.vit >= job.vit
                and self.int >= job.int
                and self.pie >= job.pie
                and self.nature in job.nature
            )
        ]

    @property
    def text_catsle(self):
        return f" {util.spacing(self.name, 6)} {self.class_s} L{util.pad(self.lv, 2)} {self.status(True)}"

    @property
    def text_detail(self):
        str_mp = ""
        for lv in range(6):
            str_mp += f"{self.mp[lv]}/{self.mmp[lv]} "
        equips = []
        for i in range(6):
            equip = util.spacing(self.equip(i + 1)[0].name, 11)
            equips.append(f"{util.spacing(const['item_type'][i+1],5)}:{equip}")
        next_exp_str = max(self.next_exp, 0) if self.lv < 50 else "------"
        imperial = "このえへい" if self.imperial else "     "
        texts = [
            f"     {util.spacing(self.name,6)}  {self.class_s}    {self.status(True)}",
            f"     LV {util.pad(self.lv,2)}        EXP {util.pad(self.exp,6)}",
            f"     {imperial}   つぎのレベルまで {util.pad(next_exp_str,6)}",
            "",
            f"  HP {util.pad(self.hp,3)}/{util.pad(self.mhp,3)}  ",
            f"  MP {str_mp}",
            "",
            f"  ちから     {util.pad(self.str,2)}      こうげき {self.atc_disp}",
            f"  すばやさ    {util.pad(self.spd,2)}      AC   {self.ac_disp}",
            f"  せいめいりょく {util.pad(self.vit,2)}",
            f"  ちえ      {util.pad(self.int,2)}",
            f"  しんこうしん  {util.pad(self.pie,2)}",
            f"",
            f"  {equips[0]}",
            f"  {equips[1]}",
            f"  {equips[2]}",
            f"  {equips[3]}",
            f"  {equips[4]}",
            f"  {equips[5]}",
        ]
        return texts

    # ステータス
    def status(self, show_ok=False):
        if self.health == 4:
            return "しぼう"
        elif self.health == 3:
            return " いし"
        elif self.health == 2:
            return " まひ"
        elif self.health == 1:
            return "ねむり"
        elif self.poison:
            return " どく"
        elif show_ok:
            return " OK"
        else:
            return util.pad(self.mhp, 3)

    # 装備取得
    def equip(self, type):
        for idx, equip in enumerate(self.equips):
            item = Item(equip)
            if item.type == type:
                return item, idx
        return Item(), None

    # アイテムを装備可能か
    def can_equip(self, item):
        if item.nature and item.nature != self.nature:
            return False  # 性格不適合
        return self.job_id in item.jobs

    # 装備を交換
    def change_equip(self, type, item_id=None):
        equiped, idx = self.equip(type)
        if idx is None:
            if not item_id is None:
                self.equips.append(item_id)
        elif item_id is None:
            self.equips.pop(idx)
        else:
            self.equips[idx] = item_id
        return equiped.id

    # 装備を外す
    def get_off_equips(self, items, hold=False):
        equips = []
        for equip in self.equips:
            if hold and self.can_equip(Item(equip)):
                equips.append(equip)
            else:
                items.append(equip)
        self.equips = equips
        items.sort()

    # 蘇生
    def revive(self, full_recover=False):
        if self.health == 4:
            self.health = 0
            self.poison = 0
            self.hp = self.mhp if full_recover else 1
            return True
        return False

    # ヒーリングと回復
    def heal_and_poison(self):
        value = self.healing - self.poison
        if value > 0:
            self.add_hp(value)
        elif value < 0:
            self.lost_hp(-value)

    # HP回復
    def add_hp(self, val=None):
        if self.hp >= self.mhp or self.health == 4:
            return False
        if val is None:
            self.hp = self.mhp
        else:
            self.hp = min(self.hp + val, self.mhp)
        return True

    # HP減少
    def lost_hp(self, val=None):
        if self.hp == 0:
            return False
        if val is None:
            self.hp = 0
        else:
            self.hp = max(self.hp - int(val), 0)
        if self.hp <= 0:
            self.health = 4
            self.poison = 0
        return True

    # 最大HP rは初期レベル時に指定
    def get_new_mhp(self, lv, r=None):
        factor = px.rndf(0.9, 1.0) if r is None else r
        mhp = int((lv + 1) * self.vit * self.job.hp_up * factor / 10)
        return mhp if r else min(max(self.mhp + 1, mhp), 999)

    # 最大MP
    def get_new_mmp(self, lv):
        mmp = self.mmp
        ability = 0
        if self.job_id in [4, 6]:
            ability = self.int
        elif self.job_id in [3, 7]:
            ability = self.pie
        elif self.job_id == 5:
            ability = max(self.int, self.pie)
        for mlv in range(6):
            min_spell_lv = self.min_spell_lv(ability, mlv)
            new_mmp = min(max(lv - min_spell_lv + 1, 0), 9)
            mmp[mlv] = max(self.mmp[mlv], new_mmp)
        return mmp

    # じゅもんを覚える最低レベル
    def min_spell_lv(self, ability, mlv, type=1):
        factor = max(ability // 3 - 3, 0)
        if self.job_id in [3, 4]:
            return mlv * 3 - factor + 1
        elif self.job_id == 5 and type == 1:
            return mlv * 4 - factor + 1
        elif self.job_id in [5, 6, 7]:
            return mlv * 4 - factor + 4
        return 100

    # あたらしいじゅもん
    def get_new_spells(self, lv):
        spells = copy.deepcopy(self.spells)
        mmp = self.get_new_mmp(lv)
        learn_type = []
        if self.job_id in [4, 6]:
            learn_type = [1]
        elif self.job_id in [3, 7]:
            learn_type = [2]
        elif self.job_id == 5:
            learn_type = [1, 2]
        for mlv in range(6):
            learned_spell = []
            unlearned_spell = []
            for spell in Spell.all():
                ability = self.int if spell.type == 1 else self.pie
                if spell.lv == mlv:
                    if spell.id in self.spells:
                        learned_spell.append(spell.id)
                    elif (
                        lv >= self.min_spell_lv(ability, mlv, spell.type)
                        and spell.type in learn_type
                    ):
                        unlearned_spell.append(spell.id)
            while len(learned_spell) < mmp[mlv] and len(unlearned_spell):
                spell_id = unlearned_spell.pop(px.rndi(0, len(unlearned_spell) - 1))
                learned_spell.append(spell_id)
                spells.append(spell_id)
        return spells

    # レベルアップ時のステータス
    def get_lvup_status(self):
        new_lv = self.lv + 1
        up_pos = {}
        up_st = {"str": 0, "spd": 0, "vit": 0, "int": 0, "pie": 0}
        if self.str < 18:
            up_pos["str"] = 10 - self.str / 3 + self.job.str_up
        if self.spd < 18:
            up_pos["spd"] = 10 - self.spd / 3 + self.job.spd_up
        if self.vit < 18:
            up_pos["vit"] = 10 - self.vit / 3 + self.job.vit_up
        if self.int < 18:
            up_pos["int"] = 10 - self.int / 3 + self.job.int_up
        if self.pie < 18:
            up_pos["pie"] = 10 - self.pie / 3 + self.job.pie_up
        if len(up_pos):
            loop = True
            while loop:
                for parm in up_pos:
                    if up_pos[parm] > px.rndf(0.0, 10.0):
                        up_st[parm] = 1
                        loop = False
        res = {
            "mhp": self.get_new_mhp(new_lv),
            "mmp": self.get_new_mmp(new_lv),
            "str": self.str + up_st["str"],
            "spd": self.spd + up_st["spd"],
            "vit": self.vit + up_st["vit"],
            "int": self.int + up_st["int"],
            "pie": self.pie + up_st["pie"],
            "spells": self.get_new_spells(new_lv),
        }
        return res

    # 経験値取得
    def add_exp(self, parm):
        self.exp = min(self.exp + parm, 999999)

    # レベルアップ
    def lvup(self, parm):
        if self.lv < 50:
            self.lv += 1
            self.mhp = parm["mhp"]
            self.mmp = parm["mmp"]
            self.str = parm["str"]
            self.spd = parm["spd"]
            self.vit = parm["vit"]
            self.int = parm["int"]
            self.pie = parm["pie"]
            self.spells = parm["spells"]

    # 転職
    def change_job(self, job_id):
        self.lv = 1
        self.exp = 0
        self.job_id = job_id
        mhp = self.get_new_mhp(self.lv, 0.95)
        self.mhp = mhp if mhp > self.mhp else (self.mhp + mhp) // 2
        job = Job(job_id)
        str_m = job.str or 9 + job.str_up
        spd_m = job.spd or 9 + job.spd_up
        vit_m = job.vit or 9 + job.vit_up
        int_m = job.int or 9 + job.int_up
        pie_m = job.pie or 9 + job.pie_up
        self.str = min((self.str + str_m) // 2, self.str)
        self.spd = min((self.spd + spd_m) // 2, self.spd)
        self.vit = min((self.vit + vit_m) // 2, self.vit)
        self.int = min((self.int + int_m) // 2, self.int)
        self.pie = min((self.vit + pie_m) // 2, self.pie)
        self.mmp = [0, 0, 0, 0, 0, 0]
        if self.job_id == 3 and not 19 in self.spells:
            self.spells.append(19)
        elif self.job_id in (4, 5) and not 1 in self.spells:
            self.spells.append(1)
        for spell in Spell.all():
            if spell.id in self.spells:
                self.mmp[spell.lv] += 1
        self.recover()

    # フル回復
    def recover(self):
        self.health = 0
        self.hp = self.mhp
        for lv in range(len(self.mp)):
            self.mp[lv] = self.mmp[lv]
