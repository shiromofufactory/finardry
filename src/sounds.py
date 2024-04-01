import pyxel as px
import os
import json
import util


class Sounds:
    def __init__(self, no_bgm=False):
        Sounds.nocut = False
        Sounds.waiting = False
        Sounds.cur_music = None
        Sounds.next_music = None
        Sounds.musics = {}
        Sounds.tick = None
        Sounds.no_bgm = no_bgm
        Sounds.loop = False
        path = "musics/"
        files = os.listdir(path)
        for file in files:
            if file.split(".")[-1] == "json":
                key = file.replace(".json", "")
                with open(path + file, "r") as fin:
                    Sounds.musics[key] = json.loads(fin.read())
                # Sounds.musics[key] = util.load_json(path + key)

    # 効果音
    def sound(id, next_music=None):
        px.play(3, id)
        Sounds.nocut = False
        if next_music:
            Sounds.next_music = next_music

    # BGM設定
    def bgm(music, loop=True, next_music=None, tick=None):
        if Sounds.nocut and loop:
            Sounds.next_music = music
        elif Sounds.cur_music != music:
            if not loop:
                Sounds.nocut = True
                Sounds.next_music = (
                    Sounds.cur_music if next_music is None else next_music
                )
            Sounds.cur_music = music
            Sounds.loop = loop
            Sounds.play(loop, tick)

    # BGM再生
    def play(loop=True, tick=None):
        for ch, sound in enumerate(Sounds.musics[Sounds.cur_music]):
            if sound is None or ch == 3:
                continue
            if Sounds.no_bgm:
                px.sounds[ch].set("r", "", "", "", 1)
            else:
                px.sounds[ch].set(*sound)
            px.play(ch, ch, loop=loop, tick=tick)

    # 止まっていた曲を再生
    def resume(tick=None):
        if Sounds.next_music and px.play_pos(0) is None and px.play_pos(3) is None:
            Sounds.nocut = False
            Sounds.waiting = False
            Sounds.bgm(Sounds.next_music, tick=tick)
            Sounds.next_music = None
            return True
        return False
