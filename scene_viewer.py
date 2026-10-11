# -*- coding: utf-8 -*-
"""
回想场景查看器 —— 独立窗口，专门用来"看游戏里这些场景跑起来"。
设计原则：
  * 完全独立：自己的 QApplication + 自己的网页实例
    -> 绝不影响正在运行的桌宠（互不干扰）
  * 复用同一套网页与场景数据（不复制、不改动任何现有文件）
  * 只读 world_data/scenes/*.json
用法：venv\\Scripts\\pythonw.exe scene_viewer.py
"""
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
# 【关键】没有这个参数，Chromium 会拒绝"没有用户点击过网页"的音频播放
# -> 场景里的 play_voice / play_se 全部静默失败（就是"没声音"的原因）。
# 只设在查看器进程里，桌宠的启动参数完全不动。
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
                      "--no-sandbox --disable-logging --log-level=3 "
                      "--autoplay-policy=no-user-gesture-required")

from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QPushButton,
                             QSplitter, QVBoxLayout, QWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView

SCENES_DIR = os.path.join(BASE, "world_data", "scenes")
PAGE = os.path.join(BASE, "web", "index.html")


def scan_scenes():
    out = []
    for fp in glob.glob(os.path.join(SCENES_DIR, "*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                j = json.load(f)
        except Exception:
            continue
        sid = j.get("scene_id") or os.path.basename(fp)[:-5]
        src = j.get("source") or {}
        title = (src.get("memory_title") or src.get("event_name") or "").strip()
        models = ",".join(sorted({c.get("model", "") for c in (j.get("characters") or []) if c.get("model")}))
        steps = len(j.get("timeline") or [])
        out.append({"id": sid, "title": title, "models": models, "steps": steps, "path": fp, "json": j})
    out.sort(key=lambda x: x["id"])
    return out


class SceneViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("回想场景查看器 — Princess Synergy")
        self.resize(1280, 840)
        self.scenes = scan_scenes()
        self.cur = None
        self.page_ready = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        head = QHBoxLayout()
        head.addWidget(QLabel("🔍"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索：场景ID / 标题 / 模型名（例如 shower、CE1406）")
        self.search.textChanged.connect(self.fill_list)
        head.addWidget(self.search, 1)
        self.lbl = QLabel("共 %d 个场景" % len(self.scenes))
        head.addWidget(self.lbl)
        root.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        self.list.currentRowChanged.connect(self.on_pick)
        split.addWidget(self.list)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.web = QWebEngineView()
        s = self.web.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.web.page().setBackgroundColor(Qt.black)
        self.web.load(QUrl.fromLocalFile(PAGE))
        self.web.loadFinished.connect(self.on_loaded)
        rv.addWidget(self.web, 1)

        bar = QHBoxLayout()
        self.info = QLabel("正在启动…")
        bar.addWidget(self.info, 1)
        b_replay = QPushButton("▶ 重播")
        b_replay.clicked.connect(lambda: self.play(self.cur))
        b_skip = QPushButton("⏭ 跳到动作")
        b_skip.clicked.connect(lambda: self.web.page().runJavaScript(
            "window._sceneSkipToMotion && window._sceneSkipToMotion();"))
        b_nextline = QPushButton("下一句 ▶")
        b_nextline.clicked.connect(lambda: self.web.page().runJavaScript(
            "window._sceneAdvance && window._sceneAdvance();"))
        b_stop = QPushButton("■ 停止")
        b_stop.clicked.connect(lambda: self.web.page().runJavaScript("window.closeScene && window.closeScene();"))
        b_prev = QPushButton("◀ 上一个")
        b_prev.clicked.connect(lambda: self.step(-1))
        b_next = QPushButton("下一个 ▶")
        b_next.clicked.connect(lambda: self.step(1))
        for b in (b_prev, b_replay, b_skip, b_nextline, b_stop, b_next):
            bar.addWidget(b)
        rv.addLayout(bar)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        root.addWidget(split, 1)

        self.setStyleSheet("""
            QWidget { background: #1c1219; color: #ffe6ee; font-family: 'Microsoft YaHei'; font-size: 12px; }
            QListWidget { background: #241821; border: 1px solid #ffb6c1; border-radius: 8px; padding: 4px; }
            QListWidget::item { padding: 4px 6px; border-radius: 5px; }
            QListWidget::item:selected { background: #ffb6c1; color: #3a2230; }
            QLineEdit { background: #241821; border: 1px solid #ffb6c1; border-radius: 6px;
                        padding: 5px 8px; color: #ffe6ee; }
            QPushButton { background: #ffb6c1; color: #3a2230; border: none; border-radius: 6px;
                          padding: 6px 14px; font-weight: 700; }
            QPushButton:hover { background: #ffd9e2; }
            QLabel { color: #ffd9e2; }
        """)
        self.fill_list()

    def fill_list(self):
        q = self.search.text().strip().lower()
        self.list.clear()
        for sc in self.scenes:
            text = "%s  %s  [%s]" % (sc["id"], sc["title"][:34], sc["models"])
            if q and q not in text.lower():
                continue
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, sc)
            self.list.addItem(it)
        self.lbl.setText("列出 %d / 共 %d 个场景" % (self.list.count(), len(self.scenes)))

    def on_loaded(self, ok):
        self.page_ready = bool(ok)
        self.info.setText("页面已就绪 ✓ 点击左侧场景开始播放" if ok else "页面加载失败 ✗")

    def on_pick(self, row):
        it = self.list.item(row)
        if it:
            self.play(it.data(Qt.UserRole))

    def step(self, d):
        r = self.list.currentRow() + d
        if 0 <= r < self.list.count():
            self.list.setCurrentRow(r)

    def play(self, sc):
        if not sc or not self.page_ready:
            return
        self.cur = sc
        self.info.setText("播放 %s | %s | 模型 %s | 时间线 %d 步"
                          % (sc["id"], sc["title"][:28], sc["models"], sc["steps"]))
        # 关键：playScene 是在桌宠模型加载完成后才定义的 —— 没就绪就调用会
        # 静默失效（表现：只看得到桌宠、看不到场景）。所以这里自带重试，
        # 并在播放前把桌宠本体和它的 UI 全部隐藏，只留场景画面。
        js = (
            "(function(){"
            "  var scene = %s;"
            "  function hidePet(){"
            "    try{ if(window.romashaModel){ window.romashaModel.visible = false; } }catch(e){}"
            "    ['ui-handle','input-container','ui-panel','chat-bubble','light-hint']"
            "      .forEach(function(id){ var el=document.getElementById(id);"
            "        if(el){ el.style.display='none'; } });"
            "  }"
            "  var t = 0;"
            "  function go(){"
            "    if (typeof window.playScene !== 'function') {"
            "      if (t++ < 100) { setTimeout(go, 250); return; }"
            "      return;"
            "    }"
            "    hidePet();"
            "    window.playScene(scene, false);"
            "  }"
            "  go();"
            "  return 'queued';"
            "})()" % json.dumps(sc["json"], ensure_ascii=False))
        self.web.page().runJavaScript(js)
        print("[查看器] 播放 %s（%s）模型=%s" % (sc["id"], sc["title"][:20], sc["models"]), flush=True)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = SceneViewer()
    w.show()
    print("[查看器] 已扫描 %d 个场景" % len(w.scenes), flush=True)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
