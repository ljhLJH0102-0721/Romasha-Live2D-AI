"""从原作游戏解密她的语音（RPG Maker MV .rpgmvo）。

密钥在 <游戏根>/www/data/System.json 的 encryptionKey（十六进制字符串，16 字节），
文件 = 16 字节 RPGMV 头 + 正文，正文每字节与 key[i % 16] 异或。

产出：
  voice_ref/                 -> TTS 参考音频（干净的日常台词）
  web/original/voice/touch/  -> 触摸反应用的语音（挠痒 / H 场景 / 日常）
"""
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

GAME = ("D:\\BaiduNetdiskDownload\\Romasha-Live2D-AI-main\\公主协同效应  v1.0.28\\"
        "PS-\\PS-1.0.28_PC\\PS-1.0.28_PC.7z\\princess_synergy-1.0.28")
APP = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(GAME, "www", "audio", "voice", "romasha")
REF = os.path.join(APP, "voice_ref")
TOUCH = os.path.join(APP, "web", "original", "voice", "touch")

with open(os.path.join(GAME, "www", "data", "System.json"), encoding="utf-8-sig") as f:
    keyhex = json.load(f).get("encryptionKey") or ""
KEY = bytes.fromhex(keyhex)
print("key: %s -> %d 字节" % (keyhex, len(KEY)))


def decrypt(name, dst):
    raw = open(os.path.join(VOICE, name), "rb").read()
    data = raw[16:] if raw[:5] == b"RPGMV" else raw
    out = bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(data))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(out)
    return out[:4]


files = sorted(os.listdir(VOICE))
files = [n for n in files if n.lower().endswith(".rpgmvo")]
print("语音总数:", len(files))

groups = {
    "talk": [n for n in files if n.startswith("full") and 40000 < os.path.getsize(os.path.join(VOICE, n)) < 200000],
    "kusu": [n for n in files if n.startswith("kusuguri")],
    "h": [n for n in files if n.startswith("_h") or n.startswith("h") and not n.startswith("hack")],
}
for g, v in groups.items():
    print("  %-5s 候选 %d  样例 %s" % (g, len(v), v[:3]))

made = []
os.makedirs(REF, exist_ok=True)
for i, n in enumerate(groups["talk"][:3], 1):
    dst = os.path.join(REF, "romasha_ref_%d.ogg" % i)
    magic = decrypt(n, dst)
    made.append((dst, magic, n))
    print("  参考 %-30s -> %-24s magic=%r %s" % (n, os.path.basename(dst), magic, "OK" if magic == b"OggS" else "BAD"))

for g, pick in (("kusu", groups["kusu"][:8]), ("h", groups["h"][:10]), ("talk", groups["talk"][3:13])):
    for i, n in enumerate(pick, 1):
        dst = os.path.join(TOUCH, "%s_%d.ogg" % (g, i))
        magic = decrypt(n, dst)
        if magic != b"OggS":
            os.remove(dst)
        else:
            made.append((dst, magic, n))
    ok = len([x for x in os.listdir(TOUCH) if x.startswith(g + "_")]) if os.path.isdir(TOUCH) else 0
    print("  %-5s 解密成功 %d 个 -> %s" % (g, ok, TOUCH))

tot = sum(os.path.getsize(d) for d, _, _ in made)
print("共解密 %d 个文件，%.1f MB" % (len(made), tot / 1048576))
