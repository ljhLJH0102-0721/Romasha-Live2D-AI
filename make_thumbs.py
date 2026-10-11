import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage

ROOT = os.path.dirname(os.path.abspath(__file__))
PIC = os.path.join(ROOT, "web", "original", "pictures")
OUT = os.path.join(ROOT, "web", "original", "thumbs")
MAX = 360

KEEP_DIRS = {"MImage"}
SKIP_PREFIX = ("!map_", "pn_", "card_", "ui_", "$", "!")
SKIP_STEMS = {
    "acstart", "black", "black2", "white", "brown", "pink", "red",
    "e_black", "database", "longdatabase", "warning", "setup",
    "talk_back", "talkauto", "l2dloading", "live2d_checker",
    "live2d_checker_btn", "twin1a", "twin1b", "video_flame",
    "warphole", "ptcpoint", "map_kurai", "rd_event", "cutinback",
    "happyend-fin", "peepingflame", "hscene_beetle",
}

made = 0
skipped = 0
failed = 0
seen = 0

for dirpath, dirnames, filenames in os.walk(PIC):
    rel_dir = os.path.relpath(dirpath, PIC)
    if rel_dir == ".":
        keep = True
    else:
        keep = any(seg in KEEP_DIRS for seg in rel_dir.split(os.sep))
    if not keep:
        continue
    for name in filenames:
        low = name.lower()
        if not low.endswith(".png") or low.startswith(SKIP_PREFIX):
            continue
        if os.path.splitext(low)[0] in SKIP_STEMS:
            continue
        src = os.path.join(dirpath, name)
        rel = os.path.relpath(src, PIC)
        dst = os.path.join(OUT, os.path.splitext(rel)[0] + ".jpg")
        seen += 1
        if os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue
        img = QImage(src)
        if img.isNull():
            failed += 1
            continue
        if img.width() > MAX or img.height() > MAX:
            img = img.scaled(MAX, MAX, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        d = os.path.dirname(dst)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        if img.save(dst, "JPG", 82):
            made += 1
        else:
            failed += 1
        if seen % 200 == 0:
            print("progress seen=%d made=%d skipped=%d failed=%d" % (seen, made, skipped, failed), flush=True)

print("THUMBS_DONE seen=%d made=%d skipped=%d failed=%d" % (seen, made, skipped, failed), flush=True)
