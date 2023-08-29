import pyxel as px
import copy
import util
from window import Window
from monster import Monster
from treasure import Treasure
from item import Item
from spell import Spell
from sounds import Sounds

const = util.load_json("data/const")
LIST_DY = (0, 0, 0, 4, 6, 6, 4, 0, 8, 14, 18, 20, 18, 14, 8, 2)


class Battle:
    def __init__(self, floor, chamber_encount, members, items, seed_id=None):
        monsters = []
        seed = None
        while len(monsters) < 5:
            if seed is None:
                if seed_id:
                    id = seed_id
                else:
                    ms_in_floor = [ms.id for ms in Monster.all() if ms.floor == floor]
                    id = ms_in_floor[px.rndi(0, len(ms_in_floor) - 1)]
            elif seed.follow_rate >= px.rndi(0, 255):
                id = seed.following
            else:
                break
            seed = Monster(id)
            counts = min(px.rndi(1, seed.counts), 5 - len(monsters))
            for _ in range(counts):
                monsters.append(Monster(id, len(monsters)))
        for ms in monsters:
            ms.slide -= [6, 5, 3, 2, 0][len(monsters) - 1]
        self.state = 0
        self.members = copy.deepcopy(members)
        self.members_vanguard_idxs = self.members_idxs(True, True)  # 何人目まで前衛？
        for mb in self.members:
            mb.fx = None
        self.phase = None
        self.commands = []
        self.actions = None
        self.action = None
        self.monsters_effection = {}
        self.members_effection = {}
        self.selected_member = None
        self.selected_monster = None
        self.selector_items = None
        self.win_motion = 0
        self.monsters = monsters
        self.items = items
        self.saved_msg = 0
        self.total_exp = 0
        self.total_gold = 0
        self.wait = 0
        self.flash = None
        self.warp = 0
        self.warp_fx = 0
        self.seed = seed_id
        self.chamber_encount = chamber_encount
        self.floor = floor
        if chamber_encount:
            print("玄室エンカウント")
            tg = monsters[0].treasure
            self.treasure = Treasure(tg) if tg else None
        else:
            self.treasure = None
        # 不意打ち・先制判定
        self.preemptive = False
        self.suprise = False
        self.notified = False
        self.is_friendly = False
        if seed_id is None:  # 固定エンカでは先制等は発生させない
            factor = 0.0
            for mb in members:
                add_spd = 6 if mb.job_id == 2 else 0
                factor += (mb.spd + add_spd - 9) / len(members)
            for ms in monsters:
                factor -= (6 - ms.ac // 2) / len(monsters)
            print(f"先制/不意打ち判定変数:{factor}")
            if max(factor / 2, 0) + 1 > px.rndi(0, 19):
                self.preemptive = True
            elif max(-factor / 2, 0) + 1 > px.rndi(0, 19):
                self.suprise = True
            elif not 3 in monsters[0].resist and 1 > px.rndi(0, 9):
                self.is_friendly = True

    @property
    def completed(self):
        for monster in self.monsters:
            if monster.is_live or monster.show:
                return False
        else:
            return True

    @property
    def defeated(self):
        for monster in self.monsters:
            if monster.is_live:
                return False
        else:
            return True

    # バトルメイン
    def update(self, pressed):
        self.show_main()
        # ウエイト処理
        if self.wait:
            self.wait -= 1
            return
        # 全滅判定
        idxs = self.members_idxs()
        if not idxs:  # 全滅
            self.message("ぜんめつした", "gameover")
            return
        # 全滅時のアニメーション待ち
        if self.defeated:
            return
        # メンバーの戻りアクション待ち
        for mb in self.members:
            if mb.fx and mb.fx[0] == "backward":
                return
        # 先制・不意打ちメッセージ
        if not self.notified:
            if self.suprise:
                self.message("モンスターは とつぜん おそいかかってきた！", "notify")
            elif self.preemptive:
                self.message("モンスターはまだ こちらに きづいていない！", "notify")
            elif self.is_friendly:
                self.message("ゆうこうてきな モンスター", "friendly")
            self.notified = True
        # 行動順番の決定
        if self.phase == "action" and self.actions is None:
            orders = []
            for idx, mb in enumerate(self.members):
                if idx < len(self.commands) and mb.health == 0:
                    spd = mb.spd - 9 + px.rndi(0, 9)
                    orders.append({"type": 0, "idx": idx, "spd": spd})
                    # 味方の防御は最初にモーション発動
                    if self.commands[idx]["action"] == 2:
                        mb.fx = ["guard", 1]
            if not self.preemptive:  # 先制攻撃
                for idx, ms in enumerate(self.monsters):
                    if ms.is_live and not ms.sleeping:
                        spd = 6 - ms.ac // 2 + px.rndi(0, 9)
                        can_atc = idx in self.monsters_idxs(True)
                        orders.append(
                            {"type": 1, "idx": idx, "spd": spd, "can_atc": can_atc}
                        )
            self.actions = sorted(orders, key=lambda order: order["spd"], reverse=True)
            self.end_action()
        # 実行動
        if self.action:
            if self.action["type"] == 0:
                self.member_action()
            elif self.action["type"] == 1:  # 敵キャラの行動
                self.monster_action()
        # actionsが空＝ターン頭へ
        if self.actions is None and self.phase:
            self.phase = None
            self.suprise = False
            self.preemptive = False
            # ガードモーションを解く、睡眠回復、毒
            for idx, mb in enumerate(self.members):
                if mb.fx and mb.fx[0] == "guard":
                    mb.fx = None
                if mb.health == 1 and px.rndi(0, 5) < 2:
                    mb.health = 0
                damage = 0
                if mb.poison:
                    damage += -(-mb.mhp // 16)
                if mb.healing and mb.health < 4:
                    damage -= mb.healing
                if damage > 0:
                    mb.lost_hp(damage)
                    self.members_effection[idx] = {
                        "damage": damage,
                        "fx_type": "damage",
                        "fx_len": 16,
                    }
                elif damage < 0:
                    mb.add_hp(-damage)
                    self.members_effection[idx] = {
                        "cure": -damage,
                        "fx_type": "cure",
                        "fx_len": 16,
                    }
            for ms in self.monsters:
                ms.sleeping = max(ms.sleeping - 1, 0)
        # ターン頭のボタンプレス待ち
        if (
            not self.phase
            and pressed
            and not self.defeated
            and not Window.get("battle_popover")
        ):
            self.start_turn()

    # 自キャラの行動
    def member_action(self):
        mb_idx = self.action["idx"]
        mb = self.members[mb_idx]
        if mb.health:  # 状態異常ならとばす
            self.end_action()
            return
        cmd = self.commands[mb_idx]
        ms = None
        if not cmd["target"] is None and cmd["target"] >= 0:
            ms = self.monsters[cmd["target"]]
            if not ms.is_live:  # ターゲット変更
                self.set_selector_monsters(True)
                ms = self.monsters[self.selected_monster]
                self.selected_monster = None
                cmd["target"] = ms.idx
        # 行動開始
        if cmd["action"] in (0, 3, 4, 5, 6):
            if not mb.fx:
                self.move_forward(mb_idx)
        elif cmd["action"] == 2:  # みをまもる
            self.end_action()
        if not mb.fx:
            return
        # 前進〜行動開始
        if mb.fx[0] == "forward":
            if mb.fx[1] < self.get_dist(mb_idx):  # 移動待ち
                return
            print(f"{mb.name}の行動 spd={self.action['spd']}")
            print("command:", self.commands[mb_idx])
            if cmd["action"] == 0:  # 攻撃
                rate_all = mb.hit
                blows = 0
                damage = 0
                scale = 2 if mb.weapon.tribe == ms.tribe else 1
                critical = False
                print(f"攻撃:{mb.atc} 命中率:{rate_all}  敵のAC:{ms.ac} 倍率:{scale}")
                while rate_all > 0:
                    rate_use = min(rate_all, 20)
                    hit_real = 20 if ms.sleeping else rate_use - 10 + ms.ac
                    if (scale > 1 or mb.weapon.id == 42) and not blows:
                        hit_real = 20  # 弱点属性/しゅりけんは必ず1回あたる
                    if hit_real > px.rndi(0, 19):
                        blows += 1
                        damage += int(mb.atc * scale * px.rndf(1.0, 2.0))
                        if mb.job_id == 8 and 2 > px.rndi(0, 9) and not 11 in ms.resist:
                            critical = True
                    rate_all -= rate_use
                blows_fx = util.maxmin(blows, 4, 1)
                if mb.weapon.id == 42:
                    mb.fx = ["attack", 5 + blows_fx * 2, blows_fx, ms]
                else:
                    mb.fx = ["attack", blows_fx * 4, blows > 0]
                self.monsters_effection[ms.idx] = {
                    "action": "damage",
                    "blows": blows,
                    "damage": damage,
                    "is_weak": scale > 1,
                    "critical": critical,
                    "fx_type": "injured",
                    "fx_pat": mb.weapon.img_dmg,
                    "fx_len": blows_fx * 4,
                }
            elif cmd["action"] == 3:  # 呪文
                spell = cmd["spell"]
                self.popover(f"{mb.name}は {spell.name}をとなえた")
                if mb.silent:
                    fx_len = 6
                else:
                    fx_len = 18
                    mb.mp[spell.lv] -= 1
                    Sounds.sound(19)
                mb.fx = ["spell_start", fx_len, not mb.silent]
            elif cmd["action"] == 4:  # ディスペル
                mb.fx = ["dispell", 12]
            elif cmd["action"] == 5:  # しきべつ
                Sounds.sound(20)
                mb.fx = ["identify", 18]
                self.monsters_effection[ms.idx] = {
                    "action": None,
                    "fx_type": "identify",
                    "fx_len": 18,
                }
            elif cmd["action"] == 6:  # アイテム
                item = cmd["item"]
                self.popover(f"{mb.name}は {item.name}をつかった")
                if item.brake:
                    self.items.pop(self.items.index(item.id))
                    self.items.sort()
                cmd["spell"] = Spell(item.use)
                mb.fx = ["spell_start", 6, False]
        # 攻撃発動〜完了
        elif mb.fx[0] == "attack" and mb.fx[1] == 0:
            mse = self.monsters_effection[ms.idx]
            if mse["fx_type"] == "injured":
                mse["fx_type"] = "damage"
                mse["fx_len"] = 16
            elif mse["fx_len"] == 0:
                self.apply_members_effection(mb_idx)
        # ディスペル〜完了
        elif mb.fx[0] == "dispell" and mb.fx[1] == 0:
            cnt = 0
            for ms in self.monsters:
                rate = max(10 + mb.lv - 2 * ms.lv, 1)
                print(f"ディスペル成功率:{rate}")
                if ms.is_live and ms.tribe == 3 and rate > px.rndi(0, 19):
                    cnt += 1
                    self.kill_monster(ms, True)
            if cnt:
                self.popover(f"{cnt}たいのモンスターの のろいをといた")
            self.apply_members_effection(mb_idx)
        # しきべつ〜完了
        elif mb.fx[0] == "identify" and mb.fx[1] == 0:
            str_evil = " / じゃあくなせいしつ" if 3 in ms.resist else ""
            str_weak = ""
            for attr in (1, 2, 4, 5):
                if (attr == 5 and attr in ms.resist) or (
                    attr != 5 and not attr in ms.resist
                ):
                    str_weak += const["attr"][attr] + " "
            texts = [
                f"レベル {ms.lv} / HP {ms.hp}",
                f"{const['tribe'][ms.tribe]}{str_evil}",
            ]
            if str_weak:
                texts.append(f"{str_weak}がゆうこう")
            if ms.nullify:
                texts.append(f"じゅもんが ききづらい")
            self.message(texts)
            self.apply_members_effection(mb_idx)
        # 呪文発動〜完了
        elif (
            mb.fx[0] in ("spell_start", "spell_volume", "spell_done") and mb.fx[1] == 0
        ):
            if mb.silent and cmd["action"] != 6:
                self.popover("じゅもんは ふうじられている")
                self.wait = 12
                self.apply_members_effection(mb_idx)
            elif mb.fx[0] == "spell_start":
                self.member_spell(mb, cmd)
            elif mb.fx[0] == "spell_volume":
                fx_len = 0
                for idx in self.members_effection:
                    mbe = self.members_effection[idx]
                    if mbe["action"] == "cure":
                        mbe["fx_type"] = "cure"
                        mbe["fx_len"] = 16
                        fx_len = 16
                for idx in self.monsters_effection:
                    ms = self.monsters[idx]
                    mse = self.monsters_effection[idx]
                    if mse["action"] == "damage":
                        mse["fx_type"] = "damage"
                        mse["fx_len"] = 16
                        mse["blows"] = 0
                        fx_len = 16
                mb.fx = ["spell_done", fx_len]
            # 呪文完了(mb.fx[1] == 0はダメージ不発時の考慮)
            if mb.fx[0] == "spell_done" and mb.fx[1] == 0:
                self.apply_members_effection(mb_idx)

    # 自キャラ呪文
    def member_spell(self, mb, cmd):
        spell = cmd["spell"]
        fx_len = 6
        sound_id = None
        for idx in self.members_idxs(False, True):
            target = self.members[idx]
            if cmd["members"] in (idx, -1) and target.health < 4:
                sound_id = spell.sound
                if spell.id in (19, 25):
                    self.members_effection[idx] = {
                        "action": "cure",
                        "cure": spell.cure(),
                    }
                elif spell.id == 31:  # マディ
                    self.members_effection[idx] = {
                        "action": "cure",
                        "cure_poison": True,
                        "cure_health": 3,
                        "cure": target.mhp - target.hp,
                    }
                elif spell.id == 22:  # ディアルコ
                    self.members_effection[idx] = {
                        "action": "cure",
                        "cure_health": 2,
                        "cure": 0,
                    }
                elif spell.id == 27:  # ラテュモフィス
                    self.members_effection[idx] = {
                        "action": "cure",
                        "cure_poison": True,
                        "cure": 0,
                    }
                elif spell.id in (3, 9) and target.health < 3:
                    self.members_effection[idx] = {
                        "action": "shield",
                        "shield": spell.intensity,
                    }
                elif spell.id in (18, 36):  # マロール、ロクトフェイト
                    self.members_effection[idx] = {
                        "action": "warp",
                        "warp": 1 if spell.id == 18 else 2,
                    }
                if idx in self.members_effection:
                    self.members_effection[idx]["fx_type"] = spell.fx
                    self.members_effection[idx]["fx_len"] = spell.fx_len
        for idx in self.monsters_idxs():
            if cmd["target"] in (idx, -1):
                ms = self.monsters[idx]
                if ms.nullify > px.rndi(0, 255):
                    print("無効化した")
                    self.monsters_effection[idx] = {
                        "action": None,
                        "fx_type": "nullify",
                        "fx_len": 18,
                    }
                elif spell.attr in (1, 2, 3):
                    sound_id = spell.sound
                    self.monsters_effection[idx] = {
                        "action": "damage",
                        "damage": spell.damage(ms),
                        "critical": False,
                    }
                elif spell.attr in (0, 4, 5, 6, 11):  # ステータス異常系
                    if spell.success(mb, ms):
                        sound_id = spell.sound
                        if spell.id == 2:
                            self.monsters_effection[idx] = {
                                "action": "sleep",
                                "sleeping": px.rndi(1, 3),
                            }
                        elif spell.id == 23:
                            self.monsters_effection[idx] = {
                                "action": "silent",
                            }
                        elif spell.id in (5, 8, 14):
                            self.monsters_effection[idx] = {
                                "action": "unshield",
                                "unshield": spell.intensity,
                            }
                            fx_len = max(fx_len, 18)
                        elif spell.id in (12, 15, 17, 29):
                            self.monsters_effection[idx] = {
                                "action": "choke",
                            }
                        elif spell.id == 32:
                            self.monsters_effection[idx] = {
                                "action": "damage",
                                "damage": ms.hp - 1,
                                "critical": False,
                            }
                    else:
                        self.monsters_effection[idx] = {
                            "action": None,
                            "fx_type": "miss",
                            "fx_len": 16,
                        }
                if idx in self.monsters_effection:
                    mse = self.monsters_effection[idx]
                    if mse["action"]:
                        mse["fx_type"] = spell.fx
                        mse["fx_len"] = spell.fx_len
                    fx_len = max(mse["fx_len"], fx_len)
        mb.fx = ["spell_volume", fx_len]
        if sound_id:
            Sounds.sound(sound_id)

    # 自キャラの行動結果反映
    def apply_members_effection(self, mb_idx):
        sounded = False
        for idx in self.members_effection:
            mb = self.members[idx]
            mbe = self.members_effection[idx]
            if "cure" in mbe:
                mb.add_hp(mbe["cure"])
            if "shield" in mbe:
                # -10より小さくならないように抑える
                mb.ac_tmp = max(mb.ac_tmp - mbe["shield"], -10 - mb.ac + mb.ac_tmp)
                print(f"変更後のAC:{mb.ac}({mb.ac_tmp}))")
            if "cure_poison" in mbe:
                mb.poison = 0
            if "cure_health" in mbe:
                if mb.health <= mbe["cure_health"]:
                    mb.health = 0
            if "warp" in mbe:
                self.warp = mbe["warp"]
        for idx in self.monsters_effection:
            ms = self.monsters[idx]
            mse = self.monsters_effection[idx]
            if mse["action"] == "damage":
                ms.hp -= mse["damage"]
                if ms.hp > 0 and mse["critical"]:
                    self.popover(f"{ms.name}を いちげきでしとめた！")
                    ms.hp = 0
                if ms.hp <= 0:
                    if not sounded:
                        Sounds.sound(10)
                        sounded = True
                    self.kill_monster(ms)
            elif mse["action"] == "unshield":
                ms.ac += mse["unshield"]
                print("変更後のAC:", ms.ac)
            elif mse["action"] == "sleep":
                ms.sleeping = max(ms.sleeping, mse["sleeping"])
            elif mse["action"] == "silent":
                ms.silent = True
            elif mse["action"] == "choke":
                if not sounded:
                    Sounds.sound(10)
                    sounded = True
                self.kill_monster(ms)
        self.move_backward(mb_idx)
        self.end_action()

    # 敵キャラの行動
    def monster_action(self):
        idx = self.action["idx"]
        ms = self.monsters[idx]
        mse = self.monsters_effection[idx] if idx in self.monsters_effection else None
        if not ms.is_live or ms.sleeping:
            print(f"{ms.name}は行動できない")
            self.end_action()
        # 行動を決定
        elif not "command" in self.action:
            command = None
            if "逃" in ms.actions:
                mslv_sum = 0
                for tmp_ms in self.monsters:
                    if tmp_ms.is_live:
                        mslv_sum += tmp_ms.lv
                mblv_sum = 0
                for tmp_mb in self.members:
                    if tmp_mb.health < 2:
                        mblv_sum += tmp_mb.lv
                print(f"逃走判定　敵LV:{mslv_sum} 味方LV:{mblv_sum}")
                if mslv_sum < mblv_sum and px.rndi(0, 9) < 3:
                    command = "run"
            if not command and "呼" in ms.actions:
                call_idx = px.rndi(0, min(len(self.monsters), 4))
                if (
                    call_idx >= len(self.monsters)
                    or not self.monsters[call_idx].is_live
                ):
                    command = "call"
                    self.action["call"] = call_idx
            if not command and "息" in ms.actions:
                if px.rndi(0, 9) < 5:
                    command = "breath"
            if not command and "毒" in ms.actions:
                if px.rndi(0, 9) < 5:
                    command = "poison"
            if (
                not command
                and not ms.silent
                and (ms.spell_m or ms.spell_p)
                and not self.suprise
            ):
                rate = 5 if self.action["can_atc"] else 10
                print(f"呪文発動判定 確率:{rate}")
                if px.rndi(0, 9) < rate:
                    command = "spell"
            if not command and self.action["can_atc"]:
                command = "attack"
            if command:
                print(f"{ms.name}の行動 spd={self.action['spd']} cmd={command}")
                self.action["command"] = command
                ms.blink = 11
            else:
                self.end_action()
        elif ms.blink:
            return  # 点滅待ち
        elif not mse:
            self.wait = 4
            if self.action["command"] == "attack":  # 攻撃
                mb_idx = self.select_member(True)
                mb = self.members[mb_idx]
                blows = 0
                damage = 0
                guard = (
                    mb_idx < len(self.commands) and self.commands[mb_idx]["action"] == 2
                )
                base_ac = 0 if guard else 10
                ac = base_ac + mb.ac
                scale = 2 if mb.weapon.tribe == ms.tribe else 1
                print(f"攻撃:{ms.atc} 攻撃回数:{ms.hits}  味方のAC:{ac} 軽減率:{scale}")
                additions = {}
                for _ in range(ms.hits):
                    if ac > px.rndi(0, 19) or mb.health:
                        blows += 1
                        damage += int(ms.atc * px.rndf(1.0, 2.0) / scale)
                        for addition in ms.additions:
                            rate = 2
                            if addition == 11:  # 即死
                                rate = 1
                            elif addition == 10:  # 吸収
                                rate = 10
                            if (
                                px.rndi(0, 9) < rate
                                and not addition in mb.resist
                                and scale < 2
                            ):
                                additions[addition] = True
                print(f"{mb.name}に {blows}回ヒット {damage}ダメージ")
                print(f"追加効果:{additions}")
                cure = min(damage, ms.mhp - ms.hp) if 10 in additions else 0
                if cure:
                    self.monsters_effection[ms.idx] = {
                        "fx_type": "cure",
                        "cure": cure,
                        "fx_len": 16,
                    }
                    print(f"mhp:{ms.mhp} hp:{ms.hp} cure:{cure}")
                else:
                    self.monsters_effection[ms.idx] = {"fx_type": "done", "fx_len": 16}
                self.members_effection[mb_idx] = {
                    "action": "damage",
                    "damage": damage,
                    "blows": blows,
                    "additions": additions,
                    "fx_type": "damage",
                    "fx_len": 16,
                }
                if damage:
                    mb.fx = ["damage", 16]
                if blows:
                    Sounds.sound(12)
            elif self.action["command"] == "run":  # 逃走
                self.popover(f"{ms.name}は とうそうした")
                ms.fade = 1
                ms.hp = 0
                self.wait = 18
                self.end_action()
            elif self.action["command"] == "call":  # 仲間を呼ぶ
                call_idx = self.action["call"]
                called = Monster(ms.id, call_idx)
                if call_idx >= len(self.monsters):
                    self.monsters.append(called)
                else:
                    self.monsters[call_idx] = called
                self.monsters_effection[ms.idx] = {"fx_type": "call", "fx_len": 12}
            elif self.action["command"] in ("breath", "poison"):  # ブレス
                is_poison = self.action["command"] == "poison"
                str_breath = "どくのブレス" if is_poison else "ブレス"
                self.popover(f"{ms.name}は {str_breath}をはいた", 18)
                Sounds.sound(10)
                for idx in self.members_idxs():
                    mb = self.members[idx]
                    if mb.health < 3:
                        if is_poison:
                            resist = 7 in mb.resist
                        else:
                            resist = 1 in mb.resist
                        damage = px.rndi((ms.hp + 3) // 4, (ms.hp + 2) // 3)
                        damage = max(damage // (2 if resist else 1), 1)
                        self.members_effection[idx] = {
                            "action": "damage",
                            "damage": damage,
                            "fx_type": "damage",
                            "flash": 2 if is_poison else 4,
                            "fx_len": 16,
                        }
                        if is_poison and px.rndi(0, 5) < 1 and not resist:
                            self.members_effection[idx]["additions"] = [7]
                        mb.fx = ["damage", 16]
                    self.monsters_effection[ms.idx] = {"fx_type": "done", "fx_len": 16}
            elif self.action["command"] == "spell":  # 呪文
                spell_ids = [
                    spell.id
                    for spell in Spell.all()
                    if spell.use_enemy
                    and (
                        (ms.spell_m >= spell.lv + 1 and spell.type == 1)
                        or (ms.spell_p >= spell.lv + 1 and spell.type == 2)
                    )
                ]
                # 下位魔法は使わない＆魔法ローテ
                spell_ids = [
                    id
                    for id in spell_ids
                    if not Spell(id).use_enemy in spell_ids and not id in ms.spelled
                ]
                print(f"使える呪文：{spell_ids}")
                if spell_ids:
                    spell = Spell(spell_ids[px.rndi(0, len(spell_ids) - 1)])
                    print(f"選択した呪文：{spell.name}({spell.id})")
                    ms.spelled.append(spell.id)
                    self.popover(f"{ms.name}は {spell.name}をとなえた")
                    self.action["spell"] = spell
                    self.monsters_effection[ms.idx] = {
                        "fx_type": "spell_start",
                        "fx_len": 6,
                    }
                else:
                    ms.spelled = []  # 選び直し
        # モーション完了
        elif mse["fx_len"] <= 0:
            if mse["fx_type"] in ("done", "cure"):
                self.apply_monsters_effection()
            elif mse["fx_type"] == "call":
                self.popover(f"{ms.name}は なかまをよんだ")
                self.end_action()
            elif mse["fx_type"] == "spell_start":
                self.monster_spell(ms)
            elif mse["fx_type"] == "spell_volume":
                fx_len = 0
                for idx in self.members_effection:
                    mb = self.members[idx]
                    mbe = self.members_effection[idx]
                    if mbe["action"] == "damage":
                        mbe["fx_type"] = "damage"
                        mbe["fx_len"] = 16
                        fx_len = max(fx_len, 16)
                self.monsters_effection[ms.idx] = {"fx_type": "done", "fx_len": fx_len}

    # 攻撃ターゲット決定
    def select_member(self, only_vanguard=False):
        mb_list = self.members_idxs(only_vanguard)
        if not mb_list:  # 全員石化など
            mb_list = self.members_idxs(True, True)
        max_idx = max(self.members_vanguard_idxs)
        while True:
            mb_idx = px.rndi(0, len(self.members) - 1)
            if only_vanguard and mb_idx > px.rndi(0, 5):
                continue  # 前の人のほうが狙われやすい調整
            if mb_idx in mb_list and mb_idx <= max_idx:
                break
        return mb_idx

    # 敵キャラ呪文
    def monster_spell(self, ms):
        spell = self.action["spell"]
        fx_len = 0
        sound_id = None
        target = -1 if spell.target == 4 else self.select_member()
        for idx in self.members_idxs():
            mb = self.members[idx]
            if target in (idx, -1) and mb.health < 3:
                if spell.attr in (1, 2, 3):
                    sound_id = spell.sound
                    self.members_effection[idx] = {
                        "action": "damage",
                        "damage": spell.damage(mb),
                    }
                elif spell.attr in (0, 4, 5, 6, 11):  # ステータス異常系
                    if spell.success(ms, mb):
                        sound_id = spell.sound
                        if spell.id == 2:
                            self.members_effection[idx] = {
                                "action": "sleep",
                                "sleeping": px.rndi(1, 3),
                            }
                        elif spell.id == 23:
                            self.members_effection[idx] = {
                                "action": "silent",
                            }
                        elif spell.id in (5, 8, 14):
                            self.members_effection[idx] = {
                                "action": "unshield",
                                "unshield": spell.intensity,
                            }
                        elif spell.id == 29:
                            self.members_effection[idx] = {
                                "action": "kill",
                            }
                        elif spell.id == 32:
                            self.members_effection[idx] = {
                                "action": "damage",
                                "damage": mb.hp - 1,
                            }
                    else:
                        self.members_effection[idx] = {
                            "action": None,
                            "fx_type": "miss",
                            "fx_len": 16,
                        }
                if idx in self.members_effection:
                    mbe = self.members_effection[idx]
                    if mbe["action"]:
                        mbe["fx_type"] = spell.fx
                        mbe["fx_len"] = spell.fx_len
                    fx_len = max(mbe["fx_len"], fx_len)
        self.monsters_effection[ms.idx] = {"fx_type": "spell_volume", "fx_len": fx_len}
        if sound_id:
            Sounds.sound(sound_id)

    # 敵キャラの行動結果反映
    def apply_monsters_effection(self):
        for idx in self.members_effection:
            mb = self.members[idx]
            mb.fx = None
            if idx < len(self.commands) and self.commands[idx]["action"] == 2:
                mb.fx = ["guard", 1]
            mbe = self.members_effection[idx]
            if mbe["action"] == "damage":
                mb.lost_hp(mbe["damage"])
            elif mbe["action"] == "unshield":
                mb.ac_tmp += mbe["unshield"]
                print("変更後のAC:", mb.ac)
            elif mbe["action"] == "sleep" and mb.health < 1:
                mb.health = 1
            elif mbe["action"] == "silent":
                mb.silent = True
            elif mbe["action"] == "kill":
                mb.lost_hp()
            if "additions" in mbe and mb.health < 3:
                msg = ""
                for addition in mbe["additions"]:
                    if addition == 7 and not mb.poison:
                        msg = "どくを うけた"
                        mb.poison = 1
                    elif addition == 8 and mb.health < 2:
                        msg = "しびれて うごけなくなった"
                        mb.health = max(mb.health, 2)
                    elif addition == 9 and mb.health < 3:
                        msg = "いしに かえられた"
                        mb.health = max(mb.health, 3)
                    elif addition == 11:
                        msg = "くびを はねられた"
                        mb.lost_hp()
                if msg and "blows" in mbe:
                    self.popover(f"{mb.name}は {msg}")
                    self.wait = 6
        for idx in self.monsters_effection:
            ms = self.monsters[idx]
            mse = self.monsters_effection[idx]
            if "cure" in mse:
                ms.hp += mse["cure"]
                print(f"{ms.name}のHP:{ms.hp}(+{mse['cure']})")
        self.end_action()

    # 行動終了
    def end_action(self):
        self.monsters_effection = {}
        self.members_effection = {}
        if len(self.actions):
            self.action = self.actions.pop(0)
        else:
            self.actions = None
            self.action = None

    # ターン開始
    def start_turn(self):
        if self.members_vanguard_idxs:
            v_idx = max(self.members_vanguard_idxs)
            self.members_vanguard_idxs = self.members_idxs(True, True)
            while v_idx < max(self.members_vanguard_idxs):
                v_idx += 1
                if self.members[v_idx].health == 0:
                    self.members[v_idx].fx = ["persuaded", 4]
        self.commands = []
        self.find_active_member(0)
        if len(self.commands) < len(self.members):
            self.show_commands()
        else:
            # 全員行動不能
            self.phase = "action"
        self.show_main()

    # 戦闘画面表示メイン
    def draw(self):
        # 背景
        u = 16 if self.floor == 6 else 0
        for x in range(32):
            px.blt(x * 16, 0, 0, u, 224, 16, 32, 0)
        # モンスター
        for ms_idx, ms in enumerate(self.monsters):
            mx, my = ms.draw()
            if mx is None:
                continue
            if ms.sleeping:
                motion = px.frame_count // 4 % 4
                self.text(mx + 48, my, ".zZ"[:motion], 13, 1)
            mse = (
                self.monsters_effection[ms_idx]
                if ms_idx in self.monsters_effection
                else None
            )
            # エフェクト
            if mse and "fx_type" in mse:
                fx_type = mse["fx_type"]
                if fx_type == "injured":
                    motion = mse["fx_len"] % 4
                    if motion == 3 and mse["is_weak"] and mse["blows"]:
                        self.flash = 10
                    u = None
                    if mse["fx_pat"] == 0:
                        if motion == 3:
                            x, y = mx + 40, my + 8
                            u, v = 64, 64
                        elif motion == 2:
                            x, y = mx + 24, my + 24
                            u, v = 80, 64
                        elif motion == 1:
                            x, y = mx + 8, my + 40
                            u, v = 96, 64
                    elif mse["fx_pat"] == 1:
                        if motion > 0:
                            x, y = mx + px.rndi(8, 40), my + px.rndi(8, 40)
                            u, v = 112, 64
                    if u is not None:
                        px.blt(x, y, 2, u, v, 16, 16, 0)
                elif fx_type == "identify":
                    motion = ((mse["fx_len"] - 1) // 3) % 3
                    if motion == 0:
                        px.blt(mx + 16, my + 16, 2, 212, 64, 16, 16, 0)
                    else:
                        m8 = (2 - motion) * 8
                        px.blt(mx + m8, my + m8, 2, 144, 64, 16, 16, 0)
                        px.blt(mx + 32 - m8, my + m8, 2, 160, 64, 16, 16, 0)
                        px.blt(mx + m8, my + 32 - m8, 2, 176, 64, 16, 16, 0)
                        px.blt(mx + 32 - m8, my + 32 - m8, 2, 192, 64, 16, 16, 0)
                elif fx_type in ("damage", "cure", "miss"):  # ダメージ表示
                    value = 0
                    if mse["fx_type"] == "damage":
                        blows = mse["blows"]
                        value = mse["damage"]
                        if blows:
                            x = mx + 24
                            y = my + 20
                            str_hit = "hits" if blows > 1 else "hit"
                            self.text(x, y, f"{blows}{str_hit}!", 7, 1)
                    elif mse["fx_type"] == "cure":
                        value = mse["cure"]
                    str_value = util.zen(value) if value else "ミス！"
                    x = mx + 32 - len(str_value) * 4
                    dy = LIST_DY[mse["fx_len"] - 1]
                    y = my + 48 - dy
                    c = 11 if mse["fx_type"] == "cure" else 14
                    Window.bdf.draw_text(x, y, str_value, c, 1)
                elif fx_type == "nullify" and mse["fx_len"]:
                    motion = mse["fx_len"] % 3
                    if motion < 3:
                        su, sv = 128 + motion * 16, 224
                        px.blt(mx + 48, my + 16, 2, su, sv, -16, 32, 0)
                else:
                    self.draw_fx(mse, mx, my)
                mse["fx_len"] = max(mse["fx_len"] - 1, 0)
            if self.phase == "command":
                # カーソル表示
                if self.selected_monster == ms_idx or (
                    self.selected_monster == -1 and px.frame_count % 2 == 0
                ):
                    px.blt(mx - 8, my + 16, 0, 0, 96, 16, 16, 3)
                # ターゲット表示
                add_x = [0, 0, 0, 0, 0]
                for mb_idx, command in enumerate(self.commands):
                    if command["target"] in [ms_idx, -1]:
                        if (px.frame_count - mb_idx * 5) % 20 < 5:
                            s = util.zen(mb_idx + 1)
                            x = mx + 16 + add_x[ms_idx]
                            Window.bdf.draw_text(x, my, s, 7, 1)
                        add_x[ms_idx] += 8
        # パーティ
        for idx in range(len(self.members)):
            # キャラクタ
            mx, my, mb, action, motion = self.get_member_image(idx)
            wu, wv = mb.weapon.img_u, mb.weapon.img_v
            if motion == 2:  # 武器（奥）
                if mb.weapon.id == 42:  # しゅりけん
                    px.blt(mx + 12, my - 4, 2, wu, wv, -16, 16, 0)
                else:
                    px.blt(mx + 8, my - 8, 2, wu, wv, -16, 16, 0)
            util.draw_member(mx, my, mb, motion)  # 　自分
            if motion == 1 and action == "attack":  # 武器（手前）
                if mb.weapon.id == 42:  # しゅりけん
                    step = self.get_shuriken_step(mb)
                    if step == 3:
                        Sounds.sound(23)
                    elif step in (7, 9, 11, 13):
                        Sounds.sound(24)
                    fx = mb.fx
                    nx, ny = mx - 14, my + 6
                    base_tx, base_ty = fx[3].draw()
                    for i in range(fx[2]):
                        if fx[2] == 1:
                            tx, ty = base_tx + 24, base_ty + 24
                        else:
                            angle = (i / fx[2]) * 360
                            tx = base_tx + 24 + px.cos(angle) * 10
                            ty = base_ty + 24 + px.sin(angle) * 10
                        if step == 2 + i * 2:
                            px.blt(nx, ny, 2, wu, wv, -16, 16, 0)
                        elif step > 2 + i * 2 and step <= 4 + i * 2:
                            rate_m = (5 + i * 2 - step) / 3
                            x = nx * rate_m + tx * (1 - rate_m)
                            y = ny * rate_m + ty * (1 - rate_m)
                            px.blt(x, y, 2, wu, wv, -16, 16, 0)
                        elif step > 4 + i * 2:
                            px.blt(tx, ty, 2, wu, wv, -16, 16, 0)
                else:
                    px.blt(mx - 16, my, 2, wu, wv, 16, 16, 0)
            if self.selected_member == idx or (
                self.selected_member == -1 and px.frame_count % 2 == 0
            ):  # カーソル
                px.blt(mx - 16, my, 0, 0, 96, 16, 16, 3)
            # エフェクト
            if idx in self.members_effection:
                mbe = self.members_effection[idx]
                if mbe["fx_len"]:
                    if mbe["fx_type"] in ("damage", "miss", "cure"):
                        value = 0
                        is_cure = False
                        if mbe["fx_type"] == "damage":
                            value = mbe["damage"]
                        elif mbe["fx_type"] == "cure":
                            value = mbe["cure"]
                            is_cure = True
                        str_value = util.zen(value) if value else "ミス！"
                        x = mx + 8 - len(str_value) * 4
                        dy = LIST_DY[mbe["fx_len"] - 1]
                        y = my + 16 - dy
                        c = 11 if is_cure else 14
                        if not is_cure or value:
                            Window.bdf.draw_text(x, y, str_value, c, 1)
                        if "flash" in mbe and mbe["fx_len"] % 6 > 3:
                            self.flash = mbe["flash"]
                    else:
                        self.draw_fx(mbe, mx, my, True)
                    mbe["fx_len"] = max(mbe["fx_len"] - 1, 0)
        if self.completed:
            self.win_motion = min(self.win_motion + 1, 35)
        if self.warp_fx:
            screen_ptr = px.screen.data_ptr()
            k = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 64][
                min(12 - self.warp_fx, 10)
            ] * 1024
            size = len(screen_ptr)
            for i in range(size):
                screen_ptr[i] = 0 if i + k >= size else screen_ptr[i + k]

    def draw_fx(self, parm, mx, my, is_member=False):
        fx_type = parm["fx_type"]
        fx_len = parm["fx_len"]
        if not fx_len:
            return
        if fx_type == "fire1":
            u, v = (fx_len % 2) * 16, 128
            x, y = (mx, my - 24) if is_member else (mx + 24, my + 16)
            px.blt(x, y, 2, u, v, 16, 48, 0)
        elif fx_type == "fire2":
            u, v = 32 + (fx_len % 2) * 32, 128
            x, y = (mx - 8, my - 24) if is_member else (mx + 16, my + 16)
            px.blt(x, y, 2, u, v, 32, 48, 0)
        elif fx_type == "fire3":
            pat = min(9 - fx_len // 2, 2)
            if pat < 2:
                u, v, w, h = pat * 16, 208, 16, 16
            else:
                w = 32 if fx_len % 2 == 0 else -32
                u, v, h = 0, 224, 32
            x, y = (mx + 8, my + 8) if is_member else (mx + 32, my + 32)
            px.blt(x - abs(w) // 2, y - h // 2, 2, u, v, w, h, 0)
        elif fx_type == "bolt":
            if fx_len >= 16:
                u, v, w = 96, 128, 32
            else:
                u, v = 128, 128
                w = 48 if fx_len % 2 == 0 else -48
            x, y = (mx + 8, my - 24) if is_member else (mx + 32, my + 16)
            px.blt(x - abs(w) // 2, y, 2, u, v, w, 48, 0)
        elif fx_type == "ice1":
            pat = (2, 2, 2, 2, 1, 1, 1, 0, 0, 0)[fx_len]
            if pat == 0:
                u, v, size = 176, 128, 16
            elif pat == 1:
                u, v, size = 176, 144, 32
            elif pat == 2:
                u, v, size = 208, 128, 48
            x, y = (mx + 8, my + 8) if is_member else (mx + 32, my + 32)
            px.blt(x - size // 2, y - size // 2, 2, u, v, size, size, 0)
        elif fx_type == "ice2":
            pat = (2, 2, 2, 2, 1, 1, 1, 0, 0, 0)[fx_len]
            h = (pat + 1) * 16
            x, y = (mx - 16, my + 24) if is_member else (mx + 8, my + 56)
            px.blt(x, y - h, 2, 32, 208, 48, h, 0)
        elif fx_type == "angel":
            if fx_len < 8:
                pat = 3
                y = my + min(fx_len, 6) * 4
                w = 16
            else:
                pat = (2, 2, 2, 2, 2, 1, 0, 2, 2, 1, 0)[fx_len - 8]
                y = my + 24
                w = -16
            u, v = 192 + pat * 16, 208
            px.blt(mx + 48, y, 2, u, v, w, 16, 0)
        elif fx_type in ("bomb1", "bomb2"):
            pat = (24 - fx_len // 2) % 4
            x, y = (mx - 16, my - 12) if is_member else (mx + 8, my + 8)
            base_u = {"bomb1": 96, "bomb2": 160}[fx_type]
            u1 = base_u + (0, 16, 32, 48)[pat]
            u2 = base_u + (0, 16, 32, 48)[(pat + 1) % 4]
            u3 = base_u + (0, 16, 32, 48)[(pat + 2) % 4]
            v = 192
            px.blt(x, y, 2, u1, v, 16, 16, 0)
            px.blt(x + 32, y + 16, 2, u1, v, 16, 16, 0)
            px.blt(x + 24, y, 2, u2, v, 16, 16, 0)
            px.blt(x, y + 32, 2, u2, v, 16, 16, 0)
            px.blt(x + 8, y + 16, 2, u3, v, 16, 16, 0)
            px.blt(x + 24, y + 32, 2, u3, v, 16, 16, 0)
            if pat == 2 and fx_type == "bomb1":
                self.flash = 9
        elif fx_type in ("venom1", "venom2"):
            pat = (16 - fx_len // 2) % 4
            x, y = (mx - 16, my - 12) if is_member else (mx + 8, my + 8)
            if fx_type == "venom1":
                u = (144, 160, 16, 32)[pat]
            else:
                u = (176, 192, 112, 128)[pat]
            v = 176
            px.blt(x, y, 2, u, v, 16, 16, 0)
            px.blt(x + 32, y, 2, u, v, 16, 16, 0)
            px.blt(x + 16, y + 8, 2, u, v, 16, 16, 0)
            px.blt(x + 8, y + 24, 2, u, v, 16, 16, 0)
            px.blt(x + 24, y + 32, 2, u, v, 16, 16, 0)
        elif fx_type in ("curse1", "curse2", "curse3"):
            if fx_len % 2:
                pat = (fx_len // 2) % 3
                x, y = (mx - 16, my - 12) if is_member else (mx + 8, my + 8)
                base_u = {"curse1": 0, "curse2": 32, "curse3": 64}[fx_type]
                u1, u2, v = base_u, base_u + 16, 192
                if pat == 0:
                    px.blt(x, y + 8, 2, u1, v, 16, 16, 0)
                    px.blt(x + 32, y + 24, 2, u1, v, 16, 16, 0)
                    px.blt(x + 16, y, 2, u2, v, 16, 16, 0)
                    px.blt(x + 16, y + 32, 2, u2, v, 16, 16, 0)
                elif pat == 1:
                    px.blt(x, y + 24, 2, u1, v, 16, 16, 0)
                    px.blt(x + 32, y + 8, 2, u1, v, 16, 16, 0)
                    px.blt(x, y + 8, 2, u2, v, 16, 16, 0)
                    px.blt(x + 32, y + 24, 2, u2, v, 16, 16, 0)
                if pat == 2:
                    px.blt(x + 16, y, 2, u1, v, 16, 16, 0)
                    px.blt(x + 16, y + 32, 2, u1, v, 16, 16, 0)
                    px.blt(x, y + 24, 2, u2, v, 16, 16, 0)
                    px.blt(x + 32, y + 8, 2, u2, v, 16, 16, 0)
        elif fx_type == "blade":
            w = 0
            if fx_len == 9:
                x, y, u, w = mx + 40, my + 8, 64, 16
                self.flash = 13
            elif fx_len == 8:
                x, y, u, w = mx + 24, my + 24, 80, 16
            elif fx_len == 7:
                x, y, u, w = mx + 8, my + 40, 96, 16
            if fx_len == 5:
                x, y, u, w = mx + 8, my + 8, 64, -16
                Sounds.sound(11)
            elif fx_len == 4:
                x, y, u, w = mx + 24, my + 24, 80, -16
            elif fx_len == 3:
                x, y, u, w = mx + 40, my + 40, 96, -16
            if w != 0:
                px.blt(x, y, 2, u, 64, w, 16, 0)
        elif fx_type in ("cloud1", "cloud2", "cloud3"):
            pat = 2 - ((fx_len - 1) // 3) % 3
            x, y = (mx - 16, my - 12) if is_member else (mx + 8, my + 8)
            base_u = {"cloud1": 0, "cloud2": 48, "cloud3": 96}[fx_type]
            u1 = base_u + (0, 16, 32)[pat]
            u2 = base_u + (0, 16, 32)[(pat + 1) % 3]
            u3 = base_u + (0, 16, 32)[(pat + 2) % 3]
            v = 176
            px.blt(x, y, 2, u1, v, 16, 16, 0)
            px.blt(x + 24, y + 32, 2, u1, v, 16, 16, 0)
            px.blt(x + 24, y, 2, u2, v, 16, 16, 0)
            px.blt(x + 8, y + 16, 2, u2, v, 16, 16, 0)
            px.blt(x + 32, y + 16, 2, u3, v, 16, 16, 0)
            px.blt(x, y + 32, 2, u3, v, 16, 16, 0)
        elif fx_type == ("blind"):
            pat = 4 - ((fx_len - 1) // 2)
            x, y = (mx - 16, my - 24) if is_member else (mx + 8, my + 16)
            if pat in (0, 2):
                px.blt(x, y, 2, 128, 64, 16, 8, 0)
                px.blt(x + 32, y, 2, 128, 64, 16, 8, 0)
            if pat in (1, 3):
                px.blt(x, y + 16, 2, 128, 64, 16, 8, 0)
                px.blt(x + 32, y + 16, 2, 128, 64, 16, 8, 0)
            if pat in (2, 3):
                px.blt(x, y + 32, 2, 128, 64, 16, 8, 0)
                px.blt(x + 32, y + 32, 2, 128, 64, 16, 8, 0)
            if pat == 4:
                px.blt(x, y + 32, 2, 128, 72, 48, 8, 0)
        elif fx_type == "heal1":
            w = 16 if (fx_len // 3) % 2 == 0 else -16
            px.blt(mx, my + 4, 2, 112, 112, w, 16, 0)
        elif fx_type == "heal2":
            pat = (fx_len // 3) % 2
            if pat == 0:
                px.blt(mx - 8, my - 4, 2, 128, 112, 16, 16, 0)
                px.blt(mx + 8, my + 12, 2, 128, 112, 16, 16, 0)
            elif pat == 1:
                px.blt(mx + 8, my - 4, 2, 128, 112, -16, 16, 0)
                px.blt(mx - 8, my + 12, 2, 128, 112, -16, 16, 0)
        elif fx_type == "heal3":
            pat = (fx_len // 3) % 2
            if pat == 0:
                u1, v1, w1 = 144, 112, 16
                u2, v2, w2 = 144, 112, -16
                u3, v3, w3 = 160, 112, 16
            elif pat == 1:
                u1, v1, w1 = 144, 112, -16
                u2, v2, w2 = 144, 112, 16
                u3, v3, w3 = 176, 112, 16
            px.blt(mx - 16, my - 12, 2, u1, v1, w1, 16, 0)
            px.blt(mx + 16, my + 20, 2, u1, v1, w1, 16, 0)
            px.blt(mx + 16, my - 12, 2, u2, v2, w2, 16, 0)
            px.blt(mx - 16, my + 20, 2, u2, v2, w2, 16, 0)
            px.blt(mx, my + 4, 2, u3, v3, w3, 16, 0)
        elif fx_type == "pure":
            pat = 3 - ((fx_len - 1) // 2) % 4
            print(pat)
            px.blt(mx, my + 4, 2, 128 + pat * 16, 208, 16, 16, 0)
        elif fx_type == "shield":
            motion = fx_len % 3
            if motion < 3:
                u, v = 128 + motion * 16, 224
                px.blt(mx - 16, my - 4, 2, u, v, 16, 32, 0)
        elif fx_type == "warp":
            self.warp_fx = fx_len

    def next_command(self, mb_idx):
        self.move_backward(mb_idx)
        self.find_active_member(mb_idx + 1)
        Window.close(
            [
                "battle_spells",
                "battle_spells_guide",
                "battle_items",
                "battle_items_guide",
            ]
        )
        if len(self.commands) >= len(self.members):
            Window.close("battle_command")
            self.phase = "action"
        else:
            self.show_commands()

    def find_active_member(self, first_idx, dist=1):
        idx = first_idx
        while idx < len(self.members) and idx >= 0 and self.members[idx].health:
            idx += dist
        if dist > 0:
            while idx > len(self.commands):
                self.commands.append({"action": None, "target": None})
        else:
            command = None
            while idx >= 0 and idx < len(self.commands):
                command = self.commands.pop(-1)
            return command

    # 逃走
    def run(self):
        rate = 0 if self.seed == 60 else 100
        mslvs = [ms.lv for ms in self.monsters if ms.is_live and not ms.sleeping]
        if not self.preemptive and mslvs:
            for mb in self.members:
                if mb.health < 4 and mb.job_id != 2:  # シーフは減算しない
                    rate -= util.maxmin(6 + max(mslvs) - mb.lv, 12)
        print("逃走成功率：", rate)
        if rate > px.rndi(0, 99):
            self.message("にげだした‥", "run")
        else:
            self.message("にげられない！")
            self.move_backward(0)
            self.commands = []
            self.phase = "action"

    # 敵を倒した
    def kill_monster(self, monster, dispell=False):
        if not dispell:
            self.total_exp += monster.exp
            self.total_gold += monster.gold
        monster.hp = 0
        monster.fade = 1
        self.wait = 12

    # 自キャラの位置とモーション
    def get_member_image(self, idx):
        member = self.members[idx]
        v_idxs = self.members_vanguard_idxs
        x = 208 if not v_idxs or idx <= max(v_idxs) else 224
        y = 40 + idx * 28
        motion = 0
        action = ""
        if member.health == 4:
            x += 8
        fx = member.fx
        if fx and not self.completed:
            action = fx[0]
            dist = self.get_dist(idx)
            if action == "forward":
                x = x - fx[1] * 4
                motion = fx[1] % 2
                if fx[1] < dist:
                    fx[1] += 1
            elif action == "persuaded":
                fx[1] -= 1
                x = x + fx[1] * 4
                motion = fx[1] % 2
                if fx[1] <= 0:
                    member.fx = None
            elif action == "backward":
                fx[1] -= 1
                x = x - fx[1] * 4
                motion = fx[1] % 2
                if fx[1] <= 0:
                    member.fx = None
            elif action == "attack":
                x = x - dist * 4
                if fx[1] <= 0:
                    motion = 0
                elif member.weapon.id == 42:
                    step = self.get_shuriken_step(member)
                    motion = 1 if step > 1 else 2
                else:
                    motion = 1 + (fx[1] % 4) // 2
                    if fx[1] % 4 == 1 and fx[2]:
                        Sounds.sound(11)
                fx[1] = max(fx[1] - 1, 0)
            elif action == "damage":
                fx[1] = max(fx[1] - 1, 0)
                x = x + 8 + fx[1] % 2
                motion = 4
            elif action == "guard":
                motion = 6
            elif action == "spell_start":
                x = x - dist * 4
                if fx[1] > 0 and fx[1] <= 16 and fx[2]:
                    r = 16 if fx[1] > 3 else fx[1] * 4
                    base_angle = (fx[1] % 3) * 15
                    for i in range(8):
                        angle = (base_angle + i * 45) % 360
                        h = 8 if (fx[1] + i) % 2 == 0 else -8
                        sx = x + 4 + r * px.cos(angle)
                        sy = y + 8 + r * px.sin(angle)
                        px.blt(sx, sy, 2, 160, 64, 8, h, 0)
                fx[1] = max(fx[1] - 1, 0)
                motion = 6
            elif action:
                x = x - dist * 4
                fx[1] = max(fx[1] - 1, 0)
                motion = 1 if action == "spell_done" else 6
                if action == "dispell" and fx[1] % 4 == 1:
                    self.flash = 7
        elif member.poison or member.hp <= member.mhp // 4:
            motion = 5
        if member.health in (1, 2):
            motion = 5
        elif member.health == 3:
            motion = 0
        elif (
            motion == 0
            and self.completed
            and member.health == 0
            and (self.win_motion + 15) % 20 < 10
        ):
            motion = 6
        return x, y, member, action, motion

    # しゅりけんのアニメーション用
    def get_shuriken_step(self, member):
        fx = member.fx
        return 5 + fx[2] * 2 - fx[1]

    # メンバー準備
    def set_selector_members(self):
        self.selector_items = [
            idx for idx, mb in enumerate(self.members) if mb.health < 4
        ]
        self.selected_member = self.selector_items[0]

    # モンスター選択準備
    def set_selector_monsters(self, only_vanguard=False):
        self.selector_items = self.monsters_idxs(only_vanguard)
        if self.selector_items:
            self.selected_monster = self.selector_items[-1]

    # カーソル初期化
    def init_selector(self, spell, mb_idx):
        if spell.target == 0:
            self.selector_items = [mb_idx]
            self.selected_member = mb_idx
        elif spell.target in (1, 2):
            self.set_selector_members()
            if spell.target == 2:
                self.selected_member = -1
        elif spell.target in (3, 4):
            self.set_selector_monsters()
            if spell.target == 4:
                self.selected_monster = -1

    # 行動可能なメンバーを配列で返す
    def members_idxs(self, only_vanguard=False, with_unhealth=False):
        mb_idxs = []
        first_idx = None
        for idx, mb in enumerate(self.members):
            if mb.health < 2 or with_unhealth:
                mb_idxs.append(idx)
            if mb.health < 4 and first_idx is None:
                first_idx = idx
        if only_vanguard and mb_idxs:
            if first_idx is None:
                first_idx = 5  # 全員動けない
            return [idx for idx in mb_idxs if idx < first_idx + 3]
        else:
            return mb_idxs

    # 行動可能なモンスターを配列で返す
    def monsters_idxs(self, only_vanguard=False):
        ms_idxs = [ms.idx for ms in self.monsters if ms.is_live]
        if only_vanguard and ms_idxs:
            max_idx = max(ms_idxs)
            return [idx for idx in ms_idxs if idx > max_idx - 3]
        else:
            return ms_idxs

    # 有効的なモンスターでの性格変更
    def change_natures(self, dist):
        for mb in self.members:
            if mb.nature == 4 - dist and 1 > px.rndi(0, 9):
                mb.nature = dist

    ### ウィンドウ表示

    def message(self, texts, parm=None):
        if Window.get("battle_popover"):
            self.saved_msg = [texts, parm]
        else:
            win = Window.open("battle_msg", 2, 1, 29, 1, texts)
            win.parm = parm

    def popover(self, texts, parm=18):
        win = Window.open("battle_popover", 2, 1, 29, 1, texts)
        win.parm = parm
        return win

    def show_main(self):
        Window.open(
            "monsters", 1, 15, 14, 19, [ms.name for ms in self.monsters if ms.show]
        )
        texts = [
            f"{util.spacing(mb.name,6)} {util.pad(mb.hp,3)}/{mb.status()}"
            for mb in self.members
        ]
        Window.open("battle_status", 17, 15, 30, 19, texts)

    def show_commands(self, command=None):
        self.phase = "command"
        idx = len(self.commands)
        self.move_forward(idx)
        mb = self.members[idx]
        values = []
        if idx in self.members_idxs(True):
            if self.members[idx].atc:
                values.append(0)
        # にげるは最初のメンバのみ
        for cm in self.commands:
            if not cm["action"] is None:
                break
        else:
            values.append(1)
        values.append(2)
        if len(mb.spells) and not self.preemptive and not mb.silent:
            values.append(3)
        if mb.job_id in [3, 5]:
            values.append(4)
        if mb.job_id == 5:
            values.append(5)
        values.append(6)
        # コマンドが５を超える場合、みをまもる > ディスペルを外す
        if len(values) > 5:
            values = [value for value in values if value != 2]
        if len(values) > 5:
            values = [value for value in values if value != 5]
        texts = [
            [" たたかう", " にげる", " みをまもる", " じゅもん", " ディスペル", " しきべつ", " アイテム"][value]
            for value in values
        ]
        cur_y = values.index(command) if not command is None else 0
        win = Window.get("battle_command")
        if not win:
            win = Window.open("battle_command", 9, 15, 14, 19, texts)
        win.texts = texts
        win.cur_y = cur_y
        win.values = values
        win.add_cursol()

    # 呪文選択
    def show_spells(self, member_idx=None):
        win = Window.get("battle_spells")
        idx = member_idx if win is None else win.parm
        if idx is None:
            return None
        member = self.members[idx]
        texts = []
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
            texts += [tm, tp]
        if win is None and cur_y is not None:
            win = Window.open("battle_spells", 1, 15, 30, 19, texts)
            win.add_cursol(None, [3, 12, 21])
            win.cur_y = cur_y
            win.parm = member_idx
        elif win:
            win.texts = texts
        win_guide = Window.get("battle_spells_guide")
        if not win_guide:
            win_guide = Window.open("battle_spells_guide", 1, 12, 14, 13)
        return win_guide

    # アイテム選択
    def show_items(self, member_idx=None):
        win = Window.get("battle_items")
        idx = member_idx if win is None else win.parm
        if idx is None:
            return None
        member = self.members[idx]
        texts = ["", ""]
        values = [None, None]
        for equip in member.equips:
            item = Item(equip)
            if item.type == 1:
                texts[0] = f"#{item.name}"
                values[0] = equip
            elif item.type == 6:
                texts[1] = f"#{item.name}"
                values[1] = equip
        # 選択済みのアイテムは表示しない
        items = copy.deepcopy(self.items)
        for command in self.commands:
            if "item" in command:
                item = command["item"]
                if item.brake:
                    items.pop(items.index(item.id))
        for id in items:
            item = Item(id)
            if item.type == 0:
                texts.append(f" {item.name}")
                values.append(id)
        if len(texts) % 2 == 1:
            texts.append("")
            values.append(None)
        lines = [
            f" {util.spacing(texts[i*2],12)} {util.spacing(texts[i*2+1],12)}"
            for i in range(len(texts) // 2)
        ]
        if win is None:
            win = Window.open("battle_items", 1, 15, 30, 19, lines)
            win.add_cursol(None, [0, 13])
            win.parm = member_idx
            if values[0] is None:
                if not values[1] is None:
                    win.cur_x = 1
                elif len(lines) > 1:
                    win.cur_y = 1
        elif win:
            win.texts = lines
        win.values = values
        win_guide = Window.get("battle_items_guide")
        if not win_guide:
            win_guide = Window.open("battle_items_guide", 1, 12, 14, 13)
        return win_guide

    ### アニメーション

    def move_forward(self, member_idx):
        self.members[member_idx].fx = ["forward", 0]

    def move_backward(self, member_idx):
        fx = self.members[member_idx].fx
        if fx:
            pos = fx[1] if fx[0] == "forward" else self.get_dist(member_idx)
            self.members[member_idx].fx = ["backward", pos]

    def get_dist(self, member_idx):
        return 4 if member_idx in self.members_idxs(True) else 8

    def text(self, x, y, s, c1, c2):
        for ay in range(3):
            for ax in range(3):
                px.text(x + ax - 1, y + ay - 1, s, c2)
        px.text(x, y, s, c1)
