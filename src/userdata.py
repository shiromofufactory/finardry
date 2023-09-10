LOCAL = False
try:
    from js import window
except:
    LOCAL = True
    print("ローカルモード")
import json
import util


class Userdata:
    # 書き込み
    def save(data):
        try:
            if LOCAL:
                with open("./local/save.json", "w") as fout:
                    fout.write(json.dumps(data))
            else:
                window.localStorage.setItem(
                    "finardry", json.dumps(data).replace(" ", "")
                )
                # url = f"{base}save?id={id}&data={json.dumps(data).replace(' ', '')}"
                # res = open_url(url).read()
                # return res.split(",")

        except:
            print("Save Failed.")
            return None

    # 読み込み
    def load():
        try:
            if LOCAL:
                return util.load_json("./local/save")
            else:
                return json.loads(window.localStorage.getItem("finardry"))
                # url = f"{base}load?id={id}"
                # return json.loads(open_url(url).read())
        except:
            print("Load Failed.")
            return None

    # リセット（webのみ）
    def reset():
        if not LOCAL:
            window.location.reload()
