"""转换层：RPG Maker MZ 回想事件 → 桌宠 Scene JSON（批量）。

只读原游戏，不改动任何原有架构。五类命令转换：
    L2ModelLoadMdl(...)            -> load_model
    L2dSetMotion(...)              -> play_motion
    L2dSetExp(...)                 -> set_expression   (经 Live2dSettingData.expSetting 映射)
    nAppCmd("Voice", [...])        -> play_voice
    code 230 (Wait N 帧)           -> wait (timeline delay)

输入：
    www/data/CommonEvents.json         场景脚本
    www/data/Live2dSettingData.json    模型/表情设置
    www/data/Nupu_PSData.json          回想条目
    www/audio/voice/<角色>/*.rpgmvo     语音
输出：
    world_data/scenes/<CE>.json        每个场景
    world_data/scenes/_report.csv      逐场景报告
    world_data/scenes/_summary.csv     统计汇总

用法：
    python scene_adapter.py CE756        单条
    python scene_adapter.py --all        全部（回想入口 + H 事件）
    python scene_adapter.py --list       列出可转换事件
"""
import ast
import csv
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

GAME = ("D:\\BaiduNetdiskDownload\\Romasha-Live2D-AI-main\\公主协同效应  v1.0.28\\"
        "PS-\\PS-1.0.28_PC\\PS-1.0.28_PC.7z\\princess_synergy-1.0.28")
APP = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(GAME, "www", "data")
WEB = os.path.join(APP, "web")
OUT_DIR = os.path.join(APP, "world_data", "scenes")
SCHEMA = "romasha.scene/1"
DISPATCH = (52, 178, 179)          # 回想分发公共事件

# ---- RPG Maker 命令模式 ----
RE_LOAD = re.compile(r'L2ModelLoadMdl\(\s*"([^"]+)"')
RE_MOTION = re.compile(r'L2d(?:SetMotion|IdleStart|FadeMdl)\(\s*"([^"]+)"\s*'
                       r'(?:,\s*"[^"]*"\s*,\s*\d+\s*,)?\s*,?\s*"([^"]+)"\s*\)')
RE_EXP = re.compile(r'L2dSetExp\(\s*"([^"]+)"\s*,\s*(\d+)\s*\)')
RE_VOICE = re.compile(r'new nAppCmd\(\s*"Voice"\s*,\s*\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\]\s*\)')

# PVoice("角色","文件") / PRandVoice("角色",["文件",...]) —— 直接给出语音文件名
RE_PVOICE = re.compile(r'P(?:Rand)?Voice\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)')
RE_PVOICE_R = re.compile(r'PRandVoice\(\s*"([^"]+)"\s*,\s*\[\s*"([^"]+)"')
RE_PARAM = re.compile(r'L2D_ParamSet\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*([0-9.+-]+)\s*\)')
RE_MEM_NO = re.compile(r'MemoryOn\(\s*(\d+)')
RE_RECALL_BRANCH = re.compile(r'回想番号\s*==\s*(\d+)')


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as f:
        return json.load(f)


_CE = _load("CommonEvents.json")
_BY_ID = {e["id"]: e for e in _CE if e}
_LSD = _load("Live2dSettingData.json")
_MEM = _load("Nupu_PSData.json")["MemoryData"]
_TITLE = {m.get("_No"): (m.get("_Title") or "").strip() for m in _MEM}
_PTN = {m.get("_No"): len([p for p in (m.get("_Ptn") or []) if p]) for m in _MEM}
_EXP = {}
for _it in _LSD.get("expSetting") or []:
    if isinstance(_it, dict):
        _EXP[(_it.get("MdlFile"), _it.get("FaceNo"))] = _it.get("MtnFile")

