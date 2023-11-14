LOCAL = False
try:
    from js import window, document
except:
    LOCAL = True
    print("ローカルモード")
import json
import util
from datetime import datetime, timedelta
import re


class Userdata:
    # 書き込み
    def save(data, is_test=False):
        try:
            data_str = json.dumps(data).replace(" ", "")
            if LOCAL:
                if not is_test:
                    with open("./local/save.json", "w") as fout:
                        fout.write(data_str)
            elif is_test:
                window.localStorage.setItem("finardryTest", data_str)
            else:
                window.localStorage.setItem("finardry", data_str)
                future_date = datetime.now() + timedelta(days=10 * 365)  # 10年後
                expires_str = future_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                modified_data = re.sub(r'"mapped":".*?",', "", data_str)
                cookie_str = f"finardry={modified_data}; expires={expires_str}; path=/"
                print(cookie_str)
                document.cookie = cookie_str
                print(document.cookie)
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
            if not LOCAL:
                match = re.search(r"finardry=([^;]+)", document.cookie)
                if match:
                    load_data = match.group(1)
                    return json.loads(load_data)
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
