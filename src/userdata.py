LOCAL = False
try:
    from js import window, document
except:
    LOCAL = True
    print("ローカルモード")
import json
import util


class Userdata:
    # 書き込み
    def save(data, is_test=False):
        try:
            if LOCAL:
                if not is_test:
                    with open("./local/save.json", "w") as fout:
                        fout.write(json.dumps(data))
            else:
                key = "finardryTest" if is_test else "finardry"
                window.localStorage.setItem(key, json.dumps(data).replace(" ", ""))
            return True
        except:
            print("Save Failed.")
            return False

    # 読み込み
    def load():
        try:
            if LOCAL:
                return util.load_json("./local/save")
            else:
                return json.loads(window.localStorage.getItem("finardry"))
        except:
            print("Load Failed.")
            return None

    # 書き込み
    def set_config(data):
        try:
            if LOCAL:
                with open("./local/config.json", "w") as fout:
                    fout.write(json.dumps(data))
            else:
                key = "finardryConfig"
                window.localStorage.setItem(key, json.dumps(data).replace(" ", ""))
            return True
        except:
            print("Save Failed.")
            return False

    # 読み込み
    def get_config():
        try:
            if LOCAL:
                return util.load_json("./local/config")
            else:
                return json.loads(window.localStorage.getItem("finardryConfig"))
        except:
            print("Load Failed.")
            return None

    # ウェブ判定
    def is_web():
        return not LOCAL

    # PWA判定
    def is_pwa():
        if LOCAL:
            return False
        return window.matchMedia("(display-mode: standalone)").matches

    # ガイドを開く
    def open_guide():
        if LOCAL:
            return
        window.open(
            "https://github.com/shiromofufactory/finardry/blob/master/readme.md",
            "_blank",
        )