try:
    _src = open(os.path.join(APP, "main.py"), encoding="utf-8").read()
    _L2D = None
    for _n in ast.parse(_src).body:
        if isinstance(_n, ast.Assign) and any(getattr(t, "id", None) == "L2D_SCENE_LABELS" for t in _n.targets):
            _L2D = ast.literal_eval(_n.value)
    H_MODELS = {k for k, v in _L2D.items() if str(v).startswith("♥")}
except Exception:
    H_MODELS = set()


def _partner(name):
    for t in ("syota", "Mn", "man"):
        if t in name:
            return t
    return None


_MODEL_CACHE = {}


def clean_text(s):
    """清掉 RPG Maker 控制码：换行标记 / 角色名占位 / 图标 / 转义。"""
    if not s:
        return ""
    parts = re.split(r"\\I\[\d+\]", s)
    out = []
    for p in parts:
        p = re.sub(r"\\n<\s*\\N\[\d+\]\s*>", "", p)
        p = re.sub(r"\\N\[\d+\]", "", p)
        p = p.replace("\\n<", "")
        p = re.sub(r"\\[A-Za-z]+\[[^\]]*\]", "", p)
        p = p.replace("\\", "").replace("<", "").strip()
        if p and (not out or out[-1] != p):
            out.append(p)
    return "".join(out).strip()


def model_motions(model):
    """模型实际拥有的动作名集合（用于剔除原事件里的笔误/无效动作）。"""
    if model in _MODEL_CACHE:
        return _MODEL_CACHE[model]
    names = set()
    try:
        p = os.path.join(WEB, "model_alt", model, "%s.model3.json" % model)
        with open(p, encoding="utf-8-sig") as f:
            d = json.load(f)
        for grp in ((d.get("FileReferences") or {}).get("Motions") or {}).values():
            for it in grp or []:
                n = os.path.basename(it.get("File", "")).replace(".motion3.json", "")
                if n:
                    names.add(n)
    except Exception:
        pass
    _MODEL_CACHE[model] = names
    return names


def voice_key():
    try:
        with open(os.path.join(DATA, "System.json"), encoding="utf-8-sig") as f:
            return bytes.fromhex(json.load(f).get("encryptionKey") or "")
    except Exception:
        return b""


