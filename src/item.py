import util
from spell import Spell
from job import Job

items_dict = {item["id"]: item for item in util.load_json("data/items")}
const = util.load_json("data/const")


class Item:
    def __init__(self, id=None):
        item = items_dict.get(id)
        if item is not None:
            self.__dict__.update(item)
        else:
            self.id = None
            self.name = ""
            self.atc = 0
            self.hit = 0
            self.tribe = 0
            self.jobs = []
            self.nature = 0
            self.img_u = None
            self.img_v = None

    @property
    def can_equip_s(self):
        result = ""
        if len(self.jobs) >= 8:
            result = "すべてのクラス"
        else:
            for equip_job in self.jobs:
                if result:
                    result += "／"
                for job in Job.all():
                    if job.id == equip_job:
                        result += job.name[0:1]
        if self.nature:
            result += f"({['', 'G', 'N', 'E'][self.nature]})"
        return result

    def details(self, in_shop=False, counts=0):
        texts = []
        if self.id:
            if not in_shop:
                texts.append(self.name)
            texts.append(f"しゅるい: {const['item_type'][self.type]}")
            texts.append(self.can_equip_s)
            if texts[-1] != "":
                texts.append("")
            if self.atc:
                texts.append(f"ダメージ :{util.pad(self.atc,3)}")
                texts.append(f"めいちゅう:{util.pad('+'+str(self.hit),3)}")
            if self.ac:
                texts.append(f"AC   :{util.pad(self.ac,3)}")
            if self.healing:
                texts.append(f"かいふく :{util.pad(self.healing,3)}")
            if self.tribe:
                texts.append(f"{const['tribe'][self.tribe]}に つよい")
            for resist in self.resist:
                s = const["attr"][resist]
                if s:
                    texts.append(f"{s}を ふせぐ")
            if self.use:
                spell = Spell(self.use)
                if spell.id:
                    if texts[-1] != "":
                        texts.append("")
                    texts.append("つかうと")
                    texts.append(f"{spell.name}のこうか")
            if in_shop:
                for _ in range(10 - len(texts)):
                    texts.append("")
                texts.append(f"{util.pad(self.price,6)} Gold")
                texts.append(f" {util.pad(counts,2)}こ もっています")
        return texts

    @classmethod
    def all(cls):
        return [Item(item_id) for item_id in items_dict.keys()]
