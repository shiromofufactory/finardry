import pyxel as px
import os
import util


class Sounds:
    def __init__(self):
        Sounds.nocut = False
        Sounds.waiting = False
        Sounds.cur_music = None
        Sounds.next_music = None
        Sounds.musics = {}
        Sounds.tick = None
        path = "musics/"
        files = os.listdir(path)
        for file in files:
            if file.split(".")[-1] == "json":
                key = file.replace(".json", "")
                Sounds.musics[key] = util.load_json(path + key)

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
            Sounds.play(loop, tick)

    # BGM再生
    def play(loop=True, tick=None):
        for ch, sound in enumerate(Sounds.musics[Sounds.cur_music]):
            if sound is None or ch == 3:
                continue
            px.sound(ch).set(*sound)
            px.play(ch, ch, loop=loop, tick=tick)

    # BGM同期待ち
    def wait(music, next_music=None):
        Sounds.nocut = False
        Sounds.bgm(music, False)
        Sounds.waiting = True
        if next_music:
            Sounds.next_music = next_music

    # 止まっていた曲を再生
    def resume(tick=None):
        if Sounds.next_music and px.play_pos(0) is None and px.play_pos(3) is None:
            Sounds.nocut = False
            Sounds.waiting = False
            Sounds.bgm(Sounds.next_music, tick=tick)
            Sounds.next_music = None
            return True
        return False

    # 一時的に音を止める/再開（Web版バグ対策）
    def pause(is_pause):
        if is_pause:
            Sounds.tick = px.play_pos(0)[1] if px.play_pos(0) else 0
            Sounds.next_music = None
            for ch in [0, 1, 2, 3]:
                px.play(ch, 63, loop=False)
        else:
            Sounds.play(tick=Sounds.tick)