def decrypt_voices(scenes):
    """把场景引用的语音从 .rpgmvo 解密到 web/ 下（幂等）。返回 (新增, 缺源)。"""
    key = voice_key()
    made, missing = 0, []
    for s in scenes:
        for v in s.get("voices") or []:
            dst = os.path.join(WEB, v["path"])
            if os.path.isfile(dst):
                continue
            src = os.path.join(GAME, "www", "audio", "voice", v["character"], v["file"] + ".rpgmvo")
            if not os.path.isfile(src) or not key:
                missing.append("%s/%s" % (v["character"], v["file"]))
                continue
            raw = open(src, "rb").read()
            data = raw[16:] if raw[:5] == b"RPGMV" else raw
            n = len(data)
            rep = (key * (n // len(key) + 1))[:n]
            out = (int.from_bytes(data, "big") ^ int.from_bytes(rep, "big")).to_bytes(n, "big")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(out)
            if out[:4] == b"OggS":
                made += 1
            else:
                os.remove(dst)
                missing.append("%s/%s" % (v["character"], v["file"]))
    return made, missing


# ============================ 解析 ============================
def walk(event_id, seen=None):
    """按执行顺序展开事件（跟随 code117 调用）；每个事件只展开一次，避免分支爆炸。"""
    if seen is None:
        seen = set()
    if event_id in seen:
        return []
    seen.add(event_id)
    ev = _BY_ID.get(event_id)
    if not ev:
        return []
    out = []
    for c in ev.get("list") or []:
        code = c.get("code")
        p = c.get("parameters")
        if code == 117 and p:
            out += walk(p[0], seen)
        elif code == 230 and p:
            try:
                out.append({"k": "wait", "frames": int(p[0])})
            except Exception:
                pass
        elif code == 101 and p:
            out.append({"k": "text", "face": (p[0] if p else ""),
                        "speaker": (p[4] if len(p) > 4 else "") or "", "body": ""})
        elif code == 401 and p:
            for o in reversed(out):
                if o.get("k") == "text":
                    o["body"] = o["body"] + (p[0] if p else "")
                    break
        elif code in (355, 655, 122):
            txt = str(p)
            for m in RE_LOAD.finditer(txt):
                out.append({"k": "load_model", "model": m.group(1)})
            for m in RE_MOTION.finditer(txt):
                out.append({"k": "play_motion", "model": m.group(1), "motion": m.group(2)})
            for m in RE_EXP.finditer(txt):
                out.append({"k": "set_expression", "model": m.group(1), "face": int(m.group(2))})
            for v in RE_VOICE.finditer(txt):
                out.append({"k": "play_voice", "character": v.group(1), "file": v.group(2)})
            # PVoice / PRandVoice（直接给文件名的那两种）
            for pv in RE_PVOICE.finditer(txt):
                out.append({"k": "play_voice", "character": pv.group(1), "file": pv.group(2)})
            for pv in RE_PVOICE_R.finditer(txt):
                out.append({"k": "play_voice", "character": pv.group(1), "file": pv.group(2)})
            for pm in RE_PARAM.finditer(txt):
                out.append({"k": "set_param", "model": pm.group(1),
                            "name": pm.group(2), "value": float(pm.group(3))})
        elif code in (250, 241):
            p0 = (p[0] if p else {}) or {}
            nm = p0.get("name", "") if isinstance(p0, dict) else ""
            if nm:
                out.append({"k": "play_se" if code == 250 else "play_bgm", "name": nm})
    return out


def _dedup(ops):
    """去掉相邻重复项；wait 不参与去重（时间不能被吃掉）。"""
    out = []
    for o in ops:
        if o.get("k") == "wait" or o.get("op") == "wait":
            out.append(o)
            continue
        if out and out[-1] == o:
            continue
        out.append(o)
    return out


def _merge_waits(ops):
    out = []
    for o in ops:
        if o.get("k") == "wait" and out and out[-1].get("k") == "wait":
            out[-1] = {"k": "wait", "frames": out[-1]["frames"] + o["frames"]}
            continue
        out.append(o)
    return out


def choose_variant(ops):
    tok = Counter(_partner(o["motion"]) for o in ops if o["k"] == "play_motion")
    tok.pop(None, None)
    if not tok:
        return None
    return max(sorted(tok), key=lambda t: (tok[t], t == "man"))


def build_scene(event_id):
    ev = _BY_ID.get(event_id)
    if not ev:
        raise ValueError("找不到事件 CE%s" % event_id)
    ops = _merge_waits(_dedup(walk(event_id)))
    body = [o for o in ops if o["k"] != "wait"]
    if not body:
        raise ValueError("CE%s 无 Live2D/语音命令" % event_id)

    variant = choose_variant(body)
    flat = " ".join(str(c.get("parameters")) for c in ev.get("list") or [])
    mo = RE_MEM_NO.search(flat)
    memory_no = int(mo.group(1)) if mo else None

    models = Counter(o["model"] for o in body if o["k"] == "play_motion")
    h = [m for m in models if m in H_MODELS] or list(models)
    model = max(h, key=lambda m: models[m]) if h else "romasha_talk"

    motions, expressions, voices, texts, timeline = [], [], [], [], []
    for o in ops:
        k = o["k"]
        if k == "load_model":
            if o["model"] == model:
                timeline.append({"op": "load_model", "character": "romasha", "model": o["model"]})
        elif k == "play_motion":
            if o["model"] != model:
                continue
            if variant is not None and _partner(o["motion"]) not in (None, variant):
                continue
            mm = model_motions(model)
            if mm and o["motion"] not in mm:
                continue
            if o["motion"] not in motions:
                motions.append(o["motion"])
            timeline.append({"op": "play_motion", "character": "romasha", "name": o["motion"]})
        elif k == "set_expression":
            mtn = _EXP.get((o["model"], o["face"]))
            if not mtn:
                continue
            e = {"face_no": o["face"], "model": o["model"], "motion": mtn}
            if e not in expressions:
                expressions.append(e)
            timeline.append({"op": "set_expression", "character": "romasha",
                             "face_no": o["face"], "motion": mtn})
        elif k == "play_voice":
            v = {"character": o["character"], "file": o["file"],
                 "path": "original/voice/h/%s/%s.ogg" % (o["character"], o["file"])}
            if v not in voices:
                voices.append(v)
            timeline.append({"op": "play_voice", "character": o["character"],
                             "file": o["file"], "path": v["path"]})
        elif k == "wait":
            sec = round(o["frames"] / 60.0, 3)
            if sec >= 0.1:
                timeline.append({"op": "wait", "seconds": sec})
        elif k == "play_se":
            _se = o["name"]
            if not _se.lower().endswith((".ogg", ".wav", ".mp3")):
                _se = _se + ".ogg"
            timeline.append({"op": "play_se", "path": "original/se/" + _se})
        elif k == "set_param":
            timeline.append({"op": "set_param", "name": o["name"], "value": o["value"]})
        elif k == "text":
            body = clean_text(o.get("body"))
            if body:
                sp = (o.get("speaker") or "").strip()
                texts.append({"speaker": sp, "text": body})
                timeline.append({"op": "say", "speaker": sp, "text": body})

    timeline = _dedup(timeline)
    title = _TITLE.get(memory_no) or (ev.get("name") or "").strip()
    return {
        "schema": SCHEMA,
        "scene_id": "CE%s" % event_id,
        "source": {"game": "princess_synergy", "event_id": event_id,
                   "event_name": (ev.get("name") or "").strip(),
                   "memory_no": memory_no, "memory_title": title.strip()},
        "trigger": {"memory_no": memory_no, "pattern_count": _PTN.get(memory_no) or 0},
        "variant": variant,
        "characters": [{"id": "romasha", "model": model,
                        "model_source": "img/live2d/%s/%s.model3.json" % (model, model),
                        "model_path": "model_alt/%s/%s.model3.json" % (model, model),
                        "voice_character": "romasha"}],
        "motions": motions,
        "expressions": expressions,
        "voices": voices,
        "texts": texts,
        "timeline": timeline,
    }


# ============================ 资源校验 ============================
def missing_resources(scene):
    ch = (scene.get("characters") or [{}])[0]
    model = ch.get("model") or ""
    miss = []
    if not (ch.get("model_path") and os.path.isfile(os.path.join(WEB, ch["model_path"]))):
        miss.append("model:%s" % ch.get("model_path"))
    for m in scene.get("motions") or []:
        p = os.path.join(WEB, "model_alt", model, "motions", "%s.motion3.json" % m)
        if not os.path.isfile(p):
            miss.append("motion:%s" % m)
    for v in scene.get("voices") or []:
        if not os.path.isfile(os.path.join(WEB, v.get("path") or "")):
            miss.append("voice:%s" % v.get("file"))
    return miss


# ============================ 入口扫描 ============================
def recall_event_map():
    """回想号 -> [事件id]，来自分发事件的分支。"""
    out = {}
    for disp in DISPATCH:
        ev = _BY_ID.get(disp)
        if not ev:
            continue
        cmds = ev.get("list") or []
        for i, c in enumerate(cmds):
            p = c.get("parameters") or []
            if c.get("code") == 111 and len(p) > 1 and isinstance(p[1], str):
                m = RE_RECALL_BRANCH.search(p[1])
                if not m:
                    continue
                no = int(m.group(1)) + 1
                ind = c.get("indent", 0)
                for c2 in cmds[i + 1:]:
                    if c2.get("code") in (411, 412) and c2.get("indent", 0) == ind:
                        break
                    if c2.get("code") == 117 and c2.get("parameters"):
                        out.setdefault(no, []).append(c2["parameters"][0])
    return out


def h_event_ids():
    ids = []
    for e in _CE:
        if not e:
            continue
        txt = " ".join(str(c.get("parameters")) for c in e.get("list") or [])
        if RE_VOICE.search(txt) and any(('"%s"' % h) in txt for h in H_MODELS):
            ids.append(e["id"])
    return ids


def all_scene_event_ids():
    ids = set(h_event_ids())
    for v in recall_event_map().values():
        ids |= set(v)
    return sorted(ids)


# ============================ 导出 ============================
def export(event_id, out_dir=OUT_DIR):
    scene = build_scene(event_id)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "%s.json" % scene["scene_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=1)
    return path, scene


def export_all(out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    ids = all_scene_event_ids()
    rows, ok, fail, miss_total = [], 0, 0, 0
    built = []
    for eid in ids:
        try:
            built.append(build_scene(eid))
            ok += 1
        except Exception as e:
            fail += 1
            rows.append([("CE%d" % eid), "", "", "", 0, 0, 0, 0, "FAIL", str(e)[:60]])

    made, vmiss = decrypt_voices(built)

    for scene in built:
        with open(os.path.join(out_dir, "%s.json" % scene["scene_id"]), "w", encoding="utf-8") as f:
            json.dump(scene, f, ensure_ascii=False, indent=1)
        miss = missing_resources(scene)
        miss_total += len(miss)
        rows.append([scene["scene_id"], scene["source"]["memory_no"] or "",
                     scene["source"]["memory_title"], scene["characters"][0]["model"],
                     len(scene["motions"]), len(scene["expressions"]),
                     len(scene.get("texts") or []),
                     len(scene["timeline"]), "OK" if not miss else "MISSING",
                     ";".join(miss[:8])])
    rows.sort(key=lambda r: r[0])

    rep = os.path.join(out_dir, "_report.csv")
    with open(rep, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scene_id", "memory_no", "title", "model",
                    "motions", "expressions", "texts", "timeline_steps", "status", "missing"])
        w.writerows(rows)

    smy = os.path.join(out_dir, "_summary.csv")
    with open(smy, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "value"])
        w.writerow(["总回想数量(MemoryData)", len(_MEM)])
        w.writerow(["回想入口事件(扫描)", len(all_scene_event_ids())])
        w.writerow(["成功转换", ok])
        w.writerow(["失败", fail])
        w.writerow(["缺失资源(条)", miss_total])
        w.writerow(["含H模型场景", len(h_event_ids())])
        w.writerow(["台词总条数", sum(len(s.get("texts") or []) for s in built)])
        w.writerow(["本次新解密语音", made])
        w.writerow(["语音缺源(条)", len(vmiss)])
    return rep, smy, rows, ok, fail, miss_total


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = ["--list"]
    if args[0] == "--list":
        ids = all_scene_event_ids()
        print("可转换事件 %d 个:" % len(ids), ids[:40], "…")
        print("回想分发覆盖回想号:", len(recall_event_map()))
    elif args[0] == "--all":
        rep, smy, rows, ok, fail, miss = export_all()
        print("逐场景报告:", rep)
        print("统计汇总  :", smy)
        print("成功 %d / 失败 %d / 缺失资源 %d 条" % (ok, fail, miss))
    else:
        eid = int(args[0].upper().replace("CE", ""))
        p, s = export(eid)
        print("已生成:", p)
        print("  ", s["scene_id"], "回想", s["source"]["memory_no"], s["source"]["memory_title"],
              "model=", s["characters"][0]["model"],
              "motion=", len(s["motions"]), "voice=", len(s["voices"]),
              "timeline=", len(s["timeline"]))
