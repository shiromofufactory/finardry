import util

treasures_dict = {
    treasure["id"]: treasure for treasure in util.load_json("data/treasures")
}


class Treasure:
    def __init__(self, id=None):
        treasure = treasures_dict.get(id)
        if treasure is not None:
            self.__dict__.update(treasure)
        else:
            self.id = None

    @classmethod
    def all(cls):
        return [Treasure(treasure_id) for treasure_id in treasures_dict.keys()]
