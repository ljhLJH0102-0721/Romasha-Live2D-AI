"""从原作游戏里提取「回想房」数据（300 个条目 + 中文翻译 + 每个条目用到的 Live2D 场景模型）。

原作数据：
  <游戏根>/www/data/Nupu_PSData.json     -> MemoryData（300 条回想）
  <游戏根>/www/data/CommonEvents.json    -> CE52/CE178/CE179 三个派发器，按 _Mr選択回想番号 分支
                                            （分支号 = 条目 _No - 1，已用 MemoryOn(N,·) 交叉验证）
  <游戏根>/翻译文件.json                  -> 日->中 词典
  每个场景用的 Live2D 模型 -> 场景事件里的 L2*( "模型名" ) 调用
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

GAME = ("D:\\BaiduNetdiskDownload\\Romasha-Live2D-AI-main\\公主协同效应  v1.0.28\\"
        "PS-\\PS-1.0.28_PC\\PS-1.0.28_PC.7z\\princess_synergy-1.0.28")
APP = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(GAME, "www", "data")
PICS = os.path.join(APP, "web", "original", "pictures", "UI_Menu", "SexMenu", "Memory", "MImage")
ALT = os.path.join(APP, "web", "model_alt")
OUT = os.path.join(APP, "world_data", "memory_data.json")
DISPATCH = (52, 178, 179)


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


trans = {}
for cand in (os.path.join(GAME, "翻译文件.json"), os.path.join(GAME, "www", "translations.json")):
    if os.path.isfile(cand):
        trans = load(cand)
        print("翻译词典:", len(trans), "条")
        break


def zh(s):
    return trans.get(s, s) if s else ""


ce = load(os.path.join(DATA, "CommonEvents.json"))
by_id = {e["id"]: e for e in ce if e}
have_img = set()
if os.path.isdir(PICS):
    have_img = {os.path.splitext(f)[0] for f in os.listdir(PICS) if f.lower().endswith(".png")}
have_model = set()
if os.path.isdir(ALT):
    have_model = {d for d in os.listdir(ALT) if os.path.isdir(os.path.join(ALT, d))}
print("可用缩略图:", len(have_img), " 可用场景模型:", len(have_model))

MODEL_RE = re.compile(r"L2[A-Za-z0-9_]*\(\s*\"([A-Za-z0-9_]+)\"")
_memo = {}


def models_of(ceid, stack=None):
    if ceid in _memo:
        return _memo[ceid]
    if stack is None:
        stack = set()
    if ceid in stack:
        return set()
    stack = stack | {ceid}
    ev = by_id.get(ceid)
    if not ev:
        return set()
    out = set()
    for c in ev.get("list") or []:
        code = c.get("code")
        p = c.get("parameters") or []
        if code == 355 and p and isinstance(p[0], str):
            out |= set(m for m in MODEL_RE.findall(p[0]) if m in have_model)
        elif code == 117 and p:
            out |= models_of(p[0], stack)
    _memo[ceid] = out
    return out


def branch_calls(ceid, pat):
    ev = by_id.get(ceid)
    if not ev:
        return []
    cmds = ev.get("list") or []
    for i, c in enumerate(cmds):
        if c.get("code") == 111 and len(c.get("parameters") or []) > 1 \
                and isinstance(c["parameters"][1], str) and c["parameters"][1].strip() == pat:
            ind = c.get("indent", 0)
            out = []
            for c2 in cmds[i + 1:]:
                if c2.get("code") in (411, 412) and c2.get("indent", 0) == ind:
                    break
                if c2.get("code") == 117 and c2.get("parameters"):
                    out.append(c2["parameters"][0])
            return out
    return []


def scene_models(no):
    for disp in DISPATCH:
        calls = branch_calls(disp, "_Mr選択回想番号 == %d" % (no - 1))
        if calls:
            out = set()
            for cid in calls[-2:]:
                out |= models_of(cid)
            return sorted(out)
    return []


md = load(os.path.join(DATA, "Nupu_PSData.json"))["MemoryData"]
items = []
with_model = 0
for i, e in enumerate(md):
    if not isinstance(e, dict):
        continue
    no = e.get("_No", i + 1)
    ptn = e.get("_Ptn") or []
    pats = []
    for j, d in enumerate(e.get("_DtlCheck") or []):
        if not isinstance(d, dict):
            continue
        nm = zh(ptn[j]) if j < len(ptn) else ""
        tx = zh(d.get("_Setu"))
        if nm or tx:
            pats.append({"name": nm, "text": tx})
    key = "M_Image%s" % no
    models = scene_models(no)
    if models:
        with_model += 1
    items.append({
        "no": no,
        "title": zh(e.get("_Title", "")),
        "desc": zh(e.get("_Setu", "")),
        "hint": zh(e.get("_Hint", "")),
        "patterns": pats,
        "img": "UI_Menu/SexMenu/Memory/MImage/%s.png" % key,
        "thumb": "UI_Menu/SexMenu/Memory/MImage/%s.jpg" % key,
        "has_img": key in have_img,
        "scenes": models,
    })

items.sort(key=lambda x: x["no"])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=1)

print("回想条目:", len(items))
print("有标题:", sum(1 for x in items if x["title"]))
print("有台词:", sum(1 for x in items if any(p["text"] for p in x["patterns"])))
print("有图:", sum(1 for x in items if x["has_img"]))
print("带 Live2D 场景:", with_model)
print("写盘:", OUT, os.path.getsize(OUT) // 1024, "KB")
for x in items[:6]:
    print("  No%-3d %-14s scenes=%s" % (x["no"], (x["title"] or "-")[:14], x["scenes"][:3]))
