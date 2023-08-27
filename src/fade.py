import pyxel as px

FADE_LIST = [
    (0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 4, 0, 0, 0, 0, 4),
    (0, 0, 0, 0, 0, 1, 5, 13, 2, 4, 9, 3, 5, 0, 4, 9),
]


class Fade:
    def __init__(self):
        Fade.state = 0
        Fade.dist = 0

    def start(is_out=False):
        Fade.state = 5 if is_out else 0
        Fade.dist = -1 if is_out else 1

    def draw():
        visible = True
        Fade.state += Fade.dist
        if Fade.dist != 0:
            if Fade.state <= 0:
                clist = [0 for _ in range(16)]
                Fade.dist = 0
                visible = False
            elif Fade.state <= 2:
                clist = FADE_LIST[0]
            elif Fade.state <= 4:
                clist = FADE_LIST[1]
            else:
                clist = [c for c in range(16)]
                Fade.dist = 0
            for c in range(16):
                px.pal(c, clist[c])
        return visible
