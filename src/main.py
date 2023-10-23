import pyxel as px
import copy
import math
import util
from actor import Actor
from member import Member
from spell import Spell
from job import Job
from item import Item
from fade import Fade
from sounds import Sounds
from battle import Battle
from bdf import BDFRenderer
from window import Window
from userdata import Userdata

const = util.load_json("data/const")
with open("./data/names.txt", "r") as fin:
    names = fin.readlines()
chambers_master = util.load_json("data/chambers")


class App:
    def __init__(self):
        px.init(256, 256, title="Finardry", quit_key=px.KEY_NONE)
        px.load("wiz2d.pyxres")
        # px.image(0).save("../images/image0.png", 1)
        # px.image(1).save("../images/image1.png", 1)
        # px.image(2).save("../images/image2.png", 1)
        Window.bdf = BDFRenderer("k8x12S.bdf")
        self.events = util.load_json("data/events")
        self.reset()
        px.run(self.update, self.draw)

    def update(self):
        pl = self.player
        bt = self.battle
        # フレームカウント
        if pl:
            self.frames += 1
        if self.btn_reverse:
            btn_a = px.GAMEPAD1_BUTTON_B
            btn_b = px.GAMEPAD1_BUTTON_A
            btn_y = px.GAMEPAD1_BUTTON_Y
            btn_x = px.GAMEPAD1_BUTTON_X
        else:
            btn_a = px.GAMEPAD1_BUTTON_A
            btn_b = px.GAMEPAD1_BUTTON_B
            btn_y = px.GAMEPAD1_BUTTON_Y
            btn_x = px.GAMEPAD1_BUTTON_X
        btn = {
            "u_": px.btn(px.KEY_UP)
            or px.btn(px.KEY_K)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_UP),
            "d_": px.btn(px.KEY_DOWN)
            or px.btn(px.KEY_J)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_DOWN),
            "l_": px.btn(px.KEY_LEFT)
            or px.btn(px.KEY_H)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_LEFT),
            "r_": px.btn(px.KEY_RIGHT)
            or px.btn(px.KEY_L)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_RIGHT),
            "u": px.btnp(px.KEY_UP, 8, 2)
            or px.btnp(px.KEY_K, 8, 2)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_UP, 8, 2),
            "d": px.btnp(px.KEY_DOWN, 8, 2)
            or px.btnp(px.KEY_J, 8, 2)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_DOWN, 8, 2),
            "l": px.btnp(px.KEY_LEFT, 8, 2)
            or px.btnp(px.KEY_H, 8, 2)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_LEFT, 8, 2),
            "r": px.btnp(px.KEY_RIGHT, 8, 2)
            or px.btnp(px.KEY_L, 8, 2)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_RIGHT, 8, 2),
            "s": px.btnp(px.KEY_S, 8, 2) or px.btnp(btn_a, 8, 2),
            "s_": px.btn(px.KEY_S) or px.btn(btn_a),
            "a": px.btnp(px.KEY_A, 8, 2) or px.btnp(btn_b, 8, 2),
            "a_": px.btn(px.KEY_A) or px.btn(btn_b),
            "w": px.btnp(px.KEY_W, 8, 2) or px.btnp(btn_x, 8, 2),
            "w_": px.btn(px.KEY_W) or px.btn(btn_x),
            "q": px.btnp(px.KEY_Q, 8, 2) or px.btnp(btn_y, 8, 2),
            "q_": px.btn(px.KEY_Q) or px.btn(btn_y),
        }
        pressed = btn["s"] or btn["a"] or btn["w"]
        press_reset = (px.btn(px.KEY_ESCAPE) and px.btn(px.KEY_1)) or (
            btn["s_"] and btn["a_"] and btn["w_"] and btn["q_"]
        )
        # リセット
        if self.is_reset:
            if not press_reset and not pressed:
                self.reset()
            return
        elif press_reset:
            px.stop()
            Window.close()
            self.is_reset = True
            return
        # BGMオンオフ切り替え（廃止）
        if False:  # btn["q"]:
            Sounds.no_bgm = not Sounds.no_bgm
            music = Sounds.next_music or Sounds.cur_music
            Sounds.cur_music = None
            Sounds.bgm(music, Sounds.loop)
        # マップ切り替え
        if not self.visible and pl:
            if not self.next_z is None:
                return self.change_map()
            if not self.next_scene is None:
                self.scene = self.next_scene
                self.next_scene = None
            Fade.start()
            self.visible = True
        # 効果音/音楽→次の音楽
        if Sounds.resume(self.next_music_tick):
            self.next_music_tick = 0
        # フェード・銭湯突入中・強制音楽は操作を受け付けない
        if Fade.dist or self.rollout:  # or Sounds.waiting:
            return
        # ウィンドウ処理
        if "yn" in Window.all:
            win = Window.all["yn"].update_cursol(btn)
            if btn["s"] or btn["a"]:
                self.select_yn(win.parm, btn["s"] and win.cur_y == 0)
            return
        elif Window.get("ev"):
            win = Window.get("ev").update_cursol(btn)
            if btn["s"]:
                if win.cur_value == pl.z:
                    Sounds.sound(7)
                    return
                self.set_position(pl.x, pl.y, win.cur_value, 8)
            if btn["s"] or btn["a"]:
                Window.close()
            return
        elif Window.get("friendly"):
            win = Window.get("friendly").update_cursol(btn)
            if btn["s"]:
                if win.cur_y == 0:
                    bt.change_natures(3)
                    Window.close(["friendly", "battle_msg"])
                    bt.start_turn()
                else:
                    bt.change_natures(1)
                    self.end_battle()
                    self.map_bgm()
            return
        elif Window.get("opening"):
            win = Window.get("opening").update_cursol(btn)
            if btn["s"] or btn["a"]:
                self.btn_reverse = btn["a"]
                cur_y = win.cur_y
                Window.close()
                self.visible = False
                if cur_y == 0:
                    self.init_data()
                if self.members:
                    if self.player.z >= 0:
                        self.scene = 0
                        self.map_bgm()
                    else:
                        self.scene = 2
                elif Userdata.is_web():
                    texts = ["ゲームをはじめるまえに ガイドをかくにんしますか？", "（「はい」をおすと べつタブでガイドがひらきます）"]
                    Window.message(texts)
                    win = Window.selector("yn", "new_game")
                else:
                    self.start_new_game()
                self.set_position(self.player.x, self.player.y, self.player.z)
            return
        elif Window.get("popup"):
            parm = Window.get("popup").parm
            if pressed:
                Window.close("popup")
                if parm and parm[0] == "fall":
                    parm[0] = "move"
                    self.next_event = True
                    self.do_event(parm)
            return
        # 戦闘メッセージ（流れないもの）
        elif Window.get("battle_msg"):
            win = Window.get("battle_msg")
            if btn["s"] or btn["a"]:
                if win.scr_y < len(win.texts) - 1:
                    win.scr_y += 1
                    return
                if win.parm == "completed":
                    for mb in bt.members:
                        while mb.next_exp <= 0:
                            ls = mb.get_lvup_status()
                            texts = [
                                f"{mb.name}は レベルが あがった",
                                f"さいだいHP : {ls['mhp']} (+{ls['mhp']-mb.mhp})",
                            ]
                            if ls["str"] - mb.str:
                                texts += [f"ちから    : {ls['str']} (+{ls['str']-mb.str})"]
                            if ls["spd"] - mb.spd:
                                texts += [f"すばやさ   : {ls['spd']} (+{ls['spd']-mb.spd})"]
                            if ls["vit"] - mb.vit:
                                texts += [f"せいめいりょく: {ls['vit']} (+{ls['vit']-mb.vit})"]
                            if ls["int"] - mb.int:
                                texts += [f"ちえ     : {ls['int']} (+{ls['int']-mb.int})"]
                            if ls["pie"] - mb.pie:
                                texts += [f"しんこうしん : {ls['pie']} (+{ls['pie']-mb.pie})"]
                            if len(ls["spells"]) > len(mb.spells):
                                texts.append("あたらしいじゅもんを おぼえた")
                            mb.lvup(ls)
                            Window.open("battle_lvup", 2, 4, 22, 12, texts)
                            return
                    if self.battle.treasure:
                        Window.close()
                        Window.open(
                            "treasure_msg", 1, 1, 30, 2, "たからのはこだ！ どうしますか？"
                        ).parm = False
                        Window.open("treasure_img", 1, 4, 10, 9).parm = 0
                        texts = [" あける", " わなをしらべる", " カルフォをとなえる", " たちさる"]
                        win = Window.open("treasure", 1, 11, 10, 14, texts).add_cursol()
                        win.cur_y = 1
                        # ワナ判定
                        traps = self.battle.treasure.traps
                        if px.rndi(0, 2) > 0 or not traps:
                            trap = None
                            # print("罠なし")
                        else:
                            trap = traps[px.rndi(0, len(traps) - 1)]
                            # print(f"罠:{const['traps'][trap]}")
                        win.parm = trap
                        self.show_treasure_members()
                        return
                    self.end_battle()
                elif win.parm == "run":
                    self.end_battle(True)
                    self.map_bgm()
                    pl.backmove()
                elif win.parm == "notify":
                    if bt.suprise:
                        bt.phase = "action"
                    else:
                        bt.start_turn()
                elif win.parm == "friendly":
                    win = Window.selector("friendly")
                    for mb in self.members:
                        if mb.nature == 1:
                            win.cur_y = 1
                    return
                elif win.parm == "gameover":
                    self.end_battle()
                Window.close("battle_msg")
            return
        # メンバーセレクト（メニュー）
        elif "select_members" in Window.all:
            win = Window.all["select_members"].update_cursol(btn)
            is_temple = win.parm is None  # カントじいん
            target = self.members[win.cur_y]
            if is_temple:
                gold = 0
                if target.health == 4:
                    gold = 100
                elif target.health == 3:
                    gold = 50
                elif target.poison:
                    gold = 10
                gold *= target.lv
                self.show_temple_gold(gold)
                if btn["s"] or btn["a"]:
                    if btn["s"]:
                        if gold <= 0:
                            Sounds.sound(7)
                            self.show_temple(" たすけるひつようは ないようだ")
                            return
                        elif self.gold < gold:
                            Sounds.sound(7)
                            self.show_temple(" きふきんを あつめてこられよ")
                            return
                        msg = f"{target.name}"
                        if target.health == 4:
                            msg += "は いきかえった"
                            Sounds.sound(22)
                        elif target.health == 3:
                            msg += "の せきかがとけた"
                            Sounds.sound(22)
                        elif target.poison:
                            msg += "の どくがなおった"
                            Sounds.sound(9)
                        target.health = 0
                        target.poison = 0
                        target.hp = target.mhp
                        target.mp = copy.deepcopy(target.mmp)
                        self.gold -= gold
                        self.show_temple(msg)
                    else:
                        self.show_catsle(2)
            else:  # じゅもん
                result, cont = False, False
                if btn["s"] or btn["a"]:
                    if btn["s"]:
                        spell, member, item_id = win.parm
                        if spell:
                            result, cont = self.use_spell(
                                spell, member, target, item_id
                            )
                        else:
                            if not self.use_item(item_id, target):
                                Sounds.sound(7)
                                return
                    if result and not member is None:
                        member.mp[spell.lv] -= 1
                        self.show_menu_members()
                        self.show_spells()
                    if cont:
                        self.show_select_members((spell, member, item_id))
                    else:
                        Window.close(["select_members", "select_members_mes"])
            return
        # アイテム使う/捨てる
        elif "select_item" in Window.all:
            win = Window.all["select_item"].update_cursol(btn)
            if btn["s"]:
                item_id = self.items[win.parm]
                item = Item(item_id)
                name = item.name
                win_msg = Window.all["item_message"]
                if win.cur_y == 0:
                    if not self.available_item(item_id):
                        Sounds.sound(7)
                    else:
                        Window.close("select_item")
                        win_msg.parm = True
                        self.use_item(item_id)
                elif win.cur_y == 1:
                    if item.id == 77:  # ワードナのまよけ
                        Sounds.sound(7)
                    else:
                        Window.close("select_item")
                        self.clear_item(item.id)
                        self.show_items([f"{name}を すてた"])
                        win_msg.parm = True
            elif btn["a"]:
                Window.close(win)
            return
        # アイテムウィンドウ
        elif "menu_items" in Window.all:
            win = Window.all["menu_items"]
            old_idx = win.cur_y * 2 + win.cur_x
            win.update_cursol(btn)
            idx = win.cur_y * 2 + win.cur_x
            if old_idx != idx:
                old_idx = idx
                if idx >= len(self.items):
                    win.cur_x = 0
                    idx = win.cur_y * 2 + win.cur_x
                self.item_guide(idx)
            if btn["s"]:
                Window.open(
                    "select_item", 25, 18, 29, 19, [" つかう", " すてる"]
                ).add_cursol().parm = idx
            elif btn["a"]:
                self.show_menu(0)
            return
        # じゅもんウィンドウ
        elif "menu_spells" in Window.all:
            win = Window.get("menu_spells")
            # mb_idx = Window.get("menu_members").cur_y
            mb_idx = win.parm
            mb = self.members[mb_idx]
            spell = None
            while spell is None:
                win.update_cursol(btn)
                spell = Spell.get_cur_spell(mb.spells, win.cur_y, win.cur_x)
            spell = Spell.get_cur_spell(mb.spells, win.cur_y, win.cur_x)
            win_guide = Window.get("spells_guide")
            win_guide.texts = spell.guide
            if btn["s"] and spell:
                if not self.available_spell(spell, mb):
                    Sounds.sound(7)
                else:
                    result, cont = self.use_spell(spell, mb)
                    if result:
                        mb.mp[spell.lv] -= 1
                        if cont:
                            self.show_menu_members()
                        self.show_spells()
            elif btn["a"]:
                Window.close(["menu_spells", "spells_guide"])
                self.show_menu_info()
            elif btn["w"]:
                while True:
                    mb_idx = util.loop(mb_idx, 1, len(self.members))
                    if self.members[mb_idx].spells:
                        break
                Window.close([win, win_guide])
                self.show_spells(mb_idx)
            return
        # そうびウィンドウ
        elif "menu_equips" in Window.all:
            win = Window.all["menu_equips"]
            win_items = Window.get("menu_equip_items")
            if win_items and win_items.has_cur:
                win_items.update_cursol(btn)
                if btn["s"]:
                    member = self.members[win.parm]
                    item_id = win_items.cur_value
                    equiped = member.change_equip(win_items.parm, item_id)
                    if not equiped is None:
                        self.items.append(equiped)
                    self.clear_item(item_id)
                    win.move_cursol(1)
                if btn["s"] or btn["a"]:
                    win_items.has_cur = False
                    win_items.scr_y = 0
                    win_items.parm = None
                self.show_equips()
            else:
                win.update_cursol(btn)
                if btn["r"] or btn["l"]:
                    dist = 1 if btn["r"] else -1
                    win.parm = util.loop(win.parm, dist, len(self.members))
                    self.show_equips()
                else:
                    self.show_equip_guide()
                self.show_equip_items()
                if btn["s"]:
                    if len(win_items.values):
                        win_items.add_cursol().parm = win.cur_y + 1
                        win_items.init_cursol()
                    else:
                        win.move_cursol(1)
                elif btn["a"]:
                    mb_idx = win.parm
                    self.show_menu(2)
                    Window.all["menu_members"].cur_y = mb_idx
            return
        # ステータスウィンドウ
        elif "menu_detail" in Window.all:
            win = Window.all["menu_detail"]
            if btn["s"] or btn["r"] or btn["l"] or btn["u"] or btn["d"]:
                dist = -1 if btn["l"] or btn["u"] else 1
                win.parm = util.loop(win.parm, dist, len(self.members))
                self.show_detail()
            elif btn["a"]:
                mb_idx = win.parm
                self.show_menu(3)
                Window.all["menu_members"].cur_y = mb_idx
            return
        # メンバー選択
        elif "menu_members" in Window.all and Window.all["menu_members"].has_cur:
            win = Window.all["menu_members"].update_cursol(btn)
            if btn["s"]:
                if win.parm == 1:  # じゅもん
                    if self.show_spells(win.cur_y) is None:
                        Sounds.sound(7)
                elif win.parm == 4:  # ならびかえ
                    if win.sub_cur_y is None:
                        win.sub_cur_x = 0
                        win.sub_cur_y = win.cur_y
                        return
                    else:
                        if self.sort_members(win.sub_cur_y, win.cur_y):
                            self.show_menu_members()
                        win.sub_cur_y = None
            elif btn["a"]:
                if win.parm == 4 and not win.sub_cur_y is None:
                    win.sub_cur_y = None
                else:
                    win.has_cur = False
            return
        # メニューウィンドウ
        elif Window.get("menu"):
            win = Window.get("menu").update_cursol(btn)
            mb_idx = Window.get("menu_members").cur_y or 0
            if btn["s"]:
                if win.cur_y == 0:
                    Window.close()
                    if not self.show_items():
                        Sounds.sound(7)
                elif win.cur_y in [1, 4]:
                    if win.cur_y == 1:  # じゅもん
                        can_spell = False
                        for mb in self.members:
                            if mb.spells:
                                break
                        else:
                            Sounds.sound(7)
                            return
                    parm = win.cur_y
                    Window.get("menu_members").add_cursol(
                        [i * 4 for i in range(len(self.members))]
                    ).parm = parm
                    if win.cur_y == 1:
                        while True:
                            if self.members[mb_idx].spells:
                                break
                            mb_idx = util.loop(mb_idx, 1, len(self.members))
                        Window.get("menu_members").cur_y = mb_idx
                elif win.cur_y == 2:  # そうび
                    Window.close()
                    self.show_equips(mb_idx)
                    self.show_equip_items()
                elif win.cur_y == 3:  # ステータス
                    Window.close()
                    self.show_detail(mb_idx)
                elif win.cur_y == 5:
                    self.save_data()
                    Window.popup("セーブしました")
            elif btn["a"]:
                parm = win.parm
                Window.close()
                self.menu_visible = False
                if self.scene == 0:
                    self.map_bgm()
                elif self.scene == 3:
                    self.show_training(parm)
            return
        # ギルガメッシュのさかば
        elif Window.get("bar"):
            win_old = Window.get("bar")
            win_new = Window.get("bar_new")
            cur_y_last = len(win_old.values)
            if len(win_new.values) < 5:
                win_old.update_cursol(btn)
            else:
                win_old.cur_y = cur_y_last
            if btn["s"]:
                if len(win_new.values) > 0 and win_old.cur_y == cur_y_last:
                    self.reserves = win_old.values + win_old.parm
                    self.sort_reserves()
                    for mb in self.reserves:
                        mb.get_off_equips(self.items)
                    self.members = win_new.values
                    self.set_members_pos()
                    self.show_catsle(0)
                else:
                    member = win_old.values[win_old.cur_y]
                    if len(win_new.values) == 0 and member.health >= 3:
                        Sounds.sound(7)
                    else:
                        win_new.values.append(member)
                        self.show_bar()
            elif btn["a"]:
                if len(win_new.values):
                    win_new.values.pop()
                    self.show_bar()
                else:
                    self.show_catsle(0)
            return
        # ボルタックしょうてん：かう
        elif Window.get("shop_buy"):
            win = Window.get("shop_buy").update_cursol(btn)
            self.show_shop_guide()
            item = win.cur_value
            if btn["s"]:
                if self.gold < item.price:
                    self.show_shop_msg("おかねが たりないようですよ")
                    Sounds.sound(7)
                    return
                elif len(self.items) >= 40:
                    self.show_shop_msg("もちものが おおすぎますよ")
                    Sounds.sound(7)
                    return
                self.gold -= item.price
                self.show_shop()
                self.show_shop_msg("きっと おきにめしますよ")
                self.items.append(item.id)
            elif btn["a"]:
                self.items.sort()
                Window.close([win, "shop_msg", "shop_guide"])
            elif btn["u"] or btn["d"]:
                self.show_shop_msg("", item)
            return
        # ボルタックしょうてん：うる
        elif "shop_sell" in Window.all:
            win = Window.all["shop_sell"].update_cursol(btn)
            if btn["s"]:
                item = Item(self.items[win.cur_y])
                if item.price == 0:
                    self.show_shop_msg("そのしなものには いただけませんね")
                    Sounds.sound(7)
                    return
                self.add_gold(item.price // 2)
                self.show_shop()
                if not item.stocks and not item.id in self.stocks:
                    self.stocks.append(item.id)
                self.clear_item(item.id)
                if len(self.items) == 0:
                    Window.close([win, "shop_msg"])
                    return
                if win.cur_y >= len(self.items):
                    win.cur_y = len(self.items) - 1
                self.show_shop_msg("ありがとう ほかにも うってくれますか？")
                self.show_shop_sell()
            elif btn["a"]:
                Window.close(win)
                Window.close("shop_msg")
            elif btn["u"] or btn["d"]:
                self.show_shop_msg("")
            return
        # ボルタックしょうてん：メイン
        elif "shop_buysell" in Window.all:
            win = Window.all["shop_buysell"].update_cursol(btn)
            if btn["s"]:
                if win.cur_x == 0:  # かう
                    self.show_shop_buy()
                    self.show_shop_msg("", Window.get("shop_buy").cur_value)
                else:  # うる
                    if len(self.items) > 0:
                        self.show_shop_sell()
                        self.show_shop_msg("なにを おうりになりますか？")
                    else:
                        Sounds.sound(7)
            elif btn["a"]:
                self.show_catsle(1)
            return
        # くんれんじょう：キャラクターをつくる（確認）
        elif Window.get("training_new_confirm"):
            win = Window.get("training_new_confirm").update_cursol(btn)
            if btn["s"] or btn["a"]:
                member = Window.get("training_new_member").parm
                value = win.cur_value
                Window.close(["training_new_member", "training_new_confirm"])
                is_close = False
                if btn["s"] and value == 0:
                    self.members.append(member)
                    self.set_members_pos()
                    is_close = True
                elif btn["s"] and value == 1:
                    self.reserves.append(member)
                    self.sort_reserves()
                    is_close = True
                if is_close:
                    Window.close(
                        ["training_new", "training_nature", "training_tutorial"]
                    )
                    self.show_training(0)
        # くんれんじょう：キャラクターをつくる（入力）
        elif Window.get("training_new"):
            win = Window.get("training_new")
            win_nat = Window.get("training_nature")
            if win_nat:
                win_nat.update_cursol(btn)
            else:
                win.update_cursol(btn)
                self.show_training_new_guide()
            if btn["s"]:
                if win_nat:
                    win_nat.parm = win_nat.cur_value
                    job_id = win.parm
                    if job_id == 1:
                        sex = 0
                    elif job_id == 3:
                        sex = 1
                    else:
                        sex = px.rndi(0, 1)
                    unique_name = False
                    while not unique_name:
                        name = names[px.rndi(0, 29) + sex * 30].strip()
                        unique_name = True
                        if len(self.members + self.reserves) == 0:
                            break
                        for mb in self.members + self.reserves:
                            if mb.name == name:
                                unique_name = False
                    member = self.make_member(name, job_id, win_nat.parm)
                    self.show_training_new_member(member)
                else:
                    win.parm = win.cur_x + 1
                    self.show_training_new()
            elif btn["a"]:
                if win_nat:
                    Window.close(win_nat)
                elif len(self.members) == 0:
                    Sounds.sound(7)
                else:
                    self.show_training(0)
                    Window.close(win)
        # くんれんじょう：キャラクターをけす
        elif Window.get("training_delete"):
            win = Window.get("training_delete")
            win_msg = Window.get("training_delete_msg")
            if win_msg.has_cur:
                win_msg.update_cursol(btn)
            else:
                win.update_cursol(btn)
            if btn["s"]:
                member = win.values[win.cur_y]
                if win_msg.has_cur:
                    if win_msg.cur_y == 0:
                        self.reserves.pop(win.cur_y)
                        self.show_training_delete(f"{member.name}は まっしょうされました")
                    else:
                        self.show_training_delete()
                else:
                    win_msg.texts = [
                        f"{member.name}を けしますか？",
                        "* このそうさは もとに もどせません！ *",
                        "",
                        "  はい",
                        "  いいえ",
                    ]
                    win_msg.add_cursol([3, 4], [1]).cur_y = 0
            elif btn["a"]:
                if win_msg.has_cur:
                    self.show_training_delete()
                else:
                    self.show_training(1)
                    Window.close(["training_delete", "training_delete_msg"])
        # くんれんじょう：名前入力
        elif Window.get("training_name"):
            win = Window.get("training_name")
            win_guide = Window.get("training_name_guide")
            value = "/"
            while value == "/":
                win.update_cursol(btn)
                value = win.cur_value
            is_close = False
            member = win.parm
            self.show_training_name_guide()
            if btn["s"]:
                name = Window.get("training_name_guide").parm
                if value == "E":
                    if not win.parm:
                        Sounds.sound(7)
                        return
                    for mb in self.members + self.reserves:
                        if not mb is member and mb.name == name:
                            Sounds.sound(7)
                            Window.popup("おなじなまえは つけられません")
                            return
                    member.name = name
                    is_close = True
                elif value == "A":
                    self.show_training_name(1)
                elif value == "B":
                    self.show_training_name(0)
                else:
                    if len(win_guide.parm) >= 6:
                        Sounds.sound(7)
                        return
                    win_guide.parm += value
                    if len(win_guide.parm) >= 6:
                        win.cur_x = 10
                        win.cur_y = 6
            elif btn["a"]:
                if len(win_guide.parm) > 0:
                    win_guide.parm = win_guide.parm[:-1]
                else:
                    is_close = True
            if is_close:
                Window.close(["training_name", "training_name_guide"])
                self.show_training_change(0, member)
            return
        # くんれんじょう：職業変更
        elif Window.get("training_job"):
            win = Window.get("training_job").update_cursol(btn)
            win_guide = Window.get("training_job_guide")
            self.show_training_job_guide()
            member = win.parm
            is_close = False
            if btn["s"]:
                if win_guide.parm:
                    self.change_job(member, win.cur_value.id)
                    is_close = True
                    texts = member.text_detail
                    Window.open(
                        "training_job_changed", 1, 0, 30, 19, texts
                    ).parm = member
                else:
                    Sounds.sound(7)
            elif btn["a"]:
                is_close = True
            if is_close:
                Window.close(["training_job", "training_job_old", "training_job_guide"])
                if not Window.get("training_job_changed"):
                    self.show_training_change(1, member)
            return
        # くんれんじょう：職業変更確認
        elif Window.get("training_job_changed"):
            if pressed:
                win = Window.get("training_job_changed")
                self.show_training_change(1, win.parm)
                Window.close(win)
        # くんれんじょう：なまえ／しょくぎょうをかえる
        elif Window.get("training_change"):
            win = Window.get("training_change").update_cursol(btn)
            if btn["s"]:
                member = win.values[win.cur_y]
                if win.parm == 0:
                    self.show_training_name(0, member)
                    self.show_training_name_guide()
                else:
                    self.show_training_job_guide()
                    self.show_training_job(member)
                Window.close(["training_change", "training_change_msg"])
            elif btn["a"]:
                self.show_training(2 + win.parm)
                Window.close(["training_change", "training_change_msg"])
            return
        # くんれんじょう：メイン
        elif Window.get("training"):
            win = Window.get("training").update_cursol(btn)
            if btn["s"]:
                if win.cur_y == 0:
                    if len(self.members + self.reserves) < 10:
                        self.show_training_new()
                    else:
                        Sounds.sound(7)
                        return
                elif win.cur_y == 1:
                    if len(self.reserves):
                        self.show_training_delete()
                    else:
                        Sounds.sound(7)
                        return
                elif win.cur_y == 2:
                    self.show_training_change(0)
                elif win.cur_y == 3:
                    self.show_training_change(1)
                elif win.cur_y == 4:
                    self.show_catsle(3)
                    return
                Window.close(win)
            elif btn["a"]:
                self.show_catsle(3)
            elif btn["w"]:
                self.show_menu()
            return
        # キャッスル
        elif "catsle" in Window.all:
            win = Window.all["catsle"].update_cursol(btn)
            if btn["s"]:
                if win.cur_y == 0:
                    self.show_place(0)
                    self.show_bar()
                elif win.cur_y == 1:
                    self.show_place(1)
                    self.show_shop()
                elif win.cur_y == 2:
                    self.show_place(2)
                    win_sel = self.show_temple("  だれを たすけますか？")
                    for idx, mb in enumerate(self.members):
                        if mb.health or mb.poison:
                            win_sel.cur_y = idx
                            break
                elif win.cur_y == 3:
                    self.show_place(3)
                    self.show_training()
                elif win.cur_y == 4:
                    Sounds.sound(5, "wiz-dungeon")
                    self.player.dir = 0
                    self.next_z = 0
                    self.set_members_pos()
                    self.change_scene(0)
                    return
                Window.close(win)
            elif btn["a"]:
                win.cur_y = 4
            elif btn["w"]:
                self.show_menu()
            return
        # ポップオーバー消滅
        elif Window.get("battle_popover"):
            win = Window.get("battle_popover")
            win.parm -= 1
            if win.parm <= 0:
                Window.close("battle_popover")
                if bt.saved_msg:
                    bt.message(bt.saved_msg[0], bt.saved_msg[1])
                return
        # たからばこ
        elif Window.get("treasure"):
            tr = bt.treasure
            win = Window.get("treasure")
            trap = win.parm
            win_img = Window.get("treasure_img")
            win_msg = Window.get("treasure_msg")
            win_mem = Window.get("treasure_members")
            if win_msg.parm:  # 罠発動
                if btn["s"] or btn["a"]:
                    if trap == None:
                        if self.no_living:
                            Window.message(["ぼうけんしゃたちは ぜんめつした"])
                        else:
                            self.get_treasure(1)
                            win_msg.parm = None
                        return
                    elif trap == 5:  # テレポート
                        self.teleport()
                        return
                    elif trap == 8:  # 警報
                        self.battle = Battle(
                            pl.z + 1, bt.chamber_encount, bt.members, bt.items
                        )
                        self.start_battle()
                        return
                    targets = []
                    if trap in (0, 2, 4):  # 単体ターゲット
                        idx_max = len(bt.members) - 1
                        while not targets:
                            idx = px.rndi(0, idx_max)
                            if bt.members[idx].health < 3:
                                targets.append(idx)
                        if trap == 4:
                            Sounds.sound(16)
                        else:
                            Sounds.sound(12)
                    elif trap in (1, 3):  # ばくだん系
                        while not targets:
                            for idx, mb in enumerate(bt.members):
                                if mb.health < 3 and px.rndi(0, 1):
                                    targets.append(idx)
                        Sounds.sound(10)
                    elif trap == 6:  # メイジブラスター
                        for idx, mb in enumerate(bt.members):
                            if mb.health < 3 and mb.job_id in (4, 6) and px.rndi(0, 1):
                                targets.append(idx)
                        Sounds.sound(16)
                    elif trap == 7:  # プリーストブラスター
                        for idx, mb in enumerate(bt.members):
                            if mb.health < 3 and mb.job_id in (3, 5) and px.rndi(0, 1):
                                targets.append(idx)
                        Sounds.sound(16)
                    str_members = ""
                    for mb_idx in targets:
                        mb = bt.members[mb_idx]
                        effected = False
                        if trap in (0, 1) and not 7 in mb.resist:
                            mb.poison = 1
                            effected = True
                        elif trap in (2, 3):
                            dmg = 0
                            for _ in range(tr.lv + 1):
                                dmg += px.rndi(1, 8)
                            effected = True
                            mb.lost_hp(dmg)
                        elif trap == 4 and not 8 in mb.resist:
                            mb.health = 2
                            effected = True
                        elif trap in (6, 7):
                            if px.rndi(0, 1) and not 9 in mb.resist:
                                mb.health = 3
                                effected = True
                            elif mb.health < 2 and not 8 in mb.resist:
                                mb.health = 2
                                effected = True
                        if effected:
                            str_members += f" {mb.name}"
                    if len(targets) > 1 and len(targets) == len(bt.members):
                        str_members = " ぜんいん"
                    if not str_members:
                        str_members = " なし"
                    win_msg.texts = ["ひがいをうけた ぼうけんしゃ:", str_members]
                    self.show_treasure_members()
                    win.parm = None
            elif win_mem.has_cur:
                win_mem.update_cursol(btn)
                mb = bt.members[win_mem.cur_y]
                if win_mem.parm == 2:
                    can_spell = 24 in mb.spells
                    mp = mb.mp[1]
                    if can_spell:
                        win_msg.texts[1] = f" カルフォを つかえる (MP:{mp})"
                    else:
                        win_msg.texts[1] = f" カルフォを つかえない"
                if btn["s"]:
                    if mb.health:
                        Sounds.sound(7)
                        return
                    elif win_mem.parm == 1:
                        base_rate = mb.check_rate
                    elif win_mem.parm == 2:
                        if not can_spell or mp == 0:
                            Sounds.sound(7)
                            return
                        mb.mp[1] -= 1
                        base_rate = 90 + mb.pie * 2
                    success_rate = base_rate - tr.lv * 5
                    failure_rate = max(102 - success_rate, 0) // 3
                    if win_mem.parm == 2:
                        failure_rate = 0
                    # print(f"調査成功率:{success_rate}")
                    # print(f"暴発率:{failure_rate}")
                    # print(f"乱数:{win_mem.cur_value}")
                    if not trap is None and failure_rate > win_mem.cur_value:
                        self.do_trap(trap)
                        win_mem.has_cur = False
                        return
                    elif success_rate > win_mem.cur_value:
                        result = trap
                    else:
                        if trap is None:
                            result = tr.traps[win_mem.cur_value % len(tr.traps)]
                        else:
                            result = None
                    if result is None:
                        win_msg.texts = ["* わなは かかっていない *", ""]
                    else:
                        win_msg.texts = [f"* わなは {const['traps'][result]} *", ""]
                elif btn["a"]:
                    win_mem.has_cur = False
            else:
                if win_img.parm == 0:
                    win.update_cursol(btn)
                    if btn["a"]:
                        win.cur_y = 3
                if btn["s"] or btn["a"]:
                    if win_img.parm == 1:
                        self.end_battle()
                    elif btn["a"]:
                        return
                    elif win.cur_y == 3:
                        self.end_battle()
                    elif win.cur_y in (1, 2):
                        win_mem.add_cursol([i * 3 for i in range(len(bt.members))])
                        win_mem.parm = win.cur_y
                        if win.cur_y == 1:
                            win_msg.texts = ["だれが わなをしらべますか？", ""]
                            max_rate = 0
                            for idx, mb in enumerate(bt.members):
                                if mb.check_rate > max_rate and not mb.health:
                                    win_mem.cur_y = idx
                                    max_rate = mb.check_rate
                        elif win.cur_y == 2:
                            for idx, mb in enumerate(bt.members):
                                if 24 in mb.spells and mb.mp[1] and not mb.health:
                                    win_mem.cur_y = idx
                                    win_msg.texts = ["だれが カルフォをとなえますか？", ""]
                                    break
                            else:
                                win_mem.has_cur = False
                                Sounds.sound(7)
                        return
                    elif trap is None:
                        self.get_treasure()
                    else:
                        self.do_trap(trap)
            return
        # 戦闘：勝利
        elif bt and bt.completed:
            Sounds.bgm("wiz-win", False, "wiz-dungeon")
            members = [mb for mb in bt.members if mb.health < 3]
            exp_each = bt.total_exp // len(members)
            for mb in members:
                mb.add_exp(exp_each)
            # 待機メンバの経験値獲得とレベルアップ
            reserves = [mb for mb in self.reserves if mb.health < 3]
            if len(reserves) > 0:
                exp_reserve = math.ceil(exp_each / len(reserves))
                for mb in reserves:
                    mb.add_exp(exp_reserve)
                    while mb.next_exp <= 0:
                        mb.lvup(mb.get_lvup_status())
                        mb.recover()
            gold = self.add_gold(bt.total_gold, 0.4)
            text = f"{exp_each}のけいけんちと {gold}Gを えた"
            bt.message(text, "completed")
            return
        # 戦闘：強制離脱
        elif bt and bt.warp:
            if bt.warp == 1:  # マロール
                self.teleport(None)
                self.map_bgm()
            elif bt.warp == 2:  # ロクトフェイト
                self.end_battle(True)
                self.go_catsle(None)
            return
        # 戦闘：カーソル操作（メンバー選択）
        elif bt and not bt.selected_member is None:
            if bt.selected_member >= 0:
                if btn["u"] or btn["d"]:
                    dist = 1 if btn["d"] else -1
                    cur = bt.selector_items.index(bt.selected_member)
                    bt.selected_member = bt.selector_items[
                        util.loop(cur, dist, len(bt.selector_items))
                    ]
            command = bt.commands[-1]
            if btn["s"]:
                util.beep()
                command["members"] = bt.selected_member
                bt.selected_member = None
                bt.next_command(len(bt.commands) - 1)
            elif btn["a"]:
                if "item" in command:
                    command.pop("item")
                bt.selected_member = None
            return
        # 戦闘：カーソル操作（モンスター選択）
        elif bt and not bt.selected_monster is None:
            if bt.selected_monster >= 0:
                if btn["r"] or btn["l"]:
                    cur = bt.selector_items.index(bt.selected_monster)
                    dist = 1 if btn["r"] else -1
                    bt.selected_monster = bt.selector_items[
                        util.loop(cur, dist, len(bt.selector_items))
                    ]
                elif btn["u"] or btn["d"]:
                    list_ud = (2, 0, 4, 3, 1)
                    dist = 1 if btn["d"] else -1
                    list_idx = list_ud.index(bt.selected_monster)
                    while True:
                        list_idx = util.loop(list_idx, dist, 5)
                        if list_ud[list_idx] in bt.selector_items:
                            bt.selected_monster = list_ud[list_idx]
                            break
            command = bt.commands[-1]
            if btn["s"]:
                util.beep()
                command["target"] = bt.selected_monster
                bt.selected_monster = None
                bt.next_command(len(bt.commands) - 1)
            elif btn["a"]:
                if "item" in command:
                    command.pop("item")
                elif command["action"] in (0, 5):
                    bt.commands.pop(-1)
                bt.selected_monster = None
            return
        # 戦闘：じゅもん
        elif Window.get("battle_spells"):
            win = Window.get("battle_spells")
            mb_idx = win.parm
            win_guide = bt.show_spells()
            bt.show_spells()
            mb = bt.members[win.parm]
            spell = None
            while spell == None:
                win.update_cursol(btn)
                spell = Spell.get_cur_spell(mb.spells, win.cur_y, win.cur_x)
            win_guide.texts = spell.guide
            if btn["s"]:
                if not self.available_spell(spell, mb):
                    Sounds.sound(7)
                    return
                bt.commands[mb_idx]["spell"] = spell
                Window.close("battle_spells_guide")
                bt.init_selector(spell, mb_idx)
            if btn["a"]:
                command = bt.commands.pop(-1)
                Window.close(["battle_spells", "battle_spells_guide"])
            return
        # 戦闘：アイテム
        elif Window.get("battle_items"):
            win = Window.get("battle_items")
            mb_idx = len(bt.commands) - 1
            win_guide = bt.show_items(mb_idx)
            bt.show_items(mb_idx)
            mb = bt.members[mb_idx]
            win.update_cursol(btn)
            item = Item(win.cur_value)
            if item.id:
                win_guide.texts = item.details()[-2:]
                if btn["s"]:
                    if self.available_item(item.id):
                        bt.commands[mb_idx]["item"] = item
                        Window.close("battle_items_guide")
                        bt.init_selector(Spell(item.use), mb_idx)
                    else:
                        Sounds.sound(7)
            else:
                win_guide.texts = []
                if btn["s"]:
                    Sounds.sound(7)
            if btn["a"]:
                command = bt.commands.pop(-1)
                Window.close(["battle_items", "battle_items_guide"])
            return
        # 戦闘：コマンド選択
        elif Window.get("battle_command"):
            win = Window.get("battle_command").update_cursol(btn)
            if btn["s"] or btn["a"]:
                mb_idx = len(bt.commands)
                if btn["s"]:
                    if win.cur_value == 1:  # 逃走は即発動
                        win.close("battle_command")
                        bt.run()
                        return
                    bt.commands.append(
                        {"action": win.cur_value, "target": None, "members": None}
                    )
                    # たたかう、しきべつは敵選択。たたかうは前衛のみ
                    if win.cur_value in (0, 5):
                        bt.set_selector_monsters(win.cur_value == 0)
                    elif win.cur_value == 3:  # じゅもん
                        bt.show_spells(mb_idx)
                    elif win.cur_value == 6:  # アイテム
                        bt.show_items(mb_idx)
                    else:
                        bt.next_command(mb_idx)
                else:
                    bt.move_backward(mb_idx)
                    command = bt.find_active_member(len(bt.commands) - 1, -1)
                    if command:
                        bt.show_commands(command["action"])
                    else:
                        bt.phase = None
                        win.close("battle_command")
            return
        # メッセージウィンドウ
        elif Window.get("message"):
            win = Window.get("message")
            if win.scr_y % 5 != 0:
                win.scr_y += 1
                return
            if pressed:
                if len(win.texts) > win.scr_y + 5:
                    win.scr_y += 1
                    return
                Window.close("message")
                parm = win.parm
                if parm == "b1-2":
                    self.go_catsle(8)
                elif parm in ("b1-3", "b2-1", "b2-5", "b2-6"):
                    self.player.dir = 0
                    self.player.backmove()
                elif parm in ("b2-3",):
                    self.player.dir = 2
                    self.player.backmove()
                elif parm in ("b4-1", "b4-4"):
                    self.player.backmove()
                elif parm == "b1-4":
                    Window.message("search")
                    Window.selector("yn", ("item", 13))
                elif parm == "b1-5":  # マーフィーズゴースト
                    self.battle = Battle(None, False, self.members, self.items, 41)
                    self.start_battle()
                elif parm == "b1-6":
                    Window.message("search")
                    Window.selector("yn", ("item", 12))
                elif parm == "b2-2":
                    Window.message("search")
                    Window.selector("yn", ("item", 10))
                elif parm == "b2-4":
                    Window.message("search")
                    Window.selector("yn", ("item", 11))
                elif parm == "b2-7":
                    Window.message("search")
                    Window.selector("yn", ("item", 14))
                elif parm == "b4-6":
                    self.battle = Battle(pl.z + 1, True, self.members, self.items)
                    self.start_battle()
                elif parm == "b4-10":
                    self.select_yn(("item", 15), True)
                    Sounds.bgm("wiz-importance", False, "wiz-dungeon")
                elif parm == "b4-2w":
                    self.lost_item(77)
            return
        # エンディングメッセージ
        elif Window.get("ending"):
            win = Window.get("ending")
            if win.scr_y % 6 != 0:
                win.scr_y += 1
                return
            if pressed:
                if len(win.texts) > win.scr_y + 6:
                    win.scr_y += 1
                    return
                for mb in self.members:
                    if mb.health < 3:
                        mb.add_exp(10000)
                        mb.imperial = True
                self.add_gold(100000)
                Window.close(win)
                self.show_catsle()
            return
        # 全滅？
        if self.no_living and self.members:
            self.members[0].health = 0
            self.go_catsle(None)
            return
        # 戦闘
        if self.scene == 1 and bt:
            bt.update(btn["s"])
            return
        # 街
        elif self.scene in [2, 3]:
            if not "place" in Window.all:
                self.show_catsle()
            return
        # エンディング
        elif self.scene == 4:
            self.show_place(None)
            Sounds.bgm("wiz-ending")
            texts = [
                "",
                "      * * おめでとう * *",
                "",
                "   あなたは ワードナのまよけを とりもどし",
                "    トレボーの しけんに ごうかくした。",
                "",
                "      トレボーは ほうしゅうとして",
                "10,000の けいけんちと 100,000Goldを",
                "   パーティのメンバーの それぞれにあたえ",
                "  ぜんいんを このえへいとして にんめいした。",
                "",
                " ほこりをもって かいきゅうしょうを つけなさい。",
                "",
                "      あそんでくれて ありがとう！",
                "",
                "      ここまでの プレイじかんは",
                f"         {util.play_time(self.frames,True)}",
                "",
                "",
                "       〜 Finardry 〜",
                "",
                "     せいさく frenchbread",
                "    X(＠frenchbread1222)",
                "",
            ]
            Window.open("ending", 3, 13, 28, 18, texts)
            return
        # 主人公が動く
        pl.update(btn)
        if pl.is_real:
            if pl.moved:
                if not pl.on_door:
                    self.moved()
                elif not pl.backmoving and px.rndi(0, 9) == 0:
                    self.encount = 100
                exist_living = False
                for member in self.members:
                    exist_living = exist_living or (member.health < 2)
                if self.no_living:
                    Window.message(["ぼうけんしゃたちは ぜんめつした"])
                return
            if pl.moving:
                has_poison = False
                for member in self.members:
                    has_poison = has_poison or member.poison
                if has_poison and not px.play_pos(3):
                    Sounds.sound(7)
            # メニュー呼び出し
            elif btn["w_"]:
                if Sounds.cur_music == "wiz-dungeon":
                    self.next_music_tick = px.play_pos(0)[1]
                else:
                    self.next_music_tick = 0
                Sounds.bgm("wiz-camp")
                self.show_menu()
                return
            elif btn["a"]:
                pl.timer = 0
            # elif btn["q"]:
            #     print(pl.x, pl.y, pl.z)
            # 簡易ステータスウィンドウ制御
            if pl.timer >= 30:
                pl.timer = 30
                self.show_status()
            elif pl.timer == 0:
                Window.close("status")
        else:
            if pl.moved:
                pl.moved = False
            if self.saved_entity["warp"]:
                if btn["s"]:
                    if (
                        pl.cell in " 0!"
                        and pl.mapped[pl.z][pl.y][pl.x]
                        and pl.sx == 0
                        and pl.sy == 0
                    ):
                        self.release_transparent(True)
                    else:
                        Sounds.sound(7)
                elif btn["a"]:
                    self.release_transparent(False)
            else:
                if btn["s"]:
                    self.release_transparent(True)
                elif btn["a"]:
                    self.set_position(self.saved_entity["x"], self.saved_entity["y"])

    def draw(self):
        bt = self.battle
        c = 0
        if bt and bt.flash:
            c = bt.flash
            bt.flash = None
        px.cls(c)
        if not self.visible:
            return
        if Fade.dist:  # フェードイン・アウト
            self.visible = Fade.draw()
            return
        # プレイヤーとフィールド
        if not self.menu_visible:
            if self.scene == 0:
                pl = self.player
                pl.draw()
            elif self.scene == 1 and bt:
                bt.draw()
            elif self.scene in [2, 3, 4] and Window.get("place"):
                place = Window.get("place").parm
                if place == None or Window.get("training"):
                    px.blt(28, 36, 1, 0, 0, 208, 112)
        # ウィンドウ
        for key in Window.all:
            win = Window.all[key]
            win.draw(self.members)
        # ロールアウト（戦闘突入）
        if self.rollout > 0:
            length = self.rollout * 4
            for y in range(length):
                for x in range(length):
                    dist = y + x
                    (u, v) = (None, None)
                    if dist == length - 1:
                        (u, v) = (2, 14)
                    elif dist == length - 2:
                        (u, v) = (4, 14)
                    elif dist < length - 2:
                        (u, v) = (6, 14)
                    if not u is None:
                        self.draw_mask(x, y, u, v)
            self.rollout += 1
            if self.rollout >= 8:
                self.rollout = 0
                self.change_scene(1)
                self.visible = False
                bt.show_main()

    def draw_mask(self, x, y, u, v):
        px.blt(120 - x * 8, 120 - y * 8, 0, u * 8, v * 8, 8, 8, 3)
        px.blt(128 + x * 8, 120 - y * 8, 0, (u + 1) * 8, v * 8, 8, 8, 3)
        px.blt(120 - x * 8, 128 + y * 8, 0, u * 8, (v + 1) * 8, 8, 8, 3)
        px.blt(128 + x * 8, 128 + y * 8, 0, (u + 1) * 8, (v + 1) * 8, 8, 8, 3)

    ### システム ###

    # リセット
    def reset(self):
        Sounds()
        Fade()
        self.is_reset = False
        self.visible = True
        self.next_scene = None
        self.next_event = False
        self.next_z = None
        self.next_music_tick = 0
        self.saved_entity = {}
        self.menu_visible = False
        self.rollout = 0
        self.player = None
        self.battle = None
        self.scene = None
        self.members = []
        self.status_timer = 0
        self.btn_reverse = False
        texts = ["Finardryの せかいへ ようこそ！"]
        if not Userdata.save(True, True):
            texts += ["", "*** けいこく ***", "このブラウザでは セーブができません", "せっていを かくにんしてください"]
        Window.message(texts)
        texts = [
            "そうさほうほう（キーボード)",
            " じゅうじキー  : いどう、カーソルせんたく",
            " Sキー     : けってい",
            " Aキー     : キャンセル",
            " Wキー     : メニューをひらく",
            " ESC+1キー : リセット",
            "",
            "そうさほうほう（コントローラ)",
            " じゅうじキー  : いどう、カーソルせんたく",
            " A/したボタン : けってい",
            " B/みぎボタン : キャンセル",
            " X/ひだりボタン: メニューをひらく",
            " 4ボタンどうじ : リセット",
            "                   ver.231023",
        ]
        Window.open("opening-guide", 2, 6, 28, 19, texts, True)
        win = Window.selector("opening")
        win.cur_y = 1 if self.load_data() else 0
        Sounds.bgm("wiz-edge")

    # ゲーム初期化
    def start_new_game(self):
        self.show_training()
        self.show_place(3)
        self.show_training_new()
        Window.close("training")

    # セーブ
    def save_data(self):
        pl = self.player
        data = {
            "x": pl.x,
            "y": pl.y,
            "z": pl.z,
            "dir": pl.dir,
            "mapped": pl.zip(),
            "light": pl.light,
            "members": [member.zip for member in self.members],
            "reserves": [member.zip for member in self.reserves],
            "items": self.items,
            "gold": self.gold,
            "stocks": self.stocks,
            "encount": self.encount,
            "chambers": self.chambers,
            "frames": self.frames,
        }
        return Userdata.save(data)

    # ロード
    def load_data(self):
        data = Userdata.load()
        success = False
        try:
            self.player = Actor(
                {
                    "x": data["x"],
                    "y": data["y"],
                    "z": data["z"],
                    "dir": data["dir"],
                    "mapped": data["mapped"],
                    "light": data["light"],
                }
            )
            self.members = [Member(member) for member in data["members"]]
            self.reserves = [Member(reserve) for reserve in data["reserves"]]
            self.items = data["items"]
            self.gold = data["gold"]
            self.stocks = data["stocks"]
            self.encount = data["encount"]
            self.chambers = data["chambers"]
            self.frames = data["frames"]
            success = True
        except:
            self.init_data()
        self.set_members_pos()
        return success

    def init_data(self):
        self.player = Actor({"x": 1, "y": 39, "z": -1, "dir": 0})
        self.members = []
        self.reserves = []
        self.items = []
        self.gold = 600
        self.stocks = []
        self.encount = 0
        self.frames = 0
        self.reset_chambers()

    # キャラクタ生成
    def make_member(self, name, job_id, nature):
        job = Job(job_id)
        str_m = job.str or 9 + job.str_up
        spd_m = job.spd or 9 + job.spd_up
        vit_m = job.vit or 9 + job.vit_up
        int_m = job.int or 9 + job.int_up
        pie_m = job.pie or 9 + job.pie_up
        if nature == 1:
            str_m += 1
            pie_m += 1
        elif nature == 2:
            vit_m += 1
        else:
            spd_m += 1
            int_m += 1
        pat = len(self.members + self.reserves)
        if pat % 5 == 0:
            str_m += 1
            vit_m += 2
        elif pat % 5 == 1:
            str_m += 2
            spd_m += 1
        elif pat % 5 == 2:
            spd_m += 2
            int_m += 1
        elif pat % 5 == 3:
            pie_m += 2
            vit_m += 1
        else:
            int_m += 2
            pie_m += 1
        member = Member(
            {
                "name": name,
                "nature": nature,
                "lv": 1,
                "job_id": job.id,
                "str": str_m,
                "spd": spd_m,
                "vit": vit_m,
                "int": int_m,
                "pie": pie_m,
            }
        )
        return member

    # メンバー整列と先頭キャラ設定
    def set_members_pos(self):
        if len(self.members):
            self.members.sort(key=lambda u: u.health)
            for i, member in enumerate(self.members):
                member.pos = 0 if i < 3 else 1
            self.player.chr = self.members[0].job_id - 1

    # メンバーならびかえ
    def sort_members(self, idx1, idx2):
        result = True
        if idx1 == idx2:
            result = False
        elif self.members[idx1].health != self.members[idx2].health:
            result = False
        if result:
            self.members[idx1], self.members[idx2] = (
                self.members[idx2],
                self.members[idx1],
            )
            self.set_members_pos()
        else:
            Sounds.sound(7)
        return result

    # ひかえメンバーならびかえ
    def sort_reserves(self):
        self.reserves.sort(key=lambda mb: (mb.job.id, -mb.lv, mb.nature))

    # 転職
    def change_job(self, member, job_id):
        self.next_music_tick = px.play_pos(0)[1]
        Sounds.bgm("wiz-lvup", False)
        member.change_job(job_id)
        member.get_off_equips(self.items, True)

    ### メニュー ###

    # ステータスウィンドウ
    def show_status(self):
        if "status" in Window.all:
            return
        texts = ["なまえ    クラス      LV AC  HP"]
        for mb in self.members:
            texts.append(
                f"{util.spacing(mb.name,6)} {mb.class_s} {util.pad(mb.lv,2)} {mb.ac_disp} {util.pad(mb.hp,3)}/{mb.status()}"
            )
        Window.open("status", 1, 14, 30, 19, texts)

    # メニューウィンドウ（コマンド）
    def show_menu(self, cur_y=0):
        # くんれんじょうのカーソル記憶
        if Window.get("training"):
            parm = Window.get("training").cur_y
        else:
            parm = None
        Window.close()
        self.menu_visible = True
        texts = [
            " アイテム",
            " じゅもん",
            " そうび",
            " ステータス",
            " ならびかえ",
            " セーブ",
        ]
        win = Window.open("menu", 25, 0, 30, 5, texts).add_cursol()
        win.cur_y = cur_y
        win.parm = parm
        self.show_menu_info()
        self.show_menu_members()

    def show_menu_info(self):
        pl = self.player
        text_light = "あかり" if pl.light else ""
        texts = [
            f"ちか{pl.z+1}かい",
            text_light,
            "Gold",
            f"{util.pad(self.gold,6)}",
            "",
            "プレイじかん",
            f" {util.play_time(self.frames)}",
        ]
        if self.scene in [2, 3]:
            texts[0] = "キャッスル"
        Window.open("menu_info", 25, 7, 30, 13, texts)

    # メニューウィンドウ（パーティ）
    def show_menu_members(self):
        texts = []
        for mb in self.members:
            if len(mb.spells):
                str_mp = "     MP "
                for mlv in range(6):
                    str_mp += str(mb.mp[mlv])
                    if mlv < 5:
                        str_mp += "/"
            else:
                str_mp = ""
            texts += [
                f" {util.spacing(mb.name,6)} {mb.class_s} LV {util.pad(mb.lv,2)}",
                f"     HP {util.pad(mb.hp,3)}/{mb.status()}  AC {mb.ac_disp}",
                str_mp,
                "",
            ]
        Window.open("menu_members", 1, 0, 22, 19, texts)

    # ターゲット選択
    def show_select_members(self, parm=None, x=8, y=4):
        texts = []
        for mb in self.members:
            texts += [
                f"     {util.spacing(mb.name,6)}",
                f"     HP {util.pad(mb.hp,3)}/{mb.status()}",
                "",
            ]
        win = Window.open("select_members", x, y, x + 16, y + 13, texts[:-1])
        win.add_cursol([i * 3 for i in range(len(self.members))])
        win.parm = parm
        return win

    # 個人ステータスウィンドウ
    def show_detail(self, member_idx=None):
        win = Window.get("menu_detail")
        idx = member_idx if win is None else win.parm
        if idx is None:
            return None
        texts = self.members[idx].text_detail
        if win is None:
            win = Window.open("menu_detail", 1, 0, 30, 19, texts)
            win.parm = member_idx
        else:
            win.texts = texts

    # ゴールドを得る
    def add_gold(self, max_value, min_rate=None):
        if min_rate is None:
            value = max_value
        else:
            value = px.rndi(int(max_value * min_rate), max_value)
        self.gold = min(self.gold + value, 999999)
        return value

    ### アイテム ###

    # アイテムウィンドウを開く
    def show_items(self, mes=None):
        if len(self.items) == 0:
            self.show_menu(0)
            return False
        texts = []
        text = ""
        for i, id in enumerate(self.items):
            text += f" {util.spacing(Item(id).name, 11)} "
            if i % 2 == 1 or i == len(self.items) - 1:
                texts.append(text)
                text = ""
        win = Window.open("menu_items", 2, 0, 29, 16, texts).add_cursol(None, [0, 13])
        if win.cur_y * 2 + win.cur_x >= len(self.items):
            win.cur_y = 0
            win.cur_x = 0
        Window.open("item_message", 2, 18, 29, 19, mes)
        if mes is None:
            self.item_guide(0)
        return True

    # アイテム説明欄
    def item_guide(self, idx):
        item = Item(self.items[idx])
        texts = []
        texts.append(const["item_type"][item.type])
        if item.type == 0:
            if item.use:
                spell = Spell(item.use)
                texts.append(f"つかうと {spell.name}のこうか")
            else:
                texts.append("じゅうような アイテム")
        else:
            texts.append(f"そうびかのう: {item.can_equip_s}")
        Window.all["item_message"].texts = texts

    # アイテムを取得（即時ソート）
    def add_item(self, item):
        self.items.append(item.id)
        self.items.sort()

    # アイテムを消去
    def clear_item(self, id):
        if not id is None and id in self.items:
            self.items.remove(id)
            self.items.sort()

    # アイテム使用可否
    def available_item(self, item_id):
        use = Item(item_id).use
        if use == 99 and self.scene != 1:
            Window.open("select_members_mes", 8, 2, 24, 2, "  だれが つかいますか？")
            self.show_select_members((None, None, item_id))
        elif use:
            return self.available_spell(Spell(use))
        else:
            False

    # アイテム使用
    def use_item(self, item_id, target=None):
        use = Item(item_id).use
        if use == 99:  # 盗賊の担当
            if target.job_id == 2 and target.health < 3:
                self.brake_item(item_id)
                self.change_job(target, 8)
                Window.popup(f"{target.name}は {target.job_s}に なった")
            else:
                return False
        elif use:
            self.use_spell(Spell(use), item_id=item_id)
        return True

    # アイテム使用後
    def brake_item(self, item_id, description=""):
        item = Item(item_id)
        if item.brake:
            self.clear_item(item_id)
        if not description is None:
            add_text = "" if not description else f"* {description} *"
            self.show_items([f"{item.name}を つかった", add_text])
        return item.brake

    # アイテムor装備もってる？
    def has_item(self, item_id):
        items = self.items[:]
        for mb in self.members:
            items += mb.equips
        return item_id in items

    # アイテムor装備を失う
    def lost_item(self, item_id):
        if item_id in self.items:
            self.clear_item(item_id)
        for mb in self.members:
            if item_id in mb.equips:
                mb.equips.remove(item_id)

    ### そうび ###

    # そうびメインウィンドウ
    def show_equips(self, member_idx=None):
        win = Window.get("menu_equips")
        win_items = Window.get("menu_equip_items")
        idx = member_idx if win is None else win.parm
        if idx is None:
            return None
        member = self.members[idx]
        atc = member.atc_disp
        ac = member.ac_disp
        atc_after = "   "
        ac_after = "   "
        if win_items and win_items.parm:
            saved_equips = copy.deepcopy(member.equips)
            member.change_equip(win_items.parm, win_items.cur_value)
            if member.atc_disp != atc:
                atc_after = "→" + member.atc_disp
            if member.ac_disp != ac:
                ac_after = "→" + member.ac_disp
            member.equips = saved_equips
        texts = [
            f"    {util.spacing(member.name,6)}   ",
            f"    {member.class_s} ",
            f"    {util.spacing('',8)} ",
            f" こうげき {atc}{atc_after}  ",
            f" AC   {ac}{ac_after}  ",
            f"    {util.spacing('',8)} ",
        ]
        for i in range(6):
            equip = util.spacing(member.equip(i + 1)[0].name, 11)
            texts[i] += f"{util.spacing(const['item_type'][i+1],5)}:{equip}"

        if win is None:
            win = Window.open("menu_equips", 1, 0, 30, 5, texts)
            win.add_cursol([0, 1, 2, 3, 4, 5], [12])
            win.parm = member_idx
        else:
            win.texts = texts
        self.show_equip_guide()

    # そうびアイテム欄
    def show_equip_items(self):
        win_equip = Window.get("menu_equips")
        member = self.members[win_equip.parm]
        type = win_equip.cur_y + 1
        texts = []
        values = []
        if member.equip(type)[0].id:
            texts.append(" * そうびをはずす *")
            values.append(None)
        for id in self.items:
            item = Item(id)
            if item.type == type and member.can_equip(item):
                texts.append(f" {item.name}")
                values.append(id)
        Window.open("menu_equip_items", 1, 7, 14, 19, texts).values = values

    # そうびガイド欄
    def show_equip_guide(self):
        win = Window.get("menu_equips")
        win_items = Window.get("menu_equip_items")
        member = self.members[win.parm]
        if win_items and win_items.has_cur:
            item = Item(win_items.cur_value)
        else:
            item = Item(member.equip(win.cur_y + 1)[0].id)
        Window.open("menu_equip_guide", 17, 7, 30, 19, item.details())

    ### じゅもん ###

    def show_spells(self, member_idx=None):
        win = Window.get("menu_spells")
        idx = member_idx if win is None else win.parm
        if idx is None:
            return None
        member = self.members[idx]
        if member.health > 0:
            return None
        texts = [
            f"     {member.name}",
            f"     {member.class_s}",
        ]
        cur_y = None
        for lv in range(6):
            tm, tp = f"L{lv+1} ", f"{member.mp[lv]}/{member.mmp[lv]}"
            for spell in Spell.all():
                if spell.id in member.spells and spell.lv == lv:
                    name = util.spacing(spell.name, 8)
                    if spell.type == 1:
                        tm += f" {name}"
                        cur_y = lv * 2 if cur_y is None else cur_y
                    elif spell.type == 2:
                        tp += f" {name}"
                        cur_y = lv * 2 + 1 if cur_y is None else cur_y
            texts += ["", tm, tp]
        if not cur_y is None and win is None:
            win = Window.open("menu_spells", 1, 0, 30, 19, texts)
            win.add_cursol([3, 4, 6, 7, 9, 10, 12, 13, 15, 16, 18, 19], [3, 12, 21])
            win.cur_y = cur_y
            win.parm = member_idx
        elif win:
            win.texts = texts
        win_guide = Window.get("spells_guide")
        if win and win_guide is None:
            Window.open("spells_guide", 17, 0, 30, 1)
        return win

    def available_spell(self, spell, member=None):
        if self.scene in [2, 3]:
            return False
        if member and member.mp[spell.lv] <= 0:
            return False
        if self.scene == 1 and spell.on_battle:
            return True
        elif self.scene == 0 and spell.on_camp:
            return True
        return False

    def use_spell(self, spell, member=None, target=None, item_id=None):
        if not self.available_spell(spell, member):
            Sounds.sound(7)
            return False, False
        pl = self.player
        id = spell.id
        result = True
        cont = False
        if spell.target == 1:
            if target is None:
                Window.open("select_members_mes", 8, 2, 24, 2, "  だれに つかいますか？")
                self.show_select_members((spell, member, item_id))
                return None, False
            cont = True
        description = ""
        if id in (19, 25):  # ディオス、ディアル
            if target.add_hp(spell.cure()):
                if item_id is not None:
                    description = f"{target.name}  HP:{util.pad(target.hp,3)}/{util.pad(target.mhp,3)}"
                Sounds.sound(9)
        elif id == 22:  # ディアルコ
            result = target.health in (1, 2)
            if result:
                target.health = 0
                self.set_members_pos()
                Sounds.sound(9)
        elif id == 27:  # ラテュモフィス
            result = target.poison
            if result:
                if item_id is not None:
                    description = f"{target.name}の どくが きえた"
                target.poison = 0
                Sounds.sound(9)
        elif id == 31:  # マディ
            result = target.add_hp() or target.health in (2, 3) or target.poison
            if result:
                target.poison = 0
                target.health = 0
                self.set_members_pos()
                Sounds.sound(9)
        elif id in (28, 34):  # ディ、カドルト
            result = target.revive(id == 34)
            if result:
                self.set_members_pos()
                Sounds.sound(9)
        elif id in (6, 18):  # デュマピック、マロール
            if id == 18 and pl.z == 5:
                Window.popup("じゅもんが かきけされた")
                result = False
            else:
                self.set_transparent(member, id, item_id)
                return False, False
        elif id == 21:  # ミルワ
            pl.light = 80
            description = "あかりが ともった "
        elif id == 30:  # ロミルワ
            pl.light = -1
            description = "あかりが ともった "
        elif id == 36:  # ロクトフェイト
            self.go_catsle(8)
            self.menu_visible = False
            return False, False
        if result and member:  # 成功：じゅもん
            if description:
                Window.popup(description)
            self.show_menu_members()
            self.show_spells()
        elif result and item_id is not None:  # 成功：アイテム
            if self.brake_item(item_id, description):
                cont = False
        elif not result:  # 失敗
            Sounds.sound(7)
        return result, cont

    ### キャッスル ###

    # キャッスルメイン
    def show_catsle(self, cur_y=0):
        self.scene = 2
        Window.close()
        Sounds.bgm("wiz-catsle")
        self.show_place(None)
        texts = [
            " ギルガメッシュのさかば",
            " ボルタックしょうてん",
            " カントじいん",
            " くんれんじょう",
            " ちかめいきゅう",
        ]
        Window.open("catsle", 10, 13, 21, 17, texts).add_cursol().cur_y = cur_y

    # キャッスル内の場所
    def show_place(self, parm):
        if parm == 0:
            place = "ギルガメッシュのさかば"
        elif parm == 1:
            place = "ボルタックしょうてん"
        elif parm == 2:
            place = "カントじいん"
        elif parm == 3:
            place = "くんれんじょう"
        else:
            place = "キャッスル"
        bef_spc = (12 - len(place)) // 2
        aft_spc = (13 - len(place)) // 2
        Window.open(
            "place", 10, 1, 21, 1, f"{' ' * bef_spc}{place}{' ' * aft_spc}"
        ).parm = parm

    # ギルガメッシュのさかば：メイン
    def show_bar(self):
        win_old = Window.get("bar")
        win_new = Window.get("bar_new")
        members_new = win_new.values if win_new else []
        texts_old = []
        texts_new = []
        values = []
        values_excluded = []
        exclude_nature = None
        for member in members_new:
            if member.nature in [1, 3]:
                exclude_nature = 4 - member.nature
        for member in self.members + self.reserves:
            if not member in members_new:
                if member.nature != exclude_nature:
                    texts_old.append(member.text_catsle)
                    values.append(member)
                else:
                    values_excluded.append(member)
        if not win_old:
            Window.open("bar", 4, 3, 28, 12, texts_old).add_cursol().values = values
            Window.open("bar_new", 4, 14, 28, 18, texts_new).values = []
        else:
            if len(win_new.values) > 0:
                texts_old.append(" (へんせいを おえる)")
            win_old.texts = texts_old
            win_old.values = values
            win_old.parm = values_excluded
            win_old.add_cursol()
            for member in win_new.values:
                texts_new.append(member.text_catsle)
            win_new.texts = texts_new

    # ボルタックしょうてん：メイン
    def show_shop(self):
        if not Window.get("shop_buysell"):
            Window.open("shop_buysell", 2, 3, 10, 3, [" かう   うる"]).add_cursol(
                [0], [0, 5]
            )
        Window.open("shop_gold", 13, 3, 29, 3, [f"しょじきん:{util.pad(self.gold,6)} Gold"])

    # ボルタックしょうてん：買う
    def show_shop_buy(self):
        texts = []
        values = []
        for item in Item.all():
            if item.stocks or item.id in self.stocks:
                values.append(item)
                texts.append(f" {util.spacing(item.name, 11)}")
        Window.open("shop_buy", 2, 5, 15, 16, texts).add_cursol().values = values

    # ボルタックしょうてん：お店ガイド
    def show_shop_guide(self):
        win = Window.get("shop_buy")
        item = win.values[win.cur_y]
        Window.open(
            "shop_guide", 17, 5, 29, 16, item.details(True, self.items.count(item.id))
        )

    # ボルタックしょうてん：売る
    def show_shop_sell(self):
        texts = []
        for id in self.items:
            item = Item(id)
            texts.append(
                f" {util.spacing(item.name, 11)}       {util.pad(item.price//2, 6)}"
            )
        Window.open("shop_sell", 2, 5, 29, 16, texts).add_cursol()

    # ボルタックしょうてん：メッセージ
    def show_shop_msg(self, msg, parm=None):
        Window.open("shop_msg", 2, 18, 29, 19, msg).parm = parm

    # カントじいん：メイン
    def show_temple(self, msg):
        Window.open("select_members_mes", 4, 18, 28, 18, msg)
        win = self.show_select_members(None, 4, 3)
        return win

    # カントじいん：おかね欄
    def show_temple_gold(self, gold):
        texts = ["Gold", util.pad(self.gold, 6)]
        if gold:
            texts += ["", "きふきん", util.pad(gold, 6)]
        Window.open("temple_gold", 23, 3, 28, 7, texts)

    # くんれんじょうメイン
    def show_training(self, cur_y=None):
        self.scene = 3
        Sounds.bgm("wiz-edge")
        self.show_place("くんれんじょう")
        texts = [
            " キャラクターを つくる",
            " キャラクターを けす",
            " なまえを かえる",
            " しょくぎょうを かえる",
            " しろに もどる",
        ]
        win = Window.open("training", 10, 13, 21, 17, texts).add_cursol()
        if not cur_y is None:
            win.cur_y = cur_y

    # くんれんじょう キャラクターをつくる
    def show_training_new(self):
        win = Window.get("training_new")
        win_nat = Window.get("training_nature")
        if not self.members:
            if not Window.get("training_tutorial"):
                texts = [
                    " はじめに キャラクターをとうろくしてください。",
                    " Finardyのパーティは 5にんへんせいです。",
                    " 4・5にんめはこうえいで、せっきんせんができません。",
                    "",
                    " はじめてプレイするばあいは 「せんし・せんし・とうぞく・",
                    " そうりょ・まほうつかい」 がおすすめです。",
                ]
                Window.open("training_tutorial", 1, 13, 30, 18, texts)

        if not win or win.parm is None:
            texts = ["しょくぎょうを えらんでください", "", "", "", "", "", "", "", ""]
            for job_id in [1, 2, 3, 4]:
                texts[2] += f" {Job(job_id).name}"
            Window.open("training_new", 1, 3, 30, 11, texts).add_cursol(
                [2], [0, 7, 14, 21]
            )
        elif not win_nat:
            texts = ["せいかくを えらんでください", "", "", "", "", ""]
            values = []
            cur_pos_y = []
            for nature in [1, 2, 3]:
                if nature in Job(win.parm).nature:
                    pos_y = 2 + len(cur_pos_y)
                    texts[pos_y] = " " + const["nature"][nature - 1]
                    values.append(nature)
                    cur_pos_y.append(pos_y)
            texts += [
                " せいかくによって なれるしょくぎょうが かわります。",
                " 「ぜん」と「あく」のキャラクターは パーティをくめません。",
                " せいかくは こうどうによって かわることがあります。",
            ]
            Window.open("training_nature", 1, 10, 30, 18, texts).add_cursol(
                cur_pos_y
            ).values = values

    # くんれんじょう キャラクターをつくる（職業ガイド）
    def show_training_new_guide(self):
        win = Window.get("training_new")
        win.texts = win.texts[:-2] + Job(win.cur_x + 1).details

    # くんれんじょう キャラクターをつくる（確認）
    def show_training_new_member(self, member):
        texts = member.text_detail
        Window.open("training_new_member", 1, 0, 30, 19, texts).parm = member
        exclude_nature = 0
        for mb in self.members:
            if mb.nature in [1, 3]:
                exclude_nature = 4 - mb.nature
        texts = [" まえにもどる"]
        values = [2]
        if len(self.members) > 0:
            texts = [" くんれんじょうで たいきする"] + texts
            values = [1] + values
        if len(self.members) < 5 and member.nature != exclude_nature:
            texts = [" パーティに くわえる"] + texts
            values = [0] + values
        Window.open(
            "training_new_confirm", 15, 17, 30, 19, texts
        ).add_cursol().values = values

    # くんれんじょう キャラクターをけす
    def show_training_delete(self, msg="どのキャラクターを けしますか？"):
        texts = []
        values = []
        for member in self.reserves:
            texts.append(member.text_catsle)
            values.append(member)
        if len(values):
            Window.open(
                "training_delete", 4, 3, 28, 12, texts
            ).add_cursol().values = values
            Window.open("training_delete_msg", 4, 14, 28, 18, msg).has_cur = None
        else:
            self.show_training(1)
            Window.close(["training_delete", "training_delete_msg"])

    # くんれんじょう なまえ／しょくぎょうを かえる
    def show_training_change(self, parm, cur_member=None):
        win = Window.get("training_change")
        if parm == 0:
            msg = "どのキャラクターの なまえを かえますか？"
        else:
            msg = "どのキャラクターの しょくぎょうを かえますか？"
        texts = []
        values = []
        cur_y = None
        for idx, member in enumerate(self.members + self.reserves):
            if member is cur_member:
                cur_y = idx
            texts.append(member.text_catsle)
            values.append(member)
        if not win:
            win = Window.open("training_change", 4, 3, 28, 12, texts).add_cursol()
            win.values = values
            win.parm = parm  # 0は名前、1は職業
            if not cur_y is None:
                win.cur_y = util.loop(cur_y, 1, len(win.cur_pos_y))
            Window.open("training_change_msg", 4, 14, 28, 18, msg)

    # くんれんじょう 名前入力
    def show_training_name(self, mode=0, member=None):
        texts = []
        values = []
        characters = const["characters"][mode]
        for line in characters:
            text = ""
            for c in line:
                if c == "A":
                    text += " カナ"
                elif c == "B":
                    text += " かな"
                elif c == "E":
                    text += " おわり"
                elif c != "/":
                    text += f" {c}"
                values.append(c)
            texts.append(text)
            texts.append("")
        win = Window.open("training_name", 4, 5, 28, 18, texts[:-1])
        win.add_cursol(
            [i * 2 for i in range(len(characters))], [i * 2 for i in range(12)]
        )
        win.values = values
        if member:
            win.parm = member

    # くんれんじょう 名前変更ガイド
    def show_training_name_guide(self):
        win = Window.get("training_name_guide")
        text = "あたらしい なまえは: "
        if win:
            name = win.parm
            if len(name) < 6 and px.frame_count % 30 < 15:
                name += "■"
            win.texts = [f"{text + name}"]
        else:
            Window.open("training_name_guide", 4, 3, 28, 3, text).parm = ""

    # くんれんじょう 職業変更
    def show_training_job(self, member=None):
        texts = []
        values = []
        for job in Job.all():
            if member.nature in job.nature:
                texts.append(f" {job.name}")
                values.append(job)
        win = Window.open("training_job", 2, 7, 8, 12, texts).add_cursol()
        win.values = values
        if member:
            win.parm = member
        texts = [
            f"     {member.name}  {member.class_s}  LV{member.lv}",
            "     どのしょくぎょうに てんしょくしますか？",
        ]
        Window.open("training_job_old", 2, 4, 29, 5, texts).parm = member

    # くんれんじょう 職業変更ガイド
    def show_training_job_guide(self):
        win = Window.get("training_job")
        texts = ["    ひつような のうりょくち（げんざいち）", "", "", "", "", "", ""]
        parm = False
        if win:
            job = win.cur_value
            member = win.parm
            if job.str:
                texts[1] = f"     ちから     {job.str} ({member.str})"
            if job.spd:
                texts[2] = f"     すばやさ    {job.spd} ({member.spd})"
            if job.vit:
                texts[3] = f"     せいめいりょく {job.vit} ({member.vit})"
            if job.int:
                texts[4] = f"     ちえ      {job.int} ({member.int})"
            if job.pie:
                texts[5] = f"     しんこうしん  {job.pie} ({member.pie})"
            texts += job.details
            texts.append("")
            if job.id == member.job_id:
                texts.append(" # げんざいの しょくぎょうです #")
            elif not job.id in member.selectable_jobs:
                texts.append(" # のうりょくちが たりません #")
            elif member.lv <= 1:
                texts.append(" # レベル1は てんしょくできません #")
            else:
                texts.append(" [けっていボタンで てんしょくします]")
                parm = True
        Window.open("training_job_guide", 7, 7, 29, 17, texts).parm = parm

    # 宝箱メンバー一覧
    def show_treasure_members(self):
        texts = []
        values = []
        self.members = copy.deepcopy(self.battle.members)
        for mb in self.members:
            texts += [
                f"     {util.spacing(mb.name,6)} LV {mb.lv}",
                f"     HP {util.pad(mb.hp,3)}/{mb.status()}",
                "",
            ]
            values.append(px.rndi(0, 99))
        texts = texts[:-1]
        win = Window.get("treasure_members")
        if win:
            win.texts = texts
        else:
            Window.open("treasure_members", 13, 4, 30, 17, texts).values = values

    ### イベント処理 ###

    # シーンチェンジ
    def change_scene(self, scene):
        Window.close()
        # 戦闘のときはロールアウト済みなのでフェードインから
        Fade.start(scene != 1)
        self.next_scene = scene

    # 一歩歩いた
    def moved(self):
        pl = self.player
        pl.moved = False
        location = f"{pl.x},{pl.y},{pl.z}"
        # 毒とヒーリング
        for member in self.members:
            health = member.health
            if health < 4:
                member.heal_and_poison()
            if health == 2 and member.vit // 9 > px.rndi(0, 255):
                member.health = 0
            if health != member.health:
                self.set_members_pos()
                return
        # ミルワ歩数減少
        if pl.light > 0:
            pl.light -= 1
            if pl.light == 0:
                Window.message("disapper-light")
        # ターン床
        if pl.cell == "t":
            pl.turn_cnt = px.rndi(2, 5)
            return
        elif pl.cell == "p":
            Sounds.sound(12)
            Window.popup("おとしあな！")
            for member in self.members:
                health = member.health
                member.lost_hp(px.rndi(3, 6))
                if health != member.health:
                    self.set_members_pos()
            return
        # イベント
        for key in self.events:
            if key == location:
                if self.do_event(self.events[key].split(",")):
                    pl.reset_move()
                    return
        # エンカウント
        self.encount += px.rndi(1, 4)
        chamber_encount = None
        if location in chambers_master:
            if not location in self.chambers or not self.chambers[location]:
                chamber_encount = location
        if self.encount > 100 or chamber_encount:
            # self.battle = Battle(None, chamber_encount, self.members, self.items, 52)
            self.battle = Battle(pl.z + 1, chamber_encount, self.members, self.items)
            self.start_battle()
            return

    # イベント起動
    def do_event(self, values):
        pl = self.player
        if values[0] in ("up", "down"):
            Window.message(values[0])
            Window.selector("yn", ("move", values[1], values[2], values[3]))
        elif values[0] == "move":
            z = int(values[3])
            if z < 0:  # 街へ
                self.go_catsle()
            else:
                sid = 5 if pl.cell in "<>" else None
                self.set_position(int(values[1]), int(values[2]), z, sid)
        elif values[0] == "ev":
            Window.message(values[0])
            win = Window.selector(values[0], values[1])
            for idx, z in enumerate(win.values):
                if pl.z == z:
                    win.cur_y = idx
        elif values[0] == "fall":
            Window.popup("シュート！").parm = values
        elif values[0] == "msg":
            # 個別イベント回避
            if values[1] == "b1-3" and 14 in self.items:
                return False
            elif values[1] in ("b1-4", "b2-1") and 13 in self.items:
                return False
            elif values[1] in ("b1-6", "b2-3") and 12 in self.items:
                return False
            elif values[1] in ("b2-2", "b2-5", "b4-1") and 10 in self.items:
                return False
            elif values[1] in ("b2-4", "b2-6") and 11 in self.items:
                return False
            elif values[1] in ("b2-7") and 14 in self.items:
                return False
            elif values[1] in ("b4-4", "b4-9", "b4-10") and 15 in self.items:
                return False
            elif values[1] == "b4-2" and self.has_item(77):
                values[1] = "b4-2w"
            elif values[1] in ("b4-6"):
                if pl.dir != 0:
                    return False
                else:
                    Sounds.sound(14)
            Window.message(values[1]).parm = values[1]
        elif values[0] == "battle":
            location = f"{pl.x},{pl.y},{pl.z}"
            if location in self.chambers:
                return False
            seed = int(values[1])
            if seed == 60 and self.has_item(77):
                return  # ワードナ不在
            self.battle = Battle(False, location, self.members, self.items, seed)
            self.start_battle()
        return True

    # はい・いいえ選択
    def select_yn(self, parm, answer):
        Window.close()
        print(parm)
        if answer:
            if parm[0] == "move":
                self.do_event(parm)
            elif parm[0] == "item":
                item = Item(parm[1])
                Window.message([f"{item.name} をてにいれた"])
                self.add_item(item)
            elif parm == "new_game":
                Userdata.open_guide()
        if parm == "new_game":
            self.start_new_game()

    ### マップ関連 ###

    # マップ移動
    def set_position(self, x, y, z=None, sound_id=None):
        Fade.start(True)
        self.next_x = x
        self.next_y = y
        self.next_z = self.player.z if z is None else z
        if not sound_id is None:  # 移動音（階段など）
            Sounds.sound(sound_id)
        if Sounds.cur_music == None and self.scene == 0:
            self.map_bgm()

    # マップ切り替え
    def change_map(self):
        if px.play_pos(3) is None or px.play_pos(0) is None:
            if Sounds.next_music and not Sounds.nocut:
                Sounds.bgm(Sounds.next_music)
            pl = self.player
            pl.x = self.next_x
            pl.y = self.next_y
            if pl.z != self.next_z:
                pl.z = self.next_z
                self.reset_chambers()
            pl.mapped[pl.z][pl.y][pl.x] = 2
            pl.reset_move()
            self.next_z = None
            if self.next_event == True:
                self.moved()
                self.next_event = False

    # 透明モードセット（デュマピック、マロール）
    def set_transparent(self, member, spell_id, item_id):
        pl = self.player
        Window.close()
        self.menu_visible = False
        pl.chr = None
        warp = spell_id == 18
        self.saved_entity = {
            "x": pl.x,
            "y": pl.y,
            "member": member,
            "spell_id": spell_id,
            "item_id": item_id,
            "warp": warp,
        }
        if warp:
            text = "テレポートしたいばしょをえらんで けっていボタン"
        else:
            text = "ちずのかくにんをおえたら けっていボタン"
        Window.open("msg_transparent", 2, 0, 29, 0, text)

    # 透明モード解除
    def release_transparent(self, confirmed):
        Window.close()
        pl = self.player
        pl.sx = 0
        pl.sy = 0
        self.set_members_pos()
        member = self.saved_entity["member"]
        if confirmed:
            item_id = self.saved_entity["item_id"]
            if item_id:
                self.brake_item(item_id, None)
            else:
                spell = Spell(self.saved_entity["spell_id"])
                member.mp[spell.lv] -= 1
        if self.saved_entity["warp"] and confirmed:
            Sounds.sound(8)
            self.map_bgm()
            pl.moved = True
        else:
            pl.x = self.saved_entity["x"]
            pl.y = self.saved_entity["y"]
            self.show_menu(1)

    # マップBGMを流す
    def map_bgm(self):
        Sounds.bgm("wiz-dungeon", tick=self.next_music_tick)

    # 城へ
    def go_catsle(self, snd_id=5):
        Window.close()
        # 善悪混在時の処理
        first_nature = self.members[0].nature
        exclude_nature = 4 - first_nature if first_nature in (1, 3) else 0
        members = []
        for member in self.members:
            if member.nature == exclude_nature:
                self.reserves.append(member)
            else:
                members.append(member)
        self.members = members
        self.set_position(1, 39, -1)
        if not snd_id is None:
            Sounds.sound(snd_id, "wiz-catsle")
        self.player.light = 0
        # 自動回復
        changed = True
        while changed:
            changed = False
            cure_petrifaction = False
            cure_dead = False
            for member in self.members + self.reserves:
                member.poison = 0
                if member.health < 3:
                    member.recover()
                    cure_petrifaction = cure_petrifaction or 31 in member.spells
                    cure_dead = cure_dead or 28 in member.spells
            for member in self.members:
                if member.health == 3 and cure_petrifaction:
                    member.recover()
                    changed = True
                if member.health == 4 and cure_dead:
                    member.recover()
                    changed = False
        self.set_members_pos()
        self.reset_chambers()
        if self.has_item(77):
            for mb in self.members + self.reserves:
                if mb.imperial:
                    self.change_scene(2)
                    break
            else:
                self.change_scene(4)
        else:
            self.change_scene(2)

    # ランダムワープ（戦闘中マロール、宝箱テレポート）
    def teleport(self, sound_id=8):
        pl = self.player
        if pl.z == 5:  # B6Fは入り口に戻される
            x, y = 1, 39
        else:
            while True:
                x, y = px.rndi(0, 39), px.rndi(0, 39)
                if pl.map_cells[pl.z][y][x] == " ":
                    break
        self.end_battle()
        self.set_position(x, y, None, sound_id)

    # 玄室データ初期化
    def reset_chambers(self):
        chambers = {}
        for key in chambers_master:
            chambers[key] = False
        self.chambers = chambers

    # 戦闘開始
    def start_battle(self):
        bgm = "wiz-battle2" if self.battle.seed == 60 else "wiz-battle1"
        Sounds.cur_music = None
        self.next_music_tick = 0
        Sounds.bgm("wiz-encount", False, bgm)
        self.rollout = 1
        self.encount = 0
        # 戦闘後移動の防止
        self.player.dx = 0
        self.player.dy = 0

    # 戦闘終了
    def end_battle(self, is_run=False):
        bt = self.battle
        if bt.chamber_encount and not is_run:
            self.chambers[bt.chamber_encount] = True
        self.members = copy.deepcopy(bt.members)
        for mb in self.members:
            mb.ac_tmp = 0
            mb.health = 0 if mb.health == 1 else mb.health
            mb.silent = False
        self.set_members_pos()
        self.change_scene(0)
        if bt.seed == 60 and bt.completed:
            self.select_yn(("item", 77), True)
        self.battle = None

    # 罠にかかった
    def do_trap(self, trap):
        win = Window.get("treasure_msg")
        win.texts = [f"おおっと！ {const['traps'][trap]}"]
        if trap == 8:
            Sounds.sound(14)
        win.parm = True

    def get_treasure(self, down=0):
        tr = self.battle.treasure
        win_img = Window.get("treasure_img")
        win_msg = Window.get("treasure_msg")
        rewards = []
        for _ in range(2):
            tg = tr.treasure_group[px.rndi(0, 3)] - down
            if tg > 0 and len(self.items) < 40:
                items = [item for item in Item.all() if item.treasure_group == tg]
                while True:
                    item = items[px.rndi(0, len(items) - 1)]
                    # 非売品かつ売ったアイテムは出現率が下がる
                    if not item.id in self.stocks or px.rndi(0, 3) == 0:
                        break
                rewards.append(f" {item.name}")
                self.add_item(item)
            else:
                gold = self.add_gold(self.battle.total_gold, 0.4)
                rewards.append(f" {gold}G")
                break
        win_msg.texts = ["たからばこのなかには:", " と".join(rewards)]
        win_img.parm = 1

    # 全滅？
    @property
    def no_living(self):
        exist_living = False
        for member in self.members:
            exist_living = exist_living or (member.health < 2)
        return not exist_living


App()
