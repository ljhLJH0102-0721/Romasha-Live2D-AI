








































import sys
import os
import ctypes

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 启用 GPU 硬件加速。若沿用旧的 --disable-gpu，Live2D 的 WebGL 会回退到 CPU 软件渲染，导致 CPU 占用飙升
# 【必须】本机 UAC 为 ConsentPromptBehaviorAdmin=0（静默提权），所有进程都是管理员权限，
# Chromium 的沙箱在这种权限下无法工作 -> QtWebEngine 加载不了网页 -> 桌宠永远不显示。
# 实测：不加 --no-sandbox 时 loadFinished 永不触发；加上后 EVENT:READY 正常。
# 页面是本地 file://，禁用沙箱风险可接受。
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --log-level=3 --ignore-gpu-blocklist --no-sandbox"
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.webenginecontext.debug=false"
devnull = open(os.devnull, "w")
os.dup2(devnull.fileno(), 2)

import memory_manager
import re
import datetime
import random
import queue
import base64
import requests
import time
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QDialog, QTextBrowser, QPushButton, QProgressBar, QLineEdit,
                             QHBoxLayout, QLabel, QScrollArea, QInputDialog, QSizePolicy, QComboBox,
                             QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QRegion, QCursor, QFont, QColor, QTextCursor, QIcon                   
from urllib.parse import unquote


import llm_brain
import motion_manager
import outfit_manager
import story_manager
import lorebook_manager
import map_manager
import relationship_manager
import scene_player


                                            
                           
                                            
class NameEditDialog(QDialog):
    def __init__(self, current_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle('命运观测终端 - 玩家档案')
                            
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(320, 160)
        self.setStyleSheet("background-color: #f8f9fa; color: #333; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        label = QLabel("请输入你在这个世界中的名字：")
        label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(label)

        self.name_input = QLineEdit(self)
        self.name_input.setText(current_name)
        self.name_input.setFont(QFont("Microsoft YaHei", 11))
        self.name_input.setStyleSheet("border: 2px solid #ffb6c1; padding: 6px; border-radius: 6px; background: white;")
        layout.addWidget(self.name_input)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("确认修改")
        self.save_btn.setStyleSheet("QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ff99ab; }")
        self.save_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("QPushButton { background: #ddd; color: #333; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ccc; }")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_name(self):
        return self.name_input.text().strip()

class StoryWindow(QWidget):
                                    
    choice_made = pyqtSignal(str)
    name_changed = pyqtSignal(str)               

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Princess Synergy - 命运观测终端")
                  
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web/favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1000, 750)
                        
                                                           
        self.setWindowFlags(Qt.Window)
        self.setStyleSheet("background-color: #f8f9fa; color: #333; border-radius: 10px;")

             
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

                               
        top_bar = QHBoxLayout()
        title_label = QLabel("📖 命运世界线推演日志")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet("color: #666;")

                         
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))

        current_name = llm_brain.config.get("player_name", "未命名")
                         
        self.name_btn = QPushButton(f"👤 当前玩家: {current_name}")
        self.name_btn.setFixedWidth(180)
        self.name_btn.setStyleSheet("""
                            QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                            QPushButton:hover { background: #ff99ab; }
                        """)
        self.name_btn.clicked.connect(self.edit_player_name)

                         
                                     
        self.is_generating_story = True
        self.action_btn = QPushButton("🛑 停止推演")
        self.action_btn.setFixedWidth(120)
        self.action_btn.setStyleSheet("""
                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #c0392b; }
                """)
        self.action_btn.clicked.connect(self.toggle_generation)

                       
        self.exit_btn = QPushButton("🚪 退出推演")
        self.exit_btn.setFixedWidth(100)
        self.exit_btn.setStyleSheet("""
                    QPushButton { background: #95a5a6; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #7f8c8d; }
                """)
                                                                
        self.exit_btn.clicked.connect(self.request_exit_story)

                       
        self.level_combo = QComboBox()
        self.level_combo.addItems(["参与度 0", "参与度 1", "参与度 2", "参与度 3"])
        self.level_combo.setCurrentIndex(2)            
        self.level_combo.setStyleSheet("""
                    QComboBox { background: rgba(255,255,255,0.9); border: 1px solid #ffb6c1; border-radius: 5px; padding: 4px 18px 4px 8px; font-size: 12px; color: #6031e2; font-weight: bold; }
                    QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: none; }
                    QComboBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #6031e2; margin-right: 4px; }
                """)

        top_bar.addWidget(title_label)
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.level_combo)           
        top_bar.addWidget(self.name_btn)
        top_bar.addWidget(self.action_btn)           
        top_bar.addWidget(self.exit_btn)            
        self.layout.addLayout(top_bar)

                                  
        self.history_browser = QTextBrowser()
        self.history_browser.setFont(QFont("Microsoft YaHei", 11))
        self.history_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: #f1f3f5; 
                        border: 1px solid #ddd; 
                        border-radius: 8px; 
                        padding: 10px;
                    }
                    /* 专属滚动条美化 */
                    QScrollBar:vertical {
                        border: none; background: #e9ecef; width: 12px; margin: 2px 2px 2px 0; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1; min-height: 40px; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        border: none; background: none;
                    }
                """)
        self.layout.addWidget(self.history_browser, stretch=5)

                                  
        self.current_browser = QTextBrowser()
        self.current_browser.setFont(QFont("Microsoft YaHei", 12))
        self.current_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: #ffffff; 
                        border: 2px solid #ffb6c1; 
                        border-radius: 8px; 
                        padding: 10px;
                    }
                    /* 专属滚动条美化 */
                    QScrollBar:vertical {
                        border: none; background: transparent; width: 12px; margin: 2px 2px 2px 0; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1; min-height: 40px; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        border: none; background: none;
                    }
                """)
        self.layout.addWidget(self.current_browser, stretch=3)

                          
        self.options_widget = QWidget()
                                                              
                                                   
        self.options_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.options_main_layout = QVBoxLayout(self.options_widget)
        self.options_main_layout.setContentsMargins(0, 0, 0, 0)
        self.options_main_layout.setSpacing(12)               
                                                                             
                                   

                               
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(8)
        self.options_main_layout.addWidget(self.buttons_container)

                            
        self.custom_input_container = QWidget()
        self.custom_input_layout = QHBoxLayout(self.custom_input_container)
        self.custom_input_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_input_layout.setSpacing(8)

        self.custom_choice_input = QLineEdit()
        self.custom_choice_input.setPlaceholderText("或者...不满意选项？亲自输入你期望的走向！(按回车发送)")
        self.custom_choice_input.setFont(QFont("Microsoft YaHei", 10))
        self.custom_choice_input.setStyleSheet(
            "border: 1px solid #ffb6c1; border-radius: 5px; padding: 8px; background: white;")
                                       
        self.custom_choice_input.textChanged.connect(self.pause_countdown)
        self.custom_choice_input.returnPressed.connect(self.send_custom_choice)

        self.custom_send_btn = QPushButton("发送抉择")
        self.custom_send_btn.setFixedWidth(100)
        self.custom_send_btn.setStyleSheet(
            "QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ff99ab; }")
        self.custom_send_btn.clicked.connect(self.send_custom_choice)

        self.custom_input_layout.addWidget(self.custom_choice_input)
        self.custom_input_layout.addWidget(self.custom_send_btn)
        self.options_main_layout.addWidget(self.custom_input_container)

        self.layout.addWidget(self.options_widget, 0)
        self.options_widget.hide()

                          
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(600)                      
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
        self.layout.addWidget(self.progress_bar, 0)          
        self.progress_bar.hide()

                
        self.target_text = ""
        self.current_text = ""
        self.pending_options = []
        self.time_left = 600                     

                                     
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)

                  
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.countdown_tick)

                            
        scrollbar_style = """
                    QScrollBar:vertical {
                        border: none;
                        background: #f1f3f5;
                        width: 12px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1;
                        min-height: 30px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                """
                           
        self.setStyleSheet(self.styleSheet() + scrollbar_style)

    def edit_player_name(self):

        current_name = llm_brain.config.get("player_name", "")
                       
        dialog = NameEditDialog(current_name, self)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_name()
            if new_name:
                self.name_changed.emit(new_name)
                            
                self.name_btn.setText(f"👤 当前玩家: {new_name}")

    def toggle_generation(self):

        if self.is_generating_story:
                           
            self.typewriter_timer.stop()
            self.countdown_timer.stop()
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                QPushButton:hover { background: #27ae60; }
            """)

                        
            self.status_label.setText(" 已暂停")
            self.status_label.setStyleSheet("color: #d35400;")      

            self.choice_made.emit("/CANCEL_GENERATION")
        else:
                            
            self.countdown_timer.stop()
            self.options_widget.hide()
            self.progress_bar.hide()

                                
            self.status_label.setText(" 推演中...")
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.is_generating_story = True
            self.action_btn.setText("🛑 停止推演")
            self.action_btn.setStyleSheet("""
                                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                                    QPushButton:hover { background: #c0392b; }
                                """)

            self.choice_made.emit("*(顺应局势，继续推进剧情)*")

    def prepare_new_chapter(self, prompt_desc=""):

                                
        self.is_generating_story = True
        self.action_btn.setText("🛑 停止推演")
        self.action_btn.setStyleSheet("""
                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #c0392b; }
                """)

                        
        self.status_label.setText(" 推演中...")
        self.status_label.setStyleSheet("color: #e74c3c;")      

        self.current_browser.clear()
        self.current_text = ""
        self.target_text = ""
        self.options_widget.hide()
        self.progress_bar.hide()
                         
        for i in reversed(range(self.buttons_layout.count())):
            widget = self.buttons_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()              

                                 
        self.custom_choice_input.clear()

        if prompt_desc:
            self.history_browser.append(f"<span style='color:#6031e2;'><b>{prompt_desc}</b></span><br>")

        self.show()
        self.typewriter_timer.start(20)              

    def update_streaming_text(self, text):

        self.target_text = text

    def typewriter_tick(self):
        if self.current_text != self.target_text:
            next_idx = len(self.current_text)
            self.current_text += self.target_text[next_idx:next_idx + 4]                
                                                       
            self.current_browser.setText(self.current_text.replace("\n", "<br>"))
            cursor = self.current_browser.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.current_browser.setTextCursor(cursor)

                                   
    def finalize_chapter(self, final_text, options):

        try:
            self.typewriter_timer.stop()

                                        
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                        QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                        QPushButton:hover { background: #27ae60; }
                    """)

                                                             
            safe_text = final_text.replace("\n", "<br>")
            self.current_browser.setText(safe_text)
                             
            self.history_browser.append(f"<span style='color:#333;'>{safe_text}</span><br><br>")

                    
            self.pending_options = options
            if self.pending_options:
                                          
                self.status_label.setText(" 请抉择...")
                self.status_label.setStyleSheet("color: #2ecc71;")

                for opt_text in self.pending_options:
                    btn = QPushButton(opt_text)
                    btn.setFont(QFont("Microsoft YaHei", 10))
                    btn.setStyleSheet(
                        "QPushButton { background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 10px; text-align: left; } QPushButton:hover { background-color: #fff0f5; border: 1px solid #ffb6c1; }")
                    btn.clicked.connect(lambda checked, text=opt_text: self.on_option_clicked(text))
                    self.buttons_layout.addWidget(btn)

                self.options_widget.show()
                self.time_left = 600
                self.progress_bar.setMaximum(600)                
                self.progress_bar.setValue(600)
                                   
                self.progress_bar.setStyleSheet(
                    "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
                self.progress_bar.show()
                self.countdown_timer.start(100)

        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 选项渲染受阻 -> {e}")

    def update_chapter_text(self, final_text):

        try:
            self.typewriter_timer.stop()
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                        QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                        QPushButton:hover { background: #27ae60; }
                    """)
            safe_text = final_text.replace("\n", "<br>")
            self.current_browser.setText(safe_text)
            self.history_browser.append(f"<span style='color:#333;'>{safe_text}</span><br><br>")
        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 文本渲染受阻 -> {e}")

    def show_options(self, options):

        try:
            self.pending_options = options
            if self.pending_options:
                                          
                self.status_label.setText(" 请抉择...")
                self.status_label.setStyleSheet("color: #2ecc71;")

                                 
                for i in reversed(range(self.buttons_layout.count())):
                    widget = self.buttons_layout.itemAt(i).widget()
                    if widget is not None:
                        widget.deleteLater()              

                for opt_text in self.pending_options:
                    btn = QPushButton(opt_text)
                    btn.setFont(QFont("Microsoft YaHei", 10))
                    btn.setStyleSheet(
                        "QPushButton { background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 10px; text-align: left; } QPushButton:hover { background-color: #fff0f5; border: 1px solid #ffb6c1; }")
                    btn.clicked.connect(lambda checked, text=opt_text: self.on_option_clicked(text))
                    self.buttons_layout.addWidget(btn)

                self.options_widget.show()
                self.time_left = 600
                self.progress_bar.setMaximum(600)                
                self.progress_bar.setValue(600)
                                    
                self.progress_bar.setStyleSheet(
                    "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
                self.progress_bar.show()
                self.countdown_timer.start(100)
        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 选项渲染受阻 -> {e}")

    def countdown_tick(self):
        self.time_left -= 1
        self.progress_bar.setValue(self.time_left)
        if self.time_left <= 0:
            self.countdown_timer.stop()
            self.on_option_clicked("*(沉默不语。请顺应局势自动推进)*")

    def on_option_clicked(self, choice_text):
        self.countdown_timer.stop()
        self.options_widget.hide()
        self.progress_bar.hide()

                         
        self.status_label.setText(" 推演中...")
        self.status_label.setStyleSheet("color: #e74c3c;")
        self.is_generating_story = True
        self.action_btn.setText("🛑 停止推演")
        self.action_btn.setStyleSheet("""
                            QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                            QPushButton:hover { background: #c0392b; }
                        """)

        self.choice_made.emit(choice_text)

    def pause_countdown(self, text):

        if text.strip() and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.status_label.setText(" 抉择中 (输入中...)")
            self.status_label.setStyleSheet("color: #f39c12;")           
                                
            self.progress_bar.setStyleSheet(
                "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #f39c12; }")

    def send_custom_choice(self):

        choice_text = self.custom_choice_input.text().strip()
        if choice_text:
            self.custom_choice_input.clear()            
                                 
            self.on_option_clicked(f"*(玩家亲自干涉)*: {choice_text}")

    def clear_story_content(self):

        self.countdown_timer.stop()
        self.typewriter_timer.stop()

        self.history_browser.clear()
        self.current_browser.clear()

        self.target_text = ""
        self.current_text = ""
        self.pending_options = []
        self.time_left = 600

        self.options_widget.hide()
        self.progress_bar.hide()
        self.progress_bar.setValue(600)

        for i in reversed(range(self.buttons_layout.count())):
            widget = self.buttons_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.custom_choice_input.clear()
        self.status_label.setText("")

    def request_exit_story(self):
                                  
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('结束推演')
        msg_box.setText(
            "确定要彻底结束本次命运推演，让她回归日常模式吗？\n"
            "（当前的推演进度将不会保留在面板上，但已存入本地小说日志）"
        )
        msg_box.setIcon(QMessageBox.Question)

                   
        msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                      
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web/favicon.ico')
        if os.path.exists(icon_path):
            msg_box.setWindowIcon(QIcon(icon_path))
                      
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        yes_btn = msg_box.button(QMessageBox.Yes)
        no_btn = msg_box.button(QMessageBox.No)

                         
        yes_btn.setText("确定")
        no_btn.setText("取消")

                              
        msg_box.setDefaultButton(QMessageBox.No)

                    
        msg_box.setStyleSheet("""
                        QMessageBox {
                            background-color: #f8f9fa;
                            color: #333333;
                            font-size: 14px;
                        }
                        QLabel {
                            color: #222222;
                            font-size: 14px;
                            min-width: 420px;
                            min-height: 60px;
                        }
                """)
                             
        yes_btn.setMinimumSize(90, 34)
        no_btn.setMinimumSize(90, 34)
        yes_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #ffb6c1;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 6px 12px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #ff99ab;
                        }
                        QPushButton:pressed {
                            background-color: #ff7f96;
                        }
                """)
        no_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dddddd;
                            color: #333333;
                            border: none;
                            border-radius: 6px;
                            padding: 6px 12px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                        QPushButton:pressed {
                            background-color: #bbbbbb;
                        }
                """)
                           
        msg_box.adjustSize()
        msg_box.setMinimumWidth(520)

                     
        result = msg_box.exec_()

                      
        if result == QMessageBox.Yes:
            self.countdown_timer.stop()
            self.typewriter_timer.stop()
            self.clear_story_content()                  
            self.choice_made.emit("/EXIT_STORY_MODE")

                         
                                       
                                                        
            self.status_label.setText("")
            self.hide()

    def closeEvent(self, event):
                            
        self.countdown_timer.stop()
        self.typewriter_timer.stop()
        self.clear_story_content()
        self.choice_made.emit("/EXIT_STORY_MODE")
        self.status_label.setText("")
        self.hide()
                                         
        event.ignore()


class BrainWorker(QThread):
    chunk_received = pyqtSignal(str)
    task_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.is_cancelled = False
        self.running = True

    def run(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            user_text, interrupted_text = task
            self.is_cancelled = False

            if user_text == "/SYSTEM_RESET_MEMORY":
                try:
                                             
                    memory_manager.clear_all_memories()
                                           
                    llm_brain.chat_history.clear()
                    story_manager.clear_recent_chat_history()
                                         
                    story_manager.clear_summary()
                                                
                    lorebook_manager.clear_dynamic_lore()
                                             
                    map_manager.clear_dynamic_map()
                    map_manager.map_instance.reload_dynamic_locations()
                                                     
                    relationship_manager.clear_relationship_state()
                                                
                    story_manager.archive_novel_log()
                                                            
                    llm_brain.config["intimacy"] = 0
                                            
                    llm_brain.config["player_name"] = ""
                                               
                    llm_brain.config["current_location"] = "罗玛莎的房间门口"
                    llm_brain.config["current_chapter"] = 1
                    llm_brain.config["is_first_encounter"] = True                          
                                                               
                    llm_brain.config["saved_outfit"] = ""
                    llm_brain.config["saved_hair"] = ""
                    llm_brain.config["saved_outfit_period"] = ""
                    llm_brain.config["night_outfit_roll_key"] = ""
                    llm_brain.config["night_outfit_result"] = ""
                    llm_brain.config["last_recent_chat_time"] = 0
                    llm_brain.save_config()
                    print("💔 [记忆消散]: 曾经相处的点滴如沙般流逝，你们回到了最初相遇时的陌生与戒备。\n")

                except Exception as e:
                    print(f"⚠️ [命运纠缠]: 过去的痕迹似乎难以抹除 ({e})")
                self.task_queue.task_done()
                continue

                              
            if user_text.startswith("/STORY_TICK_"):
                try:
                                                 
                                                
                    parts = user_text.split("_", 3)
                    level = parts[2]
                    choice_text = parts[3] if len(parts) > 3 else ""

                    llm_brain.stream_story_with_romasha(level, choice_text, self)
                except Exception as e:
                    print(f"⚠️ [命运纠缠]: 故事线推演失败 ({e})")

                if not self.is_cancelled:
                    self.task_finished.emit()
                self.task_queue.task_done()
                continue

            try:
                llm_brain.stream_chat_with_romasha(user_text, interrupted_text, self)
            except Exception as e:
                print(f"⚠️ [思绪迷茫]: 她的思绪似乎被某种未知的烦恼打断了 ({e})")

            if not self.is_cancelled:
                self.task_finished.emit()

            self.task_queue.task_done()

    def interrupt_and_submit(self, user_text, interrupted_text):
        self.is_cancelled = True
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        self.task_queue.put((user_text, interrupted_text))


class TTSWorker(QThread):
                                  
    audio_ready = pyqtSignal(str, bool, str)                  

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.running = True
        self.is_cancelled = False             

                 
    def translate_to_japanese(self, text):
        try:
            api_type = llm_brain.config.get("api_type", "openai").lower()
            messages = [
                {"role": "system", "content": "你是一个精准的中译日翻译器，请将玩家的中文台词精准直译翻译成对应的日文。【极其重要】：如果文本中包含形如 [quick_breath]、[sigh] 等英文控制标签，你必须原样保留它们，并将它们插入到日文中合理的位置。绝对不要翻译这些方括号内的标签！只需要输出最终的日文结果，不要任何解释。"},
                {"role": "user", "content": text}
            ]
            if api_type == "openai":
                response = llm_brain.client.chat.completions.create(
                    model=llm_brain.TARGET_MODEL,
                    messages=messages,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            elif api_type == "ollama":
                base_url = llm_brain.config.get("base_url", "").rstrip('/')
                if not base_url.endswith('/api/chat'):
                    base_url = f"{base_url}/api/chat"
                payload = {"model": llm_brain.TARGET_MODEL, "messages": messages, "stream": False, "options": {"temperature": 0.3}}
                headers = {"Content-Type": "application/json"}
                api_key = llm_brain.config.get("api_key", "")
                if api_key: headers["Authorization"] = f"Bearer {api_key}"
                resp = requests.post(base_url, json=payload, headers=headers, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", text).strip()
        except Exception as e:
            print(f"\n⚠️ [意识干扰]: 那种古老的语调在脑海中变得模糊，你只能靠直觉去理解她想表达的意思...")
            print(f"   (🛠️ 隐秘线索: 思绪转译受阻，已回退至熟悉的语言 - {str(e)[:50]})")
            return text

    def infer_cosy_instruct_from_tags(self, raw_text):








        text_lower = raw_text.lower()

                                       
                        
                                       
        mood_base = {
            "mood_talk_alc": "害羞娇柔",
            "mood_talk_ero": "委屈含泪",
            "mood_talk": "温柔轻软",
            "mood_neutral": "平静轻柔",
            "mood_wait": "安静压低声音",
            "mood_wait_haji": "小声迟疑嘀咕",
        }
                                       
                          
                                       
        act_overlay = {
                     
            "act_amazing": "惊讶慌乱",
            "act_smallamazing": "轻微惊讶",
            "act_guruguru": "极度羞涩混乱",
            "act_trouble": "不知所措",
            "act_smallgikuri": "心虚慌张",
            "act_question": "疑惑试探",
                          
            "act_angry": "羞愤抗拒",
            "act_smallangry": "小声抗议",
            "act_smallangryb": "压抑不满",
            "act_donbiki": "嫌弃退缩",
            "act_poster": "坚决拒绝",
            "act_chui": "轻声制止",
                     
            "act_sad": "委屈难过",
            "act_relief": "放松轻叹",
            "act_iyaiya": "无奈羞耻",
                          
            "act_hatujo": "极度羞涩喘息",
            "act_skirt": "受惊娇羞",
            "act_skirt_bust": "胸口被碰到后慌乱羞涩",
            "act_skirt_hip": "臀部被碰到后慌乱羞涩",
            "act_taol_fall": "浴巾滑落后极度慌乱羞耻",
            "act_doya": "脸红得意",
            "act_smalldoya": "小小得意可爱",
                     
            "act_smile": "开心温柔",
            "act_smallsmile": "轻柔微笑",
            "act_troublesmile": "尴尬赔笑",
            "act_victory": "得意轻快",
                
            "act_device": "轻声走神",
            "act_neutral": "平静轻柔",
            "act_talk": "自然温柔",
        }
        mood_part = None
        act_part = None
                   
        for k, v in mood_base.items():
            if f"[{k}]" in text_lower:
                mood_part = v
                break
                 
        for k, v in act_overlay.items():
            if f"[{k}]" in text_lower:
                act_part = v
                break
                                       
                 
                                       
        if act_part and mood_part:
                                
            if act_part in mood_part or mood_part in act_part:
                return f"{act_part}的少女音"
            return f"{act_part}且{mood_part}的少女音"
        if act_part:
            return f"{act_part}的少女音"
        if mood_part:
            return f"{mood_part}的少女音"
                
        return "温柔轻软的少女音"

    def run(self):
        while self.running:
            try:
                text = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self.is_cancelled = False              

                                    
                                           
                                                                       
            clean_text = re.sub(r'\[(act_|mood_|intimacy_|wear_|hair_|set_name_|move_to_|sys_chapter_up).*?\]', '', text)
            clean_text = re.sub(r'（内心：.*?）', '', clean_text)
            clean_text = clean_text.strip()

            if not clean_text:
                                                          
                                    
                self.audio_ready.emit("", True, "empty")
                self.task_queue.task_done()
                continue

                                                   
                                           
            instruct_text = ""
                                               
            match = re.match(r'^(.*?)<\|endofprompt\|>(.*)$', clean_text, re.DOTALL)
            if match:
                raw_instruct = match.group(1)          
                                                   
                instruct_text = re.sub(r'[^\w\u4e00-\u9fa5]', '', raw_instruct)
                clean_text = match.group(2).strip()                                
                                   
                clean_text = clean_text.replace("<|endofprompt|>", "")
                                        
                if len(instruct_text) < 2 and llm_brain.config.get("tts_engine", "cosyvoice") == "cosyvoice":
                    instruct_text = self.infer_cosy_instruct_from_tags(text)
                    print(f"🎭 [CosyVoice自动修正]: 模型前缀异常，已回退为动作推断 -> {instruct_text}")
            else:
                                                              
                if llm_brain.config.get("tts_engine", "cosyvoice") == "cosyvoice":
                    instruct_text = self.infer_cosy_instruct_from_tags(text)
                    print(
                        f"🎭 [CosyVoice自动补偿]: 检测到缺失 <|endofprompt|>，已根据动作标签推断语气 -> {instruct_text}")

                                                   
            if llm_brain.config.get("tts_translate_to_ja", False) and clean_text:
                print("\n🌐 [古老回音]: 她的嘴唇微动，吐出的似乎是前文明遗留下的某种古老而温柔的语调...")
                clean_text = self.translate_to_japanese(clean_text)
                print(f"   (✨ 呢喃: {clean_text})")

            try:
                tts_engine = llm_brain.config.get("tts_engine", "cosyvoice")
                                                                
                proxies = {"http": None, "https": None}

                if tts_engine == "cosyvoice":
                                               
                    final_tts_text = clean_text
                    url = llm_brain.config.get("cosy_url", "")
                    payload = {
                        "text": final_tts_text,
                        "character_name": llm_brain.config.get("cosy_character", ""),
                        "mode": llm_brain.config.get("cosy_mode", ""),
                        "instruct_text": instruct_text,                
                        "speed": 1.0
                    }
                    response = requests.post(url, json=payload, proxies=proxies, timeout=60.0)

                                                                  
                    if self.is_cancelled:
                        print("🔇 [底层拦截]: 语音生成完毕，但已被玩家的最新举动打断，该语音包作废。")
                        self.task_queue.task_done()
                        continue

                    if response.status_code == 200:
                        b64_audio = base64.b64encode(response.content).decode('utf-8')
                        self.audio_ready.emit(b64_audio, True, "success")
                    else:
                                                        
                        print(
                            f"\n🔇 [感官剥离]: 也许是基地的磁场干扰，或者是她太过紧张，她的声音细若游丝，瞬间消散在冰冷的空气中...")
                        print(f"   (🛠️ 隐秘线索: 发声器官(CosyVoice)共振失败，状态码 {response.status_code})")
                        self.audio_ready.emit("", False, "api_error")

                else:
                                               
                                                 
                    sovits_text = re.sub(r'^.*?<\|endofprompt\|>', '', clean_text)
                                                               
                    sovits_text = re.sub(r'\[.*?\]', '', sovits_text).strip()
                    url = llm_brain.config.get("sovits_url", "")
                                                              
                                                                     
                                                   
                                                      
                    params = {
                        "refer_wav_path": llm_brain.config.get("sovits_ref_audio", ""),
                        "prompt_text": llm_brain.config.get("sovits_ref_text", ""),
                        "prompt_language": llm_brain.config.get("sovits_ref_lang", ""),         
                        "text":sovits_text,             
                        "text_language": llm_brain.config.get("sovits_target_lang", "")
                    }

                                                                 
                    response = requests.get(url, params=params, proxies=proxies, timeout=60.0)

                                                              
                    if self.is_cancelled:
                        print("🔇 [底层拦截]: SoVITS语音生成完毕，但已被玩家打断，作废。")
                        self.task_queue.task_done()
                        continue

                    if response.status_code == 200:
                                              
                        b64_audio = base64.b64encode(response.content).decode('utf-8')
                        self.audio_ready.emit(b64_audio, True, "success")
                    else:
                        print(f"\n🔇 [听觉迷雾]: 她的声音似乎被某种无形的屏障阻挡了...")
                        print(
                            f"   (🛠️ 隐秘线索: API拒绝了请求，状态码 {response.status_code}，原因: {response.text[:100]})")
                        self.audio_ready.emit("", False, "api_error")

            except requests.exceptions.ConnectionError:
                                                  
                print(f"\n🔇 [听觉迷雾]: 周围的环境有些嘈杂，你只能看着她微动的双唇，却听不清声音。")
                print(f"   (🛠️ 隐秘线索: GPT-SoVITS/CosyVoice API未启动或端口错误，已瞬间触发防卡死保护！)")
                self.audio_ready.emit("", False, "connection_error")
            except requests.exceptions.ProxyError:
                print(f"\n🔇 [听觉迷雾]: 一阵莫名的耳鸣让你短暂失聪，无法听清她的话语...")
                print(f"   (🛠️ 隐秘线索: 网络代理干扰了本地连接，尝试关闭代理软件)")
                self.audio_ready.emit("", False, "proxy_error")
            except requests.exceptions.Timeout:
                print(f"\n🔇 [听觉迷雾]: 她似乎在犹豫，声音卡在了喉咙里，过了好一会都没能发出声来...")
                print(
                    f"   (🛠️ 隐秘线索: 处理超过了 60 秒。因为电脑配置较差，显卡可能仍在加载模型，请耐心再跟她聊一句试试)")
                self.audio_ready.emit("", False, "timeout")
            except Exception as e:
                print(f"\n🔇 [听觉迷雾]: 也许是太紧张了，她的声音细若游丝，几乎无法捕捉...")
                print(f"   (🛠️ 隐秘线索: 底层连接失败，错误详情: {str(e)[:150]})")
                self.audio_ready.emit("", False, "unknown_error")

            self.task_queue.task_done()


# 原作 Live2D 场景：内部名 -> 显示名。带 ♥ 的视为色色(H)场景。
L2D_SCENE_LABELS = {
    "romasha_doggy": "♥ 后背位", "romasha_Cowgirl": "♥ 骑乘位",
    "romasha_fellatio": "♥ 口交", "romasha_paizuri": "♥ 乳交",
    "romasha_tekoki": "♥ 手交", "romasha_sixnine": "♥ 69式",
    "romasha_analfuck": "♥ 后门", "romasha_chichimomi": "♥ 揉胸",
    "romasha_masturbation": "♥ 自慰", "romasha_masturbation_batalle": "♥ 自慰(战斗)",
    "romasha_kiss": "♥ 接吻", "romasha_koibito": "♥ 恋人亲昵",
    "romasha_kusuguri": "♥ 挠痒", "romasha_lovebath": "♥ 恩爱入浴",
    "romasha_massaging_ass": "♥ 揉臀", "romasha_press": "♥ 压上",
    "romasha_side": "♥ 侧位", "romasha_front": "♥ 正面位",
    "romasha_bridge": "♥ 桥式", "romasha_frog": "♥ 蛙式",
    "romasha_squat": "♥ 蹲姿", "romasha_tawashi": "♥ 缠绕",
    "romasha_takinobori": "♥ 抱腿立", "romasha_slime": "♥ 史莱姆",
    "romasha_spider": "♥ 蜘蛛", "romasha_urafuzoku": "♥ 背面服务",
    "hadaka_game": "♥ 全裸",
    "high_leg_romasha": "♥ 抬腿(罗玛莎)", "high_leg_kajua": "♥ 抬腿(卡茱)",
    "high_leg_vanilla": "♥ 抬腿(香草)", "high_leg_mob1": "♥ 抬腿(路人1)",
    "high_leg_mob2": "♥ 抬腿(路人2)", "high_leg_mob3": "♥ 抬腿(路人3)",
    "vanilla_piston": "♥ 活塞(香草)", "kajua_piston": "♥ 活塞(卡茱)",
    "wall_hip": "♥ 靠墙", "cutin_masturbation": "♥ 自慰·切入",
    "anal_tekoki": "♥ 后门手交", "Lotion": "♥ 润滑液",
    "zizi_Cowgirl": "♥ 骑乘(吉吉)", "zizi_masturbation": "♥ 自慰(吉吉)",
    "freece_rape": "♥ 侵犯(弗莉丝)", "freece_kusuguri": "♥ 挠痒(弗莉丝)",
    "mizel_rape": "♥ 侵犯(米赛尔)", "supina_Imprisonment": "♥ 拘束(斯皮娜)",
    "supina_tekoki": "♥ 手交(斯皮娜)", "tenpo_tinpo": "♥ 天妇罗",
    "romasha_castoff": "脱衣", "romasha_shower": "淋浴",
    "romasha_toilet": "厕所", "romasha_wash": "洗身",
    "romasha_swiming": "游泳", "romasha_sitdown": "坐下",
    "romasha_standback": "背后站立", "romasha_kick": "踢击",
    "romasha_kick2": "踢击2", "romasha_battale": "战斗",
    "romasha_battale2": "战斗2", "romasha_battleback": "战斗·背面",
    "romasha_battleback2": "战斗·背面2", "romasha_capsule": "胶囊舱",
    "romasha_billiards": "台球桌", "romasha_icecream": "冰淇淋",
    "romasha_hear": "听诊", "romasha_plane": "飞机",
    "romasha_pushups": "俯卧撑", "romasha_kudari_omote": "流下(表)",
    "romasha_kudari_ura": "流下(里)",
    "bath_time": "入浴", "deepbreath": "深呼吸",
    "zizi_birth": "分娩(吉吉)", "zizi_foot": "足(吉吉)",
    "freece_toilet": "厕所(弗莉丝)", "supina_sleep": "睡颜(斯皮娜)",
    "risa": "莉莎", "goblin_rose": "哥布林", "dragon": "龙",
    "last_boss": "最终BOSS", "smile": "微笑", "alcol": "酒精",
    "rubber suit": "胶衣", "H_Coin laundry": "自助洗衣店",
}


class RomashaDesktop(QMainWindow):
    def __init__(self):
        super().__init__()

        self.accumulated_text = ""
        self.processed_tags = set()

                              
        self.current_context_html = ""                         
        self.target_display_text = ""                     
        self.current_display_text = ""                      

        self.final_clean_text = ""                  
        self.is_waiting_for_voice = False                  

        self.pending_tags = []                    
        self.is_current_mood_static = False                          

        self.current_idle_motion = motion_manager.get_motion_index('talk')
        self.motion_revert_timer = QTimer(self)
        self.motion_revert_timer.setSingleShot(True)
        self.motion_revert_timer.timeout.connect(self.revert_to_idle_motion)

                                              
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)
        self.typewriter_timer.start(40)

                                    
        self.is_showing_notification = False
        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self.restore_bubble_state)

                                
        self.static_mood_timer = QTimer(self)
        self.static_mood_timer.setSingleShot(True)
        self.static_mood_timer.timeout.connect(self.resolve_static_mood)

                           
        self.has_random_taol_fall_triggered = False                     
        self.taol_recover_timer = QTimer(self)
        self.taol_recover_timer.setSingleShot(True)
        self.taol_recover_timer.timeout.connect(self.recover_taol_fall)

                                     
        self.last_text_finish_time = datetime.datetime.now()

                             
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.silently_save_config)

                                                
        self.speech_end_timer = QTimer(self)
        self.speech_end_timer.setSingleShot(True)
        self.speech_end_timer.timeout.connect(self.on_speech_finished)

        self.brain_worker = BrainWorker()
        self.brain_worker.chunk_received.connect(self.handle_stream_chunk)
        self.brain_worker.task_finished.connect(self.on_task_finished)
        self.brain_worker.start()

        self.tts_worker = TTSWorker()
        self.tts_worker.audio_ready.connect(self.play_voice)
        self.tts_worker.start()

                          
        self.is_tracking_enabled = True
        self.is_touch_enabled = True                      
        self.touch_temp_locked = False                  

                                        
        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.track_global_mouse)
                                                 

        self.last_act_tag = ""
        self.last_act_time = 0

        self.init_ui()

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'favicon.ico')))
        tray_menu = QMenu()
        show_action = QAction('显示桌宠', self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction('退出 Romasha', self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)
        self.tray_icon.show()

    # =================================================================
    # 【统一退出清理】只在"程序退出"时执行，幂等；不影响日常运行。
    # 背景：原来只有走 closeEvent 才会停计时器/等工作线程，一旦从托盘退出
    # 或被结束任务，线程和计时器还活着就被销毁 -> Qt5Core.dll 里
    # 0xc0000409 崩溃（事件日志里能查到，签名固定）。
    # 现在把清理挂到 aboutToQuit 上，任何退出方式都会先干净地收尾。
    # =================================================================
    def _graceful_shutdown(self):
        # Hide the tray icon on exit. Force-killing a Qt app leaves a ghost
        # tray icon behind in Windows, which is why so many piled up.
        try:
            if getattr(self, 'tray_icon', None) is not None:
                self.tray_icon.hide()
                self.tray_icon.setVisible(False)
                print('\U0001F9F9 [exit-guard]: tray icon removed', flush=True)
        except Exception:
            pass

        if getattr(self, "_shutting_down", False):
            return
        self._shutting_down = True
        for _n in ("motion_revert_timer", "typewriter_timer", "notification_timer",
                   "static_mood_timer", "taol_recover_timer", "auto_save_timer",
                   "speech_end_timer", "idle_timer", "time_check_timer", "mouse_timer",
                   "_alpha_timer", "_game_timer"):
            try:
                _t = getattr(self, _n, None)
                if _t is not None:
                    _t.stop()
            except Exception:
                pass
        try:
            self.brain_worker.is_cancelled = True
            self.tts_worker.is_cancelled = True
            self.brain_worker.running = False
            self.tts_worker.running = False
            self.brain_worker.wait()
            self.tts_worker.wait()
        except Exception:
            pass

    def closeEvent(self, event):
        event.ignore()
        self.hide()

                            
        self.story_window = StoryWindow()
        self.story_window.choice_made.connect(self.handle_story_choice)
        self.story_window.name_changed.connect(self.update_player_name)

    def init_ui(self):
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

                                      
        screen = QApplication.primaryScreen().geometry()
                                            
        width = int(screen.width())
        height = screen.height() - 1

                
        x = (screen.width() - width) // 2
        y = 0        
        self.setGeometry(x, y, width, height)
                                                               

                                                       
                                
        self.clearMask()

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                                   
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        self.browser.page().setBackgroundColor(Qt.transparent)

        self.browser.titleChanged.connect(self.on_html_signal)

        # ---- 逐像素 alpha 命中测试：取位图 ----
        # 网页把位图放在 window.__alphaPayload 里，这里轮询取走。
        # 不能走 document.title：位图约 5KB，窗口标题会被截断，收到的是残图。
        self._alpha_timer = QTimer(self)
        self._alpha_timer.setInterval(120)
        self._alpha_timer.timeout.connect(self._poll_alpha)
        self._alpha_timer.start()
        # ROMASHA_ALPHA_HIT=0 时彻底关掉网页侧的位图计算（省掉那点开销）
        if os.environ.get("ROMASHA_ALPHA_HIT") == "0":
            QTimer.singleShot(3000, lambda: self.browser.page().runJavaScript(
                "window.__ALPHA_HIT_ENABLED = false;"))

        # ---- 游戏模式检测（每 4 秒问一次系统：现在是不是在全屏游戏？）----
        # ---- 游戏模式：① 前台进程白名单 ② Ctrl+Alt+G 手动开关 ----
        self._sleep = False
        self._manual_game = False
        self._game_mode = False
        try:
            import ctypes
            # MOD_ALT(1) | MOD_CONTROL(2) + G
            pass  # 热键也已停用（避免误按后卡在不可响应状态）
        except Exception:
            pass
        # 【已停用】游戏模式整体关掉：实测它曾让她卡在"不响应"状态，
        # 看起来就像桌宠不见了/打不开。代码全部保留（_game_mode_tick /
        # _apply_game_mode / window.setSleepMode / WM_HOTKEY），
        # 以后要做成"有屏幕提示 + 绝不卡住"的版本再启用。
        self._game_timer = QTimer(self)
        self._game_timer.setInterval(3000)
        self._game_timer.timeout.connect(self._game_mode_tick)
        self._game_timer.start()
        self._last_game_seen = 0.0
        self._sleep = False
        self._outfit_snapshots = {}
        # 【开局记录标准状态】开局她看起来是正常的（用户反馈"一开始挺好"），
        # 所以等她稳定 20 秒后，把当前这套衣服的【全部参数】记下来当标准；
        # 以后每次穿这套就照这份整份还原 —— 也就是"把她穿回去"。
        try:
            def _boot_snapshot():
                try:
                    _n = (llm_brain.config.get("saved_outfit") or "").strip() or "towel"
                    print("\U0001F4E4 [标准状态] 开局记录：当前衣服 = %s" % _n, flush=True)
                    self._outfit_snapshot_step(_n)
                except Exception as _e:
                    print("[标准状态] 开局记录失败: %s" % _e, flush=True)
            QTimer.singleShot(20000, _boot_snapshot)
        except Exception:
            pass
        self._manual_game = False
        QTimer.singleShot(6000, self._push_gm_ui)
        # ---- 旧的自动检测（已停用）----
        # 实测 SHQueryUserNotificationState() 在本机恒返回 QUNS_BUSY(2)
        # （环境里常驻全屏窗口），自动判定会把她永久休眠 -> 暂时关掉。
        # 相关代码保留（_game_mode_tick / _apply_game_mode / window.setSleepMode），
        # 以后换成更可靠的触发方式（游戏进程白名单 / 手动开关）再启用。
        self._game_mode = False

        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'web', 'index.html'))
        start_page = QUrl.fromLocalFile(html_path)
        try:
            saved_model = (llm_brain.config.get("live2d_model") or "").strip()
            if saved_model:
                start_page.setFragment("model=" + saved_model)
                print("🧍 [立绘]: 沿用上次选择的立绘 -> %s" % saved_model)
        except Exception:
            pass
        self.browser.load(start_page)
        layout.addWidget(self.browser)
        self.setCentralWidget(central_widget)

                                       
        self.thought_idle_seconds = 0             
        self.vision_idle_seconds = 0             
        self.vision_sleep_count = 0              
        self.next_idle_trigger_minutes = 3                   
        self.current_idle_target_seconds = 180                  
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.idle_tick)

                                         
        self.current_time_period = "unknown"

                                     
        self.time_check_timer = QTimer(self)
        self.time_check_timer.timeout.connect(self.check_routine_outfit)
        self.time_check_timer.start(60000)                   

    def silently_save_config(self):
                          
        llm_brain.save_config()
                                           
                                        

    def show_system_notification(self, html_text, duration=1500):

        self.is_showing_notification = True
        safe_html = html_text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

                                     
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                                                
        self.notification_timer.start(duration)

    def update_player_name(self, new_name):
        llm_brain.config["player_name"] = new_name
        llm_brain.save_config()
                    
        self.show_system_notification(
            f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(玩家名字已更新为：{new_name})</i></span>",
            2000)

    def handle_story_choice(self, choice_text):

        if choice_text == "/CANCEL_GENERATION":
                                     
            self.brain_worker.is_cancelled = True
            self.story_window.current_browser.append(
                "<br><br><span style='color:#e74c3c;'><b>[系统]: ⚠️ 推演已被手动强行中止。你可以直接在下方做出抉择。</b></span>")
                             
            self.flush_pending_tags()
            self.is_waiting_for_voice = False
            self.touch_temp_locked = False
            self.refresh_touch_state()
            return

        if choice_text == "/EXIT_STORY_MODE":
            self.is_story_mode = False
            self.pending_story_options = []
                                                   
            self.brain_worker.is_cancelled = True

                                           
            self.flush_pending_tags()
            self.is_waiting_for_voice = False
            self.touch_temp_locked = False
            self.refresh_touch_state()

            self.show_system_notification(
                "<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(命运观测终端已关闭，切回日常模式...)</i></span>",
                3000)
            print("\n💻 [观测终端]: 命运观测的窗口渐渐暗下，世界线推演暂时收束，她重新回到了与你的日常相对之中。")
            return

                      
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚖️ 命运抉择: {choice_text}")

                        
        self.show_system_notification("<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在推演下个阶段的未来...)</i></span>", 4000)

                                                 
        current_level = str(self.story_window.level_combo.currentIndex())
        self.start_new_thought(f"/STORY_TICK_{current_level}_{choice_text}")


    def restore_bubble_state(self):

        self.is_showing_notification = False

                                                    
        if getattr(self, 'is_story_mode', False):
            bubble_html = "<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在进行世界线深度推演，请在日志面板查看...)</i></span>"
            self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\", true);")
            return
                  

                                        
        if self.is_waiting_for_voice:
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(微启双唇，正在酝酿要说的话...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                       
        elif self.current_display_text != self.target_display_text:
                                                 
                                             
            pass

                                      
        else:
                                                      
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text

                                                        
            clean_text_len = len(re.sub(r'<[^>]+>', '', final_html))
            display_time_seconds = max(5.0, clean_text_len * 0.3)

                               
            elapsed = (datetime.datetime.now() - getattr(self, 'last_text_finish_time',
                                                         datetime.datetime.now())).total_seconds()

            if elapsed < display_time_seconds:
                                 
                safe_html = final_html.replace("'", "\\'")
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")
            else:
                                      
                self.browser.page().runJavaScript("document.getElementById('chat-bubble').style.opacity = 0;")

    def get_time_period_info(self, now=None):







        now = now or datetime.datetime.now()
        hour = now.hour

                            
        holidays = {
            (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节", (4, 1): "愚人节",
            (5, 1): "劳动节", (5, 4): "青年节", (6, 1): "儿童节", (8, 1): "建军节",
            (9, 10): "教师节", (10, 1): "国庆节", (10, 31): "万圣节", (11, 11): "光棍节",
            (12, 24): "平安夜", (12, 25): "圣诞节", (12, 31): "跨年夜"
        }

                                   
                   
                                   
        if hour >= 22 or hour <= 6:
            base_period = "night"
                           
            anchor_date = now.date() if hour >= 22 else (now - datetime.timedelta(days=1)).date()
        elif hour >= 19:
            base_period = "evening"
            anchor_date = now.date()
        else:
            base_period = "day"
            anchor_date = now.date()
                                   
                  
                                   
        holiday_month = anchor_date.month
        holiday_day = anchor_date.day
        is_holiday = (holiday_month, holiday_day) in holidays
        holiday_name = holidays.get((holiday_month, holiday_day))

                                     
        is_cold = anchor_date.month in [10, 11, 12, 1, 2, 3]

        if is_holiday:
            return {
                "period_key": f"holiday_{base_period}_{anchor_date.isoformat()}_{holiday_month}_{holiday_day}",
                "holiday_name": holiday_name,
                "is_holiday": True,
                "is_cold": is_cold,
                "is_night": base_period == "night",
                "is_evening": base_period == "evening",
                "is_day": base_period == "day"
            }
                                   
                 
                                   
        return {
            "period_key": f"{base_period}_{anchor_date.isoformat()}",
            "holiday_name": None,
            "is_holiday": False,
            "is_cold": is_cold,
            "is_night": base_period == "night",
            "is_evening": base_period == "evening",
            "is_day": base_period == "day"
        }

    def persist_current_outfit_state(self, period_key):



        state = outfit_manager.export_state()
        llm_brain.config["saved_outfit"] = state["outfit"]
        llm_brain.config["saved_hair"] = state["hair"]
        llm_brain.config["saved_outfit_period"] = period_key
        llm_brain.save_config()

    def apply_initial_state(self):
        now = datetime.datetime.now()
        info = self.get_time_period_info(now)
        period_key = info["period_key"]
        current_intimacy = llm_brain.config.get("intimacy", 0)

        saved_outfit = llm_brain.config.get("saved_outfit", "")
        saved_hair = llm_brain.config.get("saved_hair", "")
        saved_period = llm_brain.config.get("saved_outfit_period", "")

        def decide_target_outfit():




                                       
                          
                                       
            if info["is_holiday"]:
                if info["is_night"]:
                    if current_intimacy >= 75:
                        roll_key = llm_brain.config.get("night_outfit_roll_key", "")
                        roll_result = llm_brain.config.get("night_outfit_result", "")

                                        
                        if roll_key == period_key and roll_result in ["towel", "sleepwear"]:
                            return roll_result

                        result = "towel" if random.random() < 0.10 else "sleepwear"
                        llm_brain.config["night_outfit_roll_key"] = period_key
                        llm_brain.config["night_outfit_result"] = result
                        llm_brain.save_config()

                        if result == "towel":
                            print("\n🛁 [节日夜色]: 节日的夜已经深了，Romasha 似乎刚洗完澡。")
                        return result

                    return "sleepwear"

                                
                return "ethnic_cloak" if info["is_cold"] else "ethnic_wear"

                                       
                   
                                       
            if info["is_night"]:
                if current_intimacy >= 75:
                    roll_key = llm_brain.config.get("night_outfit_roll_key", "")
                    roll_result = llm_brain.config.get("night_outfit_result", "")

                                    
                    if roll_key == period_key and roll_result in ["towel", "sleepwear"]:
                        return roll_result

                    result = "towel" if random.random() < 0.10 else "sleepwear"
                    llm_brain.config["night_outfit_roll_key"] = period_key
                    llm_brain.config["night_outfit_result"] = result
                    llm_brain.save_config()

                    if result == "towel":
                        print("\n🛁 [时光流转]: 夜深了，Romasha 似乎刚洗完澡...")
                    return result

                return "sleepwear"

                                       
                   
                                       
            if info["is_evening"]:
                return "uniform_dress"

                                       
                   
                                       
            return "uniform_tight"

        target_outfit = decide_target_outfit()

                                        
                                   
        self.current_time_period = period_key

        if saved_outfit in outfit_manager.OUTFITS and saved_period == period_key:
            outfit_manager.restore_state(
                saved_outfit,
                saved_hair if saved_hair in outfit_manager.HAIRSTYLES else None
            )
            params = outfit_manager.get_outfit_params(
                saved_outfit,
                saved_hair if saved_hair in outfit_manager.HAIRSTYLES else None
            )
        else:
            params = outfit_manager.get_outfit_params(target_outfit)
                                      
            if info["is_holiday"] and info["holiday_name"] and not info["is_night"]:
                print(
                    f"\n🎉 [节日风信]: 今天是{info['holiday_name']}，她似乎也顺着空气里那点微妙的节日气息，悄悄换上了更合时宜的衣装。")
            elif target_outfit == "towel":
                print(f"\n👗 [观察]: 夜深了，听到浴室传来隐约的水声后，Romasha裹着浴巾走了出来。")
            elif target_outfit == "sleepwear":
                print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换上了轻薄的睡衣。")
            else:
                print(f"\n👗 [观察]: Romasha已经换上了一身适合现在的衣服。")

        for param_id, val in params.items():
            self.set_parameter(param_id, val)

                                     
        self.persist_current_outfit_state(period_key)

    def track_global_mouse(self):
                           
        if self.is_tracking_enabled:
            pos = self.mapFromGlobal(QCursor.pos())
            if not getattr(self, "_game_mode", False):
                self.browser.page().runJavaScript(f"window.updateGlobalMouse({pos.x()}, {pos.y()});")

    def refresh_touch_state(self):

        enabled_str = "true" if self.is_touch_enabled else "false"
        busy_str = "true" if self.touch_temp_locked else "false"
        self.browser.page().runJavaScript(f"window.toggleTouch({enabled_str});")
        self.browser.page().runJavaScript(f"window.toggleTouchBusy({busy_str});")

    TOUCH_SHY = {"bust": "wait_haji", "crotch": "smallgikuri", "hip": "skirt(hip)"}
    TOUCH_ERO = {"bust": "talk_ero", "crotch": "talk_ero", "hip": "skirt(bust)"}
    TOUCH_CALM = {"head": "relief", "face": "smallsmile",
                  "hand_right": "smile", "hand_left": "smile",
                  "belly": "smallgikuri", "leg": "trouble"}

    INSTANT_TOUCH_LINES = {
        "head": "「……唔。」她没有躲开，眼睛微微眯了起来。",
        "face": "「你老盯着我脸看干嘛。」她别开视线，耳根却红了。",
        "hand_right": "她没有抽回手，指尖反而轻轻勾住了你。",
        "hand_left": "「牵着就牵着吧。」她小声说。",
        "belly": "「……别碰腰，痒。」她扭了一下身子。",
        "leg": "「手往哪儿放呢。」她拍开了你的手。",
    }
    INSTANT_SHY_LINES = {
        "bust": "「……！」她猛地一颤，手臂下意识护在胸前，脸一下烧红了。",
        "crotch": "「等、等一下——」她膝盖一软，声音都变了调。",
        "hip": "「！」她整个人一僵，随即回头瞪了你一眼。",
    }
    INSTANT_ERO_LINES = {
        "bust": "「你、你别一直摸那里……」她声音发颤，却没有真的推开你。",
        "crotch": "「不行……皓皓，你手别动……」她嘴上这么说，腿却并得更紧了。",
        "hip": "「……你越来越过分了。」她说得凶，呼吸却乱了。",
    }
    INSTANT_HEAT_LINES = {
        "bust": "「嗯……皓皓，你这样……我会忍不住的……」她咬着唇，眼神开始发飘。",
        "crotch": "「唔……别停……」她自己都没意识到说了什么，脸埋在肩上。",
        "hip": "「啊……你、你故意的吧。」她腰一软，整个人靠向你。",
    }
    INSTANT_STRIP = "「啊……！」最后一件也滑落了，她慌忙用手臂遮住胸口，红着眼眶瞪你：「你、你是故意的吧……」"

    TOUCH_VOICE_CACHE = None

    def touch_voice_file(self, part):
        sensitive = ("bust", "crotch", "hip")
        cat = "kusu" if part == "belly" else ("h" if part in sensitive else "talk")
        cls = type(self)
        if cls.TOUCH_VOICE_CACHE is None:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "web", "original", "voice", "touch")
            cache = {"kusu": [], "h": [], "talk": []}
            if os.path.isdir(base):
                for f in sorted(os.listdir(base)):
                    if not f.lower().endswith(".ogg"):
                        continue
                    for c in ("kusu", "h", "talk"):
                        if f.startswith(c + "_"):
                            cache[c].append("original/voice/touch/" + f)
            cls.TOUCH_VOICE_CACHE = cache
        files = cls.TOUCH_VOICE_CACHE.get(cat) or []
        return random.choice(files) if files else None

    def react_to_touch(self, part):
        import json as _json
        import time
        sensitive = ("bust", "crotch", "hip")
        now = time.time()
        if now - getattr(self, "_touch_last_ts", 0) > 25:
            self._touch_streak = 0
        self._touch_last_ts = now

        if part in sensitive:
            streak = getattr(self, "_touch_streak", 0) + 1
            self._touch_streak = streak
            if streak <= 1:
                motion = self.TOUCH_SHY.get(part)
                line = self.INSTANT_SHY_LINES.get(part)
            elif streak == 2:
                motion = self.TOUCH_ERO.get(part)
                line = self.INSTANT_ERO_LINES.get(part)
            elif streak == 3:
                motion = "hatujo"
                line = self.INSTANT_HEAT_LINES.get(part)
            elif streak == 4:
                # 【加料】第 4 下：换成更撩的裙摆动作（都是她自己的动作，
                # 不跨模型、绝不变形）
                motion = {"bust": "skirt(bust)", "hip": "skirt(hip)"}.get(part, "talk_ero")
                line = self.INSTANT_ERO_LINES.get(part)
            else:
                motion = "talk_ero"
                line = self.INSTANT_HEAT_LINES.get(part)
        else:
            streak = 0
            self._touch_streak = 0
            motion = self.TOUCH_CALM.get(part)
            line = self.INSTANT_TOUCH_LINES.get(part)

        if motion:
            self.browser.page().runJavaScript(
                "window.playMotionByName(%s);" % _json.dumps(motion),
                lambda r: print("✋ [触摸]: %s -> 播放动作 %s -> %s" % (part, motion, r)))
        if streak:
            print("✋ [触摸]: 敏感部位连续第 %d 次（动作 %s）" % (streak, motion or "无"))

        if llm_brain.config.get("touch_voice", True):
            vf = self.touch_voice_file(part)
            if vf:
                self.browser.page().runJavaScript("window.playVoiceFile(%s);" % _json.dumps(vf))
                print("🔊 [语音]: 播放 %s" % vf)

        if streak == 5:
            # 【只在指定衣服下才会滑落】默认只认浴衣/浴巾(towel)。
            # 换成别的衣服时，到极限也只是"受不了"，衣服不会掉。
            # 想改成别的衣服：把 config.json 的 strip_outfit 改成对应名字。
            want = str(llm_brain.config.get("strip_outfit", "towel") or "").strip()
            cur = ""
            try:
                cur = (outfit_manager.export_state() or {}).get("outfit", "") or ""
            except Exception:
                cur = llm_brain.config.get("saved_outfit", "") or ""
            if want and cur == want:
                print("✋ [触摸]: 浴衣状态下到了极限 —— 衣服滑落（换装 -> 裸体）")
                # 【真·掉落动画】看她穿的是什么，播对应的原作场景：
                #   浴巾(towel) -> 淋浴脱衣 S_shower*   （浴巾掉落）
                #   其它衣服        -> 脱衣 castoff*      （衣物滑落，卡在腿上）
                # 场景播完会自动释放、自动切回她。
                # 下面的三拍参数版同时生效，作为场景缺失时的兜底。
                try:
                    # 【已停用】自定义场景播完不会正确释放模型，她会卡在场景模型上
                    # （表现为"切回浴巾不重置、立绘还是浴巾卡腿"）。
                    # 场景文件保留在 world_data/scenes/CASTOFF_*.json，
                    # 以后补上 wait/say 节奏、能盯着画面验证时再启用。
                    # 【只有浴巾才播场景】实测 romasha_castoff 只有 38 个参数，
                    # 完全没有衣服参数 -> 它只能脱它自己那身（看起来是浴巾）。
                    # 所以：浴巾 = 正好对得上，播真动画；其它衣服 = 播了反而是错的，
                    # 改用下面的三拍参数掉落。
                    # 【已停用】按你的要求不要这个场景动画。
                    # 掉落统一走下面的三拍参数版：稳定、不会卡在场景模型上、
                    # 也不会出现"脱成浴巾"（那个模型只有 38 个参数、没有衣服开关）。
                    _ok = False

                    print("\U0001F3AC [掉落] 播放场景 %s -> %s"
                          % (_sid, "成功" if _ok else "失败（用三拍兜底）"), flush=True)
                except Exception as _e:
                    print("\U0001F3AC [掉落] 场景异常: %s" % _e, flush=True)
                # 【分三拍掉落】没有现成的"脱衣"动作，所以用节奏 + 她自己的
                # 衣服参数来"演"：毛巾先滑 -> 内衣 -> 最后成型。观感上是掉了，
                # 而且全程只动她自己模型的参数（绝不跨模型，不会变形）。
                self._take_param_snapshot()   # 【先存快照】掉落前的完整状态
                # 【按衣服分类】播这套衣服自己的掉落动作（见 outfit_manager.OUTFIT_DROP）
                try:
                    import json as _json
                    _m = outfit_manager.drop_motion(cur)
                    if _m:
                        self.browser.page().runJavaScript(
                            "window.playMotionByName(%s);" % _json.dumps(_m))
                        print("\U0001F457 [\u6389\u843d] \u300c%s\u300d\u7684\u4e13\u5c5e\u52a8\u4f5c: %s" % (cur, _m), flush=True)
                    else:
                        print("\U0001F457 [\u6389\u843d] \u300c%s\u300d\u6ca1\u6709\u53ef\u6389\u7684\u4e1c\u897f\uff0c\u8df3\u8fc7" % cur, flush=True)
                except Exception:
                    pass
                # 【掉落特效】白闪 + 她下沉回弹 + 抖动（纯 PIXI，无素材）
                try:
                    self.browser.page().runJavaScript("window.dropEffect && window.dropEffect();")
                except Exception:
                    pass
                try:
                    self.browser.page().runJavaScript("window.playMotionByName('wait_haji');")
                    self.set_parameter('bath_taol_ON', 1.0)          # 第1拍：浴巾滑落（1=脱下）
                    print("\U0001F457 [掉落] 第1拍：浴巾滑落", flush=True)
                except Exception:
                    pass

                def _drop2():
                    try:
                        self.browser.page().runJavaScript("window.playMotionByName('smallgikuri');")
                        self.set_parameter('buraONFOFF', 30.0)       # 第2拍：内衣
                        print("\U0001F457 [掉落] 第2拍：内衣滑落", flush=True)
                    except Exception:
                        pass

                def _drop3():
                    try:
                        self.apply_outfit("nude")                    # 第3拍：成型
                        self.browser.page().runJavaScript("window.playMotionByName('talk_ero');")
                        print("\U0001F457 [掉落] 第3拍：完全滑落", flush=True)
                    except Exception:
                        pass

                QTimer.singleShot(450, _drop2)
                QTimer.singleShot(950, _drop3)
                self._touch_streak = 0
                # 【自动复位】约 20 秒后她自己把衣服穿回去
                # （浴巾之后当然要拉上）。只会复位一次，不会反复。
                def _restore(o=cur):
                    # 优先用快照逐项还原（保证和掉落前一模一样）
                    snap = getattr(self, "_param_snapshot", None)
                    if snap:
                        try:
                            n = 0
                            for _k, _v in snap.items():
                                try:
                                    self.set_parameter(_k, _v)
                                    n += 1
                                except Exception:
                                    pass
                            print("\U0001F496 [还原] 已按快照原样还原她（%d 个参数）" % n, flush=True)
                            return
                        except Exception as _e:
                            print("\U0001F496 [还原] 快照还原失败: %s" % _e, flush=True)
                    try:
                        self.apply_outfit(o)
                        self.browser.page().runJavaScript("window.playMotionByName('smallgikuri');")
                        print("👘 [换装]: 20 秒后她自己把「%s」穿回了。" % o, flush=True)
                    except Exception as e:
                        print("[复位] 失败 %s" % e, flush=True)
                # 用可取消的计时器：玩家一旦手动换装（见 OUTFIT:SET 分支），
                # 这个待执行的"自动穿回"必须作废，绝不允许它覆盖玩家的选择。
                try:
                    if getattr(self, "_restore_timer", None):
                        self._restore_timer.stop()
                except Exception:
                    pass
                self._restore_timer = QTimer(self)
                self._restore_timer.setSingleShot(True)
                self._restore_timer.timeout.connect(_restore)
                self._restore_timer.start(20000)
                return self.INSTANT_STRIP
            print("✋ [触摸]: 已到极限（当前衣服 %s 不会滑落，需要 strip_outfit=%s）"
                  % (cur or "(未知)", want))
            self._touch_streak = 0
            self.browser.page().runJavaScript("window.playMotionByName('smallangryB');")
            return None
        return line or ""

    def get_touch_prompt(self, part):










        rel = relationship_manager.load_relationship_state()
                                                                  
                                                
                                                                  
        stage = rel.get("current_relationship_stage", "stranger")
        highest_stage = rel.get("highest_relationship_stage", "stranger")
                  
        physical = rel.get("physical_intimacy_stage", 0)
                 
        accepted = set(rel.get("accepted_touch_zones", []))
                 
        attitude = rel.get("current_attitude", "normal")
        temp_distance = rel.get("temporary_distance_level", 0)
        blocked = set(rel.get("temporary_blocked_touch_zones", []))
              
        first_night = rel.get("first_night_completed", False)
        current_intimacy = llm_brain.config.get("intimacy", 0)

                                       
                         
                                       
        default_map = {
            "head": "*你轻轻摸了摸她的头*",
            "face": "*你轻轻碰了碰她的脸颊*",
            "hand_right": "*你牵起了她的右手*",
            "hand_left": "*你握住了她的左手*",
            "belly": "*你轻轻碰到了她的腰侧*",
            "leg": "*你碰到了她的腿*",
            "hip": "*你碰到了她的臀侧*",
            "bust": "*你碰到了她胸前敏感的位置*",
            "crotch": "*你触碰到了她极其私密的区域*",
            "unknown": "*你轻轻碰了碰她*"
        }

                                                                  
                       
                              
                                 
                                                                  
        if part in blocked:
            if (
                    stage in ["lovers", "bonded", "married"]
                    or highest_stage in ["bonded", "married"]
                    or current_intimacy >= 80
            ):
                if part == "bust":
                    return "*你的动作靠近了她胸前敏感的位置，而她现在显然不太想那里被碰*"
                if part == "hip":
                    return "*你的手碰到了她腰臀附近，而她现在似乎不太愿意你继续在那里停留*"
                if part == "crotch":
                    return "*你的动作靠近了她最私密的区域，而她现在明显不想那里被碰*"
            if part == "bust":
                return "*你的动作靠近了她胸前敏感的位置*"
            if part == "hip":
                return "*你的手碰到了她腰臀附近*"
            if part == "crotch":
                return "*你的动作靠近了她极其私密的区域*"
            return default_map.get(part, default_map["unknown"])
                                                                  
                              
                        
                                 
                                                                  
        if attitude in ["hurt", "distant", "cold"] or temp_distance >= 40:
            guarded_map = {
                "head": "*你试着轻轻摸了摸她的头*",
                "face": "*你小心地碰了碰她的脸颊*",
                "hand_right": "*你试着碰了碰她的右手*",
                "hand_left": "*你轻轻碰到了她的左手*",
                "belly": "*你碰到了她的腰侧*",
                "leg": "*你靠近时碰到了她的腿*",
                "hip": "*你的手碰到了她腰臀附近*",
                "bust": "*你的动作靠近了她胸前敏感的位置*",
                "crotch": "*你的动作靠近了她极其私密的区域*",
                "unknown": "*你轻轻碰了碰她*"
            }
                                                   
                                           
            return guarded_map.get(part, guarded_map["unknown"])

                                                                      
                                        
                                                                      
        if (
                stage == "close"
                or (stage == "trusted" and current_intimacy >= 55)
                or (highest_stage in ["lovers", "bonded", "married"] and current_intimacy >= 60)
        ):
            if part == "head":
                return "*你温柔地摸了摸她的头*"
            if part == "face":
                return "*你轻轻抚过她的脸颊*"
            if part == "hand_right":
                return "*你自然地牵起了她的右手*"
            if part == "hand_left":
                return "*你轻轻握住了她的左手*"
            if part == "belly":
                return "*你轻轻扶住了她的腰*"
            if part == "leg":
                return "*你贴近时碰到了她的腿*"
            return default_map.get(part, default_map["unknown"])
                                       
                                       
                                       
        if stage in ["lovers", "bonded", "married"] or (
                highest_stage in ["lovers", "bonded", "married"] and current_intimacy >= 80
        ):
            if part == "head":
                return "*你温柔地摸了摸她的头*"
            if part == "face":
                return "*你轻轻抚过她的脸颊*"
            if part == "hand_right":
                return "*你自然地牵起了她的右手*"
            if part == "hand_left":
                return "*你轻轻握住了她的左手*"
            if part == "belly":
                return "*你从身后轻轻环住了她的腰*"
            if part == "leg":
                return "*你贴近她时，手碰到了她的腿*"

                                           
            if part == "hip":
                if physical >= 4 or "hip" in accepted:
                    return "*你贴近她，手轻轻落在她腰臀一侧*"
                return "*你碰到了她的臀侧*"

                                    
            if part == "bust":
                if physical >= 5 or "bust" in accepted:
                    return "*你贴近她时，手触到了她胸前柔软的位置*" + self.outfit_context_note()
                return "*你碰到了她胸前敏感的位置*"

                                                  
            if part == "crotch":
                if physical >= 5 and first_night:
                    return "*在彼此早已熟悉的亲密距离里，你碰到了她最私密的地方*" + self.outfit_context_note()
                return "*你的动作靠近了她极其私密的区域*"

        return default_map.get(part, default_map["unknown"])

    def reset_afk(self):
                                               
        was_deep_sleeping = (self.vision_idle_seconds >= 300)

                            
        self.thought_idle_seconds = 0
        self.vision_idle_seconds = 0
        self.vision_sleep_count = 0               
        self.next_idle_trigger_minutes = 3
        self.current_idle_target_seconds = 180

                                   
        if self.is_tracking_enabled:
            self.browser.page().runJavaScript("window.toggleTracking(true);")

                    
                                                    
                                                   
        if was_deep_sleeping:
                                                                         
                      
            self.set_idle_motion(self.current_idle_motion)

    def idle_tick(self):
                                          
        if getattr(self, 'is_story_mode', False):
            return

                                                       
        is_generating = (not self.brain_worker.task_queue.empty()) or self.is_waiting_for_voice or getattr(self,
                                                                                                           'is_typing',
                                                                                                           False)

        self.vision_idle_seconds += 1                               
                                 
        if not is_generating:
            self.thought_idle_seconds += 1

                                     
        if self.vision_idle_seconds == 300:
            self.browser.page().runJavaScript("window.toggleTracking(false);")
                                                                                             
                                         
            self.set_idle_motion(motion_manager.get_motion_index('talk'))

                                
            if self.vision_sleep_count == 0:
                print(f"\n💤 [观察]: 经过一段时间的静默，Romasha收起思绪，沉浸到了自己的世界中。")
            elif self.vision_sleep_count == 1:
                print(f"\n💤 [观察]: 刚才的挪动并没有引起Romasha进一步的注意，她的视线再次移开，继续发呆了。")
            else:
                print(f"\n💤 [观察]: 仿佛已经习惯了这种无声的摆弄，Romasha只是安静地待在新的位置，依然没有看你。")

            self.vision_sleep_count += 1

                                                   
        if self.thought_idle_seconds == self.current_idle_target_seconds:
                          
            current_intimacy = llm_brain.config.get("intimacy", 0)
            if current_intimacy > 90 and outfit_manager._current_outfit == "towel" and not self.has_random_taol_fall_triggered:
                if random.random() < 0.2:
                    self.has_random_taol_fall_triggered = True
                    sys_prompt = "[系统机制：由于长时间的安静，加上你的动作幅度，你身上裹着的浴巾突然意外滑落了！你完全没防备。请立刻输出带有 [act_taol_fall] 标签的动作反应，并伴随一句极其慌乱、娇羞的惊呼或心声。]"
                    self.start_new_thought(sys_prompt)

                                             
                    self.next_idle_trigger_minutes += random.randint(3, 10)
                    self.current_idle_target_seconds = self.thought_idle_seconds + (self.next_idle_trigger_minutes * 60)
                    return

            self.trigger_idle_thought(minutes=self.thought_idle_seconds // 60)

                      
            self.next_idle_trigger_minutes += random.randint(3, 10)

                           
            self.current_idle_target_seconds = self.thought_idle_seconds + (self.next_idle_trigger_minutes * 60)


    def trigger_idle_thought(self, minutes):
        if minutes == 3:
                                      
            sys_prompt = "[系统机制：距离刚才的互动已经安静了整整 3 分钟。请结合刚才的对话氛围、彼此关系与当前情境，自主判断他现在的大致状态（例如仍在安静陪伴、只是暂时没有说话、在做自己的事，或已经离开）。请根据你此时真实的心情，输出一小段自言自语、轻声呢喃或内心独白（使用括号表示心声）。你可以保留刚才互动时的情绪余温，也可以自然改变动作；若你主观上拿不准，也可以表现出迟疑、安静感知或很轻的试探。注意：不要机械罗列可能性，而是直接给出符合你当下判断的自然反应。]"
        else:
                                          
            sys_prompt = f"[系统机制：对方已经持续安静了 {minutes} 分钟。请根据这个时长、之前的对话上下文、当前时间氛围，以及你自身的直觉，自主推断他现在的状态（例如仍在身边沉默、已经睡着、暂时离开、或你只能感觉到他的存在感已经变淡）。你的视线可以自然移开，不必一直看着他。此时你可以选择让情绪渐渐平复（切换回普通的 talk 等待机动作），或者继续沉浸在自己的世界里小声嘀咕、发呆。请给出一小段符合你当前主观判断的心声、自言自语或动作反应。注意：不要把判断说得像系统播报，应像一个真实的人凭感觉作出的自然反应。]"

                                 
        self.current_context_html = f"<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(漫长的安静中，Romasha 似乎在想些什么...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(安静中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

        self.start_new_thought(sys_prompt)

    def resolve_static_mood(self):
                                          
        if getattr(self, 'is_story_mode', False):
            return

                                             
        if self.vision_idle_seconds < 300:
                                            
            sys_prompt = "[系统机制：你刚才已经维持静止发呆或小声嘀咕 15 秒了。请根据你此刻的情绪，决定切换回正常的动态常态动作（如 mood_talk, mood_talk_alc 等）。你可以小声嘟囔一句话、说一两句心声，也可以什么都不说只输出动作标签。]"

            self.current_context_html = f"<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(短暂的定格后，她似乎有了动作...)</i></span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(调整状态...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

            self.start_new_thought(sys_prompt)

    def revert_to_idle_motion(self):
        self.set_parameter('ParamCheek', 0.0)
        self.set_parameter('angry', 0.0)
                                                                     
                         
        self.set_idle_motion(self.current_idle_motion)

    def check_routine_outfit(self):
        now = datetime.datetime.now()
        info = self.get_time_period_info(now)
        period_key = info["period_key"]
        current_intimacy = llm_brain.config.get("intimacy", 0)

                             
        def decide_target_outfit():
                                       
                          
                                       
            if info["is_holiday"]:
                                           
                if info["is_night"]:
                    if current_intimacy >= 75:
                        roll_key = llm_brain.config.get("night_outfit_roll_key", "")
                        roll_result = llm_brain.config.get("night_outfit_result", "")

                                        
                        if roll_key == period_key and roll_result in ["towel", "sleepwear"]:
                            return roll_result

                        result = "towel" if random.random() < 0.10 else "sleepwear"
                        llm_brain.config["night_outfit_roll_key"] = period_key
                        llm_brain.config["night_outfit_result"] = result
                        llm_brain.save_config()

                        if result == "towel":
                            print("\n🛁 [节日夜色]: 节日的夜已经深了，Romasha 似乎刚洗完澡。")
                        return result

                    return "sleepwear"

                                
                return "ethnic_cloak" if info["is_cold"] else "ethnic_wear"

                                       
                   
                                       
            if info["is_night"]:
                if current_intimacy >= 75:
                    roll_key = llm_brain.config.get("night_outfit_roll_key", "")
                    roll_result = llm_brain.config.get("night_outfit_result", "")

                                    
                    if roll_key == period_key and roll_result in ["towel", "sleepwear"]:
                        return roll_result

                    result = "towel" if random.random() < 0.10 else "sleepwear"
                    llm_brain.config["night_outfit_roll_key"] = period_key
                    llm_brain.config["night_outfit_result"] = result
                    llm_brain.save_config()

                    if result == "towel":
                        print("\n🛁 [时光流转]: 夜深了，Romasha 似乎刚洗完澡...")
                    return result

                return "sleepwear"

                                       
                   
                                       
            if info["is_evening"]:
                return "uniform_dress"

                                       
                   
                                       
            return "uniform_tight"

        target_outfit = decide_target_outfit()

                                               
        if getattr(self, 'current_time_period', "unknown") == "unknown":
            self.current_time_period = period_key
            return

                                                              
                                                                      
        if period_key != self.current_time_period:
            self.current_time_period = period_key

                                              
            if getattr(self, 'manual_outfit_lock', False):
                if info["is_day"]:
                                                    
                    self.manual_outfit_lock = False
                else:
                                                  
                    return

                               
            if target_outfit and target_outfit != outfit_manager._current_outfit:
                if info["is_holiday"] and info["holiday_name"]:
                    print(
                        f"\n🎉 [节日风信]: 今天是{info['holiday_name']}，她似乎也顺着空气里那点微妙的节日气息，悄悄换上了更合时宜的衣装。")
                elif target_outfit == "towel":
                    print(f"\n👗 [观察]: 夜深了，听到浴室传来隐约的水声后，Romasha裹着浴巾走了出来。")
                elif target_outfit == "sleepwear":
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换上了轻薄的睡衣。")
                else:
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换了一身适合现在的衣服。")

                                   
                if info["is_holiday"] and info["holiday_name"]:
                    bubble_html = f"<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(仿佛是顺着 {info['holiday_name']} 的气息，她悄悄换上了一身更合时宜的衣装...)</i></span><br>"
                else:
                    bubble_html = "<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(一阵轻微的窸窣声后，她换好了一身衣服...)</i></span><br>"
                self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\");")

                                                         
                QTimer.singleShot(3000, lambda: self._apply_delayed_outfit_with_persist(target_outfit, period_key))

                         
                                                                     
                                                 
                                                  

                       
    def _apply_delayed_outfit_with_persist(self, target_outfit, period_key):



        params = outfit_manager.get_outfit_params(target_outfit)
        for param_id, val in params.items():
            self.set_parameter(param_id, val)
        self.persist_current_outfit_state(period_key)

    def push_model_list(self):
        import json as _json
        from urllib.parse import quote as _quote
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        alt_dir = os.path.join(web_dir, "model_alt")
        default_url = "model/romasha_talk.model3.json"
        labels = L2D_SCENE_LABELS
        current = (llm_brain.config.get("live2d_model") or "").strip() or default_url
        items = []
        try:
            for name in sorted(os.listdir(alt_dir)):
                d = os.path.join(alt_dir, name)
                if not os.path.isdir(d):
                    continue
                cand = sorted(f for f in os.listdir(d) if f.lower().endswith(".model3.json"))
                if not cand:
                    continue
                url = "model_alt/" + _quote(name) + "/" + _quote(cand[0])
                items.append({"name": labels.get(name, name), "tip": name,
                              "url": url, "active": url == current})
        except Exception as e:
            print("扫描原作模型失败: %s" % e)
        items = sorted(items, key=lambda x: (0 if str(x["name"]).startswith("♥") else 1, x["name"]))
        try:
            js = "window.setModelList(" + _json.dumps(items, ensure_ascii=False) + ");"
            self.browser.page().runJavaScript(js)
            print("🧍 [立绘]: 已推送 %d 个可选立绘。" % len(items))
        except Exception as e:
            print("推送立绘清单失败: %s" % e)

    def switch_live2d_model(self, url):
        import json as _json
        from urllib.parse import unquote as _unquote
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        default_url = "model/romasha_talk.model3.json"
        target = (url or "").strip()
        if target == default_url:
            target = ""
        if target:
            disk = os.path.join(web_dir, _unquote(target).replace("/", os.sep))
            if not os.path.isfile(disk):
                print("⚠️ [立绘]: 找不到模型文件，已取消切换 -> %s" % target)
                return
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            snapshot = dict(llm_brain.config)
            snapshot["live2d_model"] = target
            with open(cfg_path, "w", encoding="utf-8") as f:
                _json.dump(snapshot, f, ensure_ascii=False, indent=2)
            llm_brain.config["live2d_model"] = target
        except Exception as e:
            print("⚠️ [立绘]: 保存配置失败 %s" % e)
        start_url = target or default_url
        js = ("try{window.location.hash='model=%s';window.location.reload();}"
              "catch(e){document.title='EVENT:LOAD_ERROR:switch_failed';}") % start_url
        self.browser.page().runJavaScript(js)
        print("🧍 [立绘]: 正在切换 -> %s（页面重载中）" % start_url)

    def push_h_scene_list(self):
        """「回想」列表：由 world_data/scenes/ 的 Scene 数据库驱动。"""
        import json as _json
        items = []
        for m in scene_player.list_scene_metas():
            items.append(m)
        try:
            js = "window.setHSceneList(" + _json.dumps(items, ensure_ascii=False) + ");"
            self.browser.page().runJavaScript(js)
            print("🎬 [Scene]: 已推送 %d 个原作场景（点击 = play_scene）" % len(items))
        except Exception as e:
            print("推送场景失败: %s" % e)

    def play_scene(self, scene_id):
        """播放 world_data/scenes/<scene_id>.json 定义的场景（转换层产物）。"""
        return scene_player.play_scene(self.browser, scene_id)

    def push_outfit_list(self):
        import json as _json
        labels = {
            "uniform_tight": "紧身制服", "uniform_dress": "制服裙", "sleepwear": "睡衣",
            "swimsuit": "泳装", "ethnic_wear": "民族服",
            "ethnic_cloak": "民族服·披风", "towel": "浴巾", "bunny": "兔女郎", "nude": "裸体",
        }
        hair_labels = {"loose": "披发", "bun": "丸子头"}
        state = outfit_manager.export_state()
        cur_outfit = state.get("outfit") or llm_brain.config.get("saved_outfit", "")
        cur_hair = state.get("hair") or llm_brain.config.get("saved_hair", "")
        acc_labels = {
            "leotard": "紧身连衣",
            "fundoshi": "兜裆布",
            "minzoku": "民族胸布腰布",
            "heart_eye": "心形眼",
            "gaze": "视线",
            "pierce": "乳环",
            "milk": "乳汁",
            "tattoo": "纹身",
            "blush": "脸红",
            "bigbust": "胸部大小"}
        accs = list(llm_brain.config.get("accessories") or [])
        # 【三层独立】服装层只放互斥的那 9 套；配饰层单独推，可多选叠加
        data = {
            "outfits": [{"name": n, "label": labels.get(n, n), "active": n == cur_outfit}
                        for n in outfit_manager.OUTFITS if n not in self.ACCESSORY_KEYS],
            "accessories": [{"name": n, "label": acc_labels.get(n, labels.get(n, n)), "active": n in accs}
                            for n in self.ACCESSORY_KEYS],
            "hairs": [{"name": n, "label": hair_labels.get(n, n), "active": n == cur_hair}
                      for n in outfit_manager.HAIRSTYLES],
        }
        try:
            js = "window.setOutfitList(" + _json.dumps(data, ensure_ascii=False) + ");"
            self.browser.page().runJavaScript(js)
            print("👗 [换装]: 清单已推送（%d 套服装 / %d 件配饰 / %d 种发型），当前：%s / %s"
                  % (len(data["outfits"]), len(data["accessories"]), len(data["hairs"]), cur_outfit, cur_hair))
        except Exception as e:
            print("推送换装清单失败: %s" % e)

    # =================================================================
    # 【三层独立】服装 / 配饰 / 发型 互不干扰：
    #   服装层 = OUTFITS 里那 9 套（互斥）
    #   配饰层 = 下面这 10 件（可多选叠加，存在 config["accessories"] 里）
    #   发型层 = 2 种（存在 config["saved_hair"] 里）
    # 换衣服不会清掉配饰（BASE_STATE 清完后再把配饰推一遍）；
    # 点配饰 = 开/关切换，不会换掉身上的衣服。
    # =================================================================
    ACCESSORY_KEYS = ("leotard", "fundoshi", "minzoku", "heart_eye", "gaze",
                      "pierce", "milk", "tattoo", "blush", "bigbust")

    def apply_accessories(self):
        """把当前选中的配饰逐个叠加推上去（必须在 BASE_STATE 之后调用）。"""
        try:
            names = list(llm_brain.config.get("accessories") or [])
        except Exception:
            names = []
        n = 0
        for nm in names:
            d = (outfit_manager.OUTFITS.get(nm) or {})
            for k, v in d.items():
                if k == "formchange":
                    continue
                self.set_parameter(k, v)
                n += 1
        if names:
            print("\U0001F48E [\u914d\u9970]: \u53e0\u52a0 %s\uff08%d \u4e2a\u53c2\u6570\uff09"
                  % ("+".join(names), n), flush=True)

    def toggle_accessory(self, name):
        """点配饰 = 开/关；不改动身上的衣服。"""
        cur = list(llm_brain.config.get("accessories") or [])
        if name in cur:
            cur.remove(name); on = False
        else:
            cur.append(name); on = True
        llm_brain.config["accessories"] = cur
        llm_brain.save_config()
        print("\U0001F48E [\u914d\u9970]: %s \u300c%s\u300d\uff08\u5f53\u524d: %s\uff09"
              % ("\u7a7f\u4e0a" if on else "\u8131\u4e0b", name, "+".join(cur) or "\u65e0"), flush=True)
        # 重新推一遍：先回基础态清干净，再叠衣服 + 配饰
        try:
            self.apply_outfit(llm_brain.config.get("saved_outfit") or "uniform_tight",
                              llm_brain.config.get("saved_hair") or None)
        except Exception as e:
            print("[\u914d\u9970] \u91cd\u65b0\u5e94\u7528\u5931\u8d25: %s" % e, flush=True)

    def apply_outfit(self, name, hair=None, react=False):
        if name not in outfit_manager.OUTFITS:
            print("⚠️ [换装]: 未知的衣服 -> %s" % name)
            return
        if hair is None:
            hair = llm_brain.config.get("saved_hair") or None
        if hair not in outfit_manager.HAIRSTYLES:
            hair = None
        try:
            params = outfit_manager.get_outfit_params(name, hair)
            for param_id, val in params.items():
                self.set_parameter(param_id, val)
            # 把"这套衣服自己的掉落动作"同步给网页（拖拽松手时用它）
            try:
                import json as _json
                self.browser.page().runJavaScript(
                    "window.__dropMotion = %s;" % _json.dumps(outfit_manager.drop_motion(name) or ""))
                self.browser.page().runJavaScript(
                    "window.__dropReal = %s;" % ("true" if (outfit_manager.OUTFIT_DROP.get(name) or {}).get("real") else "false"))
                self._pushed_drop_for = name
            except Exception:
                pass
            # 有"标准状态"就直接整份覆盖（同一帧内完成，避免闪一下表值的样子）
            try:
                _snap = (getattr(self, "_outfit_snapshots", None) or {}).get(name)
                if _snap:
                    for _k, _v in _snap.items():
                        self.set_parameter(_k, _v)
                    print("\U0001F457 [\u6362\u88c5]: \u5df2\u6309\u6807\u51c6\u72b6\u6001\u628a\u300c%s\u300d\u7a7f\u56de\uff08%d \u4e2a\u53c2\u6570\uff09" % (name, len(_snap)), flush=True)
            except Exception as e:
                print("[\u6362\u88c5] \u6807\u51c6\u72b6\u6001\u8fd8\u539f\u5931\u8d25: %s" % e, flush=True)
            self.persist_current_outfit_state(self.current_time_period)
            state = outfit_manager.export_state()
            print("👗 [换装]: 已换上「%s」，发型「%s」，参数 %d 个已推送到模型。"
                  % (name, state.get("hair"), len(params)))
            self.push_outfit_list()
            # 【穿回去】第一次穿这套 -> 记下标准状态；以后每次穿这套 -> 整份还原
            try:
                QTimer.singleShot(1200, lambda _n=name: self._outfit_snapshot_step(_n))
            except Exception:
                pass
            # 【诊断】0.4 秒后把模型里的真实参数值读回来打印，一眼看出哪个没生效
            try:
                _ids = ["formchange", "bath_taol_ON", "buraONFOFF", "pantsuONFOFF",
                        "negligeeONOFF", "negligeeinnerONOFF", "mizugiONOFF", "minzokucloth",
                        "bunny", "FudeONOFF"]
                _js = ("(function(){var m=window.romashaModel;if(!m)return 'no-model';"
                       "var cm=m.internalModel.coreModel;var o={};var ids=%s;"
                       "for(var i=0;i<ids.length;i++){try{o[ids[i]]=cm.getParameterValueById(ids[i]);}"
                       "catch(e){o[ids[i]]='ERR';}}return JSON.stringify(o);})()"
                       % str(_ids).replace("'", '"'))
                self.browser.page().runJavaScript(
                    _js, lambda r: print("\U0001F50D [换装诊断] %s -> 模型实参 %s" % (name, r), flush=True))
            except Exception:
                pass
            # 【三层独立】最后再叠一遍配饰：BASE_STATE 会清掉它们，
            # 整份快照还原也可能带回旧值，所以放在最后 = 配饰永远生效 ✓
            self.apply_accessories()
            # 【换装展示】换好衣服后让她先摆个姿势，2.4 秒后再转个圈。
            # 这是个"动作串接"的组合技：两个动作按顺序播，不会互相打断。
            # 一丝不挂时不适合摆姿势，改成害羞地缩一下。
            try:
                import json as _j
                if name == "nude":
                    self.browser.page().runJavaScript(
                        "window.playMotionByName(%s);" % _j.dumps("wait_haji"))
                else:
                    self.browser.page().runJavaScript(
                        "window.playMotionByName(%s);" % _j.dumps("poster"))
                    QTimer.singleShot(2400, lambda: self.browser.page().runJavaScript(
                        "window.playMotionByName('guruguru');"))
                    print("\U0001F457 [换装]: 让她展示一下新衣服（poster -> guruguru）", flush=True)
            except Exception:
                pass
            if react:
                self.on_outfit_changed(name)
        except Exception as e:
            print("⚠️ [换装]: 失败 %s" % e)

    OUTFIT_LABELS = {"uniform_tight": "紧身制服", "uniform_dress": "制服裙", "sleepwear": "睡衣",
                     "swimsuit": "泳装", "ethnic_wear": "民族服", "ethnic_cloak": "民族服·披风",
                     "towel": "浴巾", "bunny": "兔女郎", "nude": "一丝不挂"}

    OUTFIT_REACT_LINES = {
        "nude": "「……！？」她下意识用手臂挡在身前，耳根一下红透：「你、你就这样把我剥光了……也不先说一声。」",
        "swimsuit": "「这套……是不是太露了一点。」她拉了拉肩带，不太敢看你。",
        "bunny": "「兔、兔女郎？！皓皓你——」她抓着衣摆，又羞又恼地瞪你。",
        "towel": "「只有一条浴巾……」她裹紧了些，声音闷闷的。",
        "sleepwear": "「……睡衣倒是挺舒服的。」她小声嘟囔，耳朵尖有点红。",
        "ethnic_wear": "「花纹很漂亮，谢谢。」她低头摸了摸衣角。",
        "ethnic_cloak": "「披风有点重……不过，很暖。」",
        "uniform_tight": "「又换回这套了？」她理了理衣领。",
        "uniform_dress": "「裙子啊……你很喜欢看我穿这个吧。」",
    }

    def on_outfit_changed(self, name):
        import json as _json
        label = self.OUTFIT_LABELS.get(name, name)
        line = self.OUTFIT_REACT_LINES.get(name)
        if line:
            safe = line.replace("'", "\\'")
            self.browser.page().runJavaScript(
                "window.showBubble('<span style=\"color:#ffc0d0;\">%s</span>', true);" % safe)
        motion = "wait_haji" if name in ("nude", "swimsuit", "bunny", "towel") else "smallsmile"
        self.browser.page().runJavaScript("window.playMotionByName(%s);" % _json.dumps(motion))
        print("👗 [换装]: 已触发她的即时反应（%s / 动作 %s）" % (label, motion))
        self.start_new_thought("*你亲手让她换上了「%s」，她此刻的样子就在你眼前*" % label)

    def outfit_context_note(self):
        state = outfit_manager.export_state()
        cur = state.get("outfit") or llm_brain.config.get("saved_outfit", "")
        if cur == "nude":
            return "（她此刻一丝不挂，身上什么都没有）"
        if cur == "towel":
            return "（她此刻只裹着一条浴巾）"
        if cur in ("swimsuit", "bunny"):
            return "（她此刻穿着%s，大片肌肤裸露在外）" % self.OUTFIT_LABELS.get(cur, cur)
        return "（她此刻穿着%s）" % self.OUTFIT_LABELS.get(cur, cur)

    def apply_hair(self, name):
        if name not in outfit_manager.HAIRSTYLES:
            print("⚠️ [换装]: 未知的发型 -> %s" % name)
            return
        # 【发型权威】把所有"标准状态"快照里的发型一起更新。
        # 否则 apply_outfit 里那次"整份还原"会把发型退回旧的
        # （症状：选了丸子头没反应、一直保持披发）。
        try:
            _hv = outfit_manager.HAIRSTYLES.get(name)
            _snaps = getattr(self, "_outfit_snapshots", None) or {}
            for _o, _d in _snaps.items():
                if isinstance(_d, dict):
                    _d["hearchange"] = _hv
            llm_brain.config["saved_hair"] = name
            llm_brain.save_config()
            self._hair_authority = name
            self._hair_force = True
            print("\U0001F487 [\u53d1\u578b]: \u5df2\u628a\u300c%s\u300d\u5199\u5165\u6240\u6709\u5feb\u7167\uff08%d \u5957\uff09" % (name, len(_snaps)), flush=True)
        except Exception as _e:
            print("[\u53d1\u578b] \u66f4\u65b0\u5feb\u7167\u5931\u8d25: %s" % _e, flush=True)
        cur = outfit_manager.export_state().get("outfit") or llm_brain.config.get("saved_outfit", "")
        if cur not in outfit_manager.OUTFITS:
            cur = "uniform_tight"
        self.apply_outfit(cur, name)

    def reset_live2d_pose(self):
        try:
            llm_brain.config["scale"] = 0.5
            llm_brain.config["pos_x"] = -1.0
            llm_brain.config["pos_y"] = 100.0
            llm_brain.save_config()
            js = "window.applySavedState(0.5, -1, 100, %s, %s);" % (
                "true" if getattr(self, "is_tracking_enabled", True) else "false",
                "true" if getattr(self, "is_touch_enabled", True) else "false")
            self.browser.page().runJavaScript(js)
            print("🧍 [立绘]: 已复位为 0.5 倍、水平居中、距顶 100px。")
        except Exception as e:
            print("⚠️ [立绘]: 复位失败 %s" % e)

    def check_model_ready(self):
        import json as _json
        js = "JSON.stringify({m:!!window.romashaModel,u:window.currentModelUrl||''})"

        def _cb(res):
            try:
                data = _json.loads(res) if res else {}
            except Exception:
                data = {}
            if data.get("m"):
                cur = (data.get("u") or "").strip()
                print("🧍 [动态场景]: 当前模型已就绪 -> %s" % (cur or "默认"))
                if cur and cur != "model/romasha_talk.model3.json":
                    fit = ("(function(){var m=window.romashaModel;if(!m)return 'no';"
                           "var ox=m.scale.x||1;var w=m.width/ox,h=m.height/ox;if(!w||!h)return 'bad';"
                           "var s=Math.min(window.innerWidth*0.92/w,window.innerHeight*0.92/h);"
                           "m.scale.set(s);"
                           "m.x=window.innerWidth/2-m.width/2;"
                           "m.y=window.innerHeight/2-m.height/2;"
                           "return s.toFixed(3);})()")
                    self.browser.page().runJavaScript(
                        fit, lambda r: print("🧍 [动态场景]: 已自动适配屏幕（缩放 %s）" % r))
                return
            cur = (data.get("u") or "").strip()
            if cur and cur != "model/romasha_talk.model3.json":
                print("⚠️ [动态场景]: %s 没能加载，已自动回到日常立绘。" % cur)
                self.switch_live2d_model("model/romasha_talk.model3.json")

        self.browser.page().runJavaScript(js, _cb)

    def push_relationship_stats(self):
        import json as _json
        try:
            rel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_data", "relationship_state.json")
            with open(rel_path, "r", encoding="utf-8") as f:
                rel = _json.load(f)
        except Exception:
            rel = {}

        cfg = llm_brain.config
        stage_map = {
            "stranger": "陌生人", "acquaintance": "点头之交", "friend": "朋友",
            "close_friend": "挚友", "lover": "恋人", "married": "已婚",
        }
        raw_stage = rel.get("current_relationship_stage", "stranger")
        stage = stage_map.get(raw_stage, raw_stage)

        def num(v, d=0):
            try:
                return int(v)
            except Exception:
                return d

        intimacy = num(cfg.get("intimacy", 0))
        touch_zones = rel.get("accepted_touch_zones", [])
        if not isinstance(touch_zones, list):
            touch_zones = []
        phys = num(rel.get("physical_intimacy_stage", 0))

        rows = [
            {"k": "关系阶段", "v": stage, "pct": None},
            {"k": "亲密度", "v": str(intimacy), "pct": intimacy},
            {"k": "信任", "v": str(num(rel.get("trust", 0))), "pct": num(rel.get("trust", 0))},
            {"k": "依恋", "v": str(num(rel.get("attachment", 0))), "pct": num(rel.get("attachment", 0))},
            {"k": "害羞度", "v": str(num(rel.get("shyness", 0))), "pct": num(rel.get("shyness", 0))},
            {"k": "边界软化", "v": str(num(rel.get("boundary_softness", 0))), "pct": num(rel.get("boundary_softness", 0))},
            {"k": "身体亲密阶段", "v": "%d / 5" % phys, "pct": phys / 5.0 * 100.0},
            {"k": "可接触部位", "v": "%d / 9" % len(touch_zones), "pct": len(touch_zones) / 9.0 * 100.0},
            {"k": "当前心情", "v": str(rel.get("current_attitude", "normal")), "pct": None},
            {"k": "章节", "v": "第 %s 章" % cfg.get("current_chapter", 1), "pct": None},
            {"k": "所在位置", "v": str(cfg.get("current_location", "?")), "pct": None},
            {"k": "她对你的称呼", "v": (cfg.get("player_name") or "（未设定）"), "pct": None},
        ]
        try:
            js = "window.updateStats(" + _json.dumps({"rows": rows}, ensure_ascii=False) + ");"
            self.browser.page().runJavaScript(js)
        except Exception as e:
            print("推送关系数据失败: %s" % e)

    def push_memory_list(self):
        import json as _json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_data", "memory_data.json")
        if not os.path.isfile(path):
            print("⚠️ [回想房]: 缺少 world_data/memory_data.json（先运行 make_memory_data.py）")
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = _json.load(f)
        except Exception as e:
            print("⚠️ [回想房]: 读取失败 %s" % e)
            return

        def _esc(s):
            return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def _br(s):
            return _esc(s).replace("\r\n", "<br>").replace("\n", "<br>")

        items = []
        scene_by_memory = {}
        try:
            for sid in scene_player.list_scenes():
                scene = scene_player.load_scene(sid)
                no = (scene.get("source") or {}).get("memory_no") if scene else None
                if no is not None and no not in scene_by_memory:
                    scene_by_memory[no] = sid
        except Exception:
            pass
        # The desktop companion only exposes the first 195 story memories.
        # The original game data remains untouched on disk.
        for e in data:
            try:
                if int(e.get("no", 0)) >= 196:
                    continue
            except Exception:
                pass
            parts = ['<div class="cap-t">%s. %s</div>' % (
                e.get("no", "?"), _esc(e.get("title")) or "（原作未记录）")]
            if e.get("desc"):
                parts.append('<div class="cap-d">%s</div>' % _br(e.get("desc")))
            if e.get("hint"):
                parts.append('<div class="cap-h">%s</div>' % _esc(e.get("hint")))
            for p in e.get("patterns") or []:
                if p.get("name"):
                    parts.append('<div class="cap-h">【%s】</div>' % _esc(p.get("name")))
                if p.get("text"):
                    parts.append('<div class="cap-p">%s</div>' % _br(p.get("text")))
            scn = e.get("scenes") or []
            if scn:
                def _is_h(_m):
                    return str(L2D_SCENE_LABELS.get(_m, "")).startswith("♥")
                ordered = [m for m in scn if _is_h(m)] + [m for m in scn if not _is_h(m)]
                btns = "".join(
                    '<span class="scn" data-url="model_alt/%s/%s.model3.json" data-name="%s">&#9654; %s</span>'
                    % (m, m, m, L2D_SCENE_LABELS.get(m, m)) for m in ordered[:10])
                parts.append('<div class="cap-scn">该回想的原始 Live2D 场景（★ 为色色场景，点击播放）：%s</div>' % btns)
            items.append({
                "name": "%s. %s" % (e.get("no", "?"), e.get("title") or "???"),
                "url": "original/pictures/" + e.get("img", ""),
                "thumb": "original/thumbs/" + e.get("thumb", ""),
                "note": "".join(parts),
                "memory_no": int(e.get("no", 0) or 0),
                "memory_text": [
                    {"name": p.get("name", ""), "text": p.get("text", "")}
                    for p in (e.get("patterns") or [])
                ],
                "scene_names": scn,
                "scene_id": scene_by_memory.get(int(e.get("no", 0) or 0)),
            })
        # Append the 32 playable Live2D special scenes to the same 回想 view.
        h_path = os.path.join(os.path.dirname(path), "h_scenes.json")
        try:
            with open(h_path, encoding="utf-8") as f:
                for s in _json.load(f):
                    model = str(s.get("model") or "")
                    if not model:
                        continue
                    items.append({
                        "name": "特殊场景 · " + str(s.get("label") or s.get("id") or model),
                        "url": "model_alt/%s/%s.model3.json" % (model, model),
                        "thumb": "original/thumbs/" + str(s.get("thumb") or ""),
                        "note": "特殊 Live2D 场景，点击播放。",
                        "scene_id": str(s.get("id") or ""),
                        "timeline": s.get("timeline") or [],
                        "voices": [
                            "original/voice/h/%s/%s.ogg" % (v[0], v[1])
                            for v in (s.get("voices") or []) if len(v) >= 2
                        ],
                    })
        except Exception as e:
            print("⚠️ [回想房]: 特殊场景读取失败 %s" % e)
        self.browser.page().runJavaScript(
            "window.setGalleryList(" + _json.dumps(items, ensure_ascii=False) + ");")
        print("📖 [回想房]: 已推送 %d 个原作回想条目（含中文台词，图/缩略图齐全）" % len(items))

    def push_gallery_manifest(self):
        import json as _json
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        base = os.path.join(web_dir, "original", "pictures")
        # 只收真正的内容图：根目录的事件 CG / 背景  +  回想图库(MImage)。
        # 排除：卡牌(UI_Card)、特效(CEffect)、战斗头像(Btl_Face)、存档界面(Save)、
        # 地牢/菜单等所有 UI 素材，以及地图光照层(!map_*) 和纯色/工具图。
        cg_dirs = {"MImage"}
        skip_prefix = ("!map_", "pn_", "card_", "ui_", "$", "!")
        skip_stems = {
            "acstart", "black", "black2", "white", "brown", "pink", "red",
            "e_black", "database", "longdatabase", "warning", "setup",
            "talk_back", "talkauto", "l2dloading", "live2d_checker",
            "live2d_checker_btn", "twin1a", "twin1b", "video_flame",
            "warphole", "ptcpoint", "map_kurai", "rd_event", "cutinback",
            "happyend-fin", "peepingflame", "hscene_beetle",
        }
        items = []
        try:
            for root, dirs, files in os.walk(base):
                rel_dir = os.path.relpath(root, base)
                if rel_dir == ".":
                    keep = True
                    cat = ""
                else:
                    segs = rel_dir.split(os.sep)
                    keep = any(s in cg_dirs for s in segs)
                    cat = segs[-1]
                if not keep:
                    continue
                for name in files:
                    low = name.lower()
                    if not low.endswith(".png"):
                        continue
                    if low.startswith(skip_prefix):
                        continue
                    if os.path.splitext(low)[0] in skip_stems:
                        continue
                    full = os.path.join(root, name)
                    rel_in_pic = os.path.relpath(full, base).replace("\\", "/")
                    url = "original/pictures/" + rel_in_pic
                    thumb = "original/thumbs/" + os.path.splitext(rel_in_pic)[0] + ".jpg"
                    if not os.path.isfile(os.path.join(web_dir, thumb.replace("/", os.sep))):
                        thumb = url
                    stem = os.path.splitext(name)[0]
                    items.append({
                        "name": stem if cat == "" else (cat + "·" + stem),
                        "url": url,
                        "thumb": thumb,
                        "cat": cat,
                    })
        except Exception as e:
            print("扫描原作素材失败: %s" % e)
        items.sort(key=lambda x: (0 if x["cat"] == "" else 1, x["cat"], x["name"]))
        try:
            thumbed = sum(1 for it in items if it.get("thumb") != it.get("url"))
            js = "window.setGalleryList(" + _json.dumps(items, ensure_ascii=False) + ");"
            self.browser.page().runJavaScript(js)
            print("🎨 [画册]: 已推送 %d 张原作图片（其中 %d 张走缩略图）。" % (len(items), thumbed))
        except Exception as e:
            print("推送画册失败: %s" % e)

    # ================================================================
    # 逐像素 alpha 命中测试
    # 网页把她"真正画出来的像素"栅格化成 1bit/格 的位图送过来；
    # 这里在 WM_NCHITTEST 里查这张位图：只有真有像素的地方才 HTCLIENT，
    # 其余一律 HTTRANSPARENT（Windows 会把这一次鼠标事件直接交给下面的
    # 窗口/桌面）。于是"能点到的地方"精确等于"看得见的地方"。
    # 兜底：位图还没送到时，退回包围盒正中 50% 宽的竖带 ——
    # 这样至少她还抓得住，且不会有整块包围盒挡住桌面。
    # ================================================================
    # ================================================================
    # 【游戏模式 / 休眠】
    # 用 Windows 自带的 SHQueryUserNotificationState() —— 系统就是靠它决定
    # "全屏游戏时不要弹通知"。返回 QUNS_BUSY(2, 全屏演示/无边框全屏) 或
    # QUNS_RUNNING_D3D_FULL_SCREEN(3, D3D 独占全屏) 就认定"正在玩游戏"。
    # 休眠时：窗口遮罩设为【空区域】(她在窗口系统里完全不存在 -> 不吃点击、
    # 不参与合成，对游戏零干扰、占用最低)，网页降到 4fps 并停掉位图与鼠标追踪。
    # 游戏结束后自动恢复。
    # ================================================================
    # =================================================================
    # 【AI 设置窗口】独立窗口、屏幕居中 —— 不放在她那个小窗口里
    # （放在她窗口里会被裁、又小又难点，用户反馈过）
    # =================================================================
    # =================================================================
    # 【设置窗口】标签页式：AI 对话 / 语音 / 启动与行为 / 关于
    #   开机自启用注册表 HKCU\...\Run（不需要管理员，随时可关）。
    # =================================================================
    _AUTOSTART_NAME = "RomashaLive2D"

    def _autostart_cmd(self):
        import sys as _sys
        base = os.path.dirname(os.path.abspath(__file__))
        exe = os.path.join(base, "venv", "Scripts", "pythonw.exe")
        if not os.path.isfile(exe):
            exe = _sys.executable
        return '"%s" "%s"' % (exe, os.path.join(base, "main.py"))

    def _autostart_get(self):
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Run",
                               0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(k, self._AUTOSTART_NAME)
                return True
            finally:
                winreg.CloseKey(k)
        except Exception:
            return False

    def _autostart_set(self, on):
        """开/关开机自启；返回 True 表示操作成功。"""
        try:
            import winreg
            k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_SET_VALUE)
            try:
                if on:
                    winreg.SetValueEx(k, self._AUTOSTART_NAME, 0, winreg.REG_SZ, self._autostart_cmd())
                    print("\U0001F680 [\u8bbe\u7f6e]: \u5df2\u5f00\u542f\u5f00\u673a\u81ea\u542f", flush=True)
                else:
                    try:
                        winreg.DeleteValue(k, self._AUTOSTART_NAME)
                    except FileNotFoundError:
                        pass
                    print("\U0001F6D1 [\u8bbe\u7f6e]: \u5df2\u5173\u95ed\u5f00\u673a\u81ea\u542f", flush=True)
            finally:
                winreg.CloseKey(k)
            return True
        except Exception as e:
            print("[\u8bbe\u7f6e] \u5f00\u673a\u81ea\u542f\u8bbe\u7f6e\u5931\u8d25: %s" % e, flush=True)
            return False

    def open_action_manual(self):
        """行动手册：把所有能做的事列清楚（♥ 面板 -> 行动手册）。"""
        from PyQt5.QtWidgets import (QWidget as _W, QVBoxLayout as _VB,
                                     QTextBrowser as _TB, QPushButton as _PB)
        try:
            w = getattr(self, "_help_dlg", None)
            if w is None:
                w = _W()
                w.setWindowTitle("行动手册 - Romasha")
                w.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
                w.resize(620, 660)
                lay = _VB(w)
                tb = _TB()
                tb.setOpenExternalLinks(False)
                tb.setStyleSheet("QTextBrowser{background:#241821;color:#ffe6ee;"
                                 "border:2px solid #ffb6c1;border-radius:10px;padding:12px;"
                                 "font-family:'Microsoft YaHei';font-size:13px;}")
                tb.setHtml("""
                <style>
                  h2{color:#ffc8d8;font-size:16px;margin:12px 0 6px;}
                  table{border-collapse:collapse;width:100%;}
                  td{padding:5px 8px;border-bottom:1px solid rgba(255,182,193,0.18);vertical-align:top;}
                  td.k{color:#ffd9e2;font-weight:700;white-space:nowrap;width:34%;}
                  .tip{color:#c9a;font-size:12px;}
                </style>
                <h2>🐾 怎么跟她互动</h2>
                <table>
                  <tr><td class="k">单击她的头 / 身体</td><td>不同部位有不同反应（头部会更害羞）</td></tr>
                  <tr><td class="k">连点 3 次以上</td><td>她会烦：扭头、小声抱怨</td></tr>
                  <tr><td class="k">长按不放（约 1 秒）</td><td>她低头看设备</td></tr>
                  <tr><td class="k">双击</td><td>小小得意一下</td></tr>
                  <tr><td class="k">滚轮</td><td>缩放她的立绘（有冷却）</td></tr>
                  <tr><td class="k">拖动她</td><td>移动位置；<b>松手后播放当前这身衣服的"掉落/反应"动作</b></td></tr>
                </table>

                <h2>👗 换装与掉落</h2>
                <table>
                  <tr><td class="k">♥ → 换装</td><td>9 套衣服（制服 / 睡衣 / 泳装 / 民族服 / 浴巾 / 兔女郎 …）</td></tr>
                  <tr><td class="k">拖她（穿浴巾时）</td><td>浴巾掉落（保持脱下的样子）</td></tr>
                  <tr><td class="k">连摸敏感部位 5 次</td><td>害羞 → 色气 → 兴奋 → 撩 → <b>浴巾状态才会真正滑落</b>；20 秒后自己穿回</td></tr>
                  <tr><td class="k">每套衣服的动作</td><td>浴巾=taol_fall / 睡衣=裙摆 / 泳装·制服=裙摆 / 民族服 / 兔女郎 各不相同</td></tr>
                  <tr><td class="k">切回任何一套</td><td>一键穿回（按标准状态整份还原，不会卡住）</td></tr>
                </table>

                <h2>❤️ 爱心面板（点她旁边的小爱心）</h2>
                <table>
                  <tr><td class="k">换装</td><td>选衣服 / 发型</td></tr>
                  <tr><td class="k">立绘复原</td><td>把她放回屏幕中央的正确大小</td></tr>
                  <tr><td class="k">回想</td><td><b>打开独立的场景查看器</b>（292 个原作回想）</td></tr>
                  <tr><td class="k">游戏模式</td><td>检测到你列表里的游戏在跑 → 她自己休眠/隐藏；退出游戏自动恢复</td></tr>
                  <tr><td class="k">休眠方式</td><td>游戏模式时是隐藏还是保持可见</td></tr>
                  <tr><td class="k">AI 设置</td><td>接口地址 / API Key / 模型名 / 语音服务</td></tr>
                  <tr><td class="k">行动手册</td><td>就是这一页</td></tr>
                </table>

                <h2>🎬 场景查看器（回想）</h2>
                <table>
                  <tr><td class="k">点左边列表</td><td>立刻播放该场景（动作 + 台词 + 音效）</td></tr>
                  <tr><td class="k">点画面</td><td>推进到下一句（galgame 手感）</td></tr>
                  <tr><td class="k">下一句 ▶</td><td>同上</td></tr>
                  <tr><td class="k">⏭ 跳到动作</td><td><b>跳过中间的台词堆，直接到下一个动画</b>（有些场景第一个动作在第 1300 步之后）</td></tr>
                  <tr><td class="k">◀ 上一个 / 下一个 ▶</td><td>在列表里换场景</td></tr>
                  <tr><td class="k">■ 停止</td><td>收回场景模型</td></tr>
                  <tr><td class="k">搜索框</td><td>按场景号（CE1336）/ 标题 / 模型名搜索</td></tr>
                  <tr><td class="k">Esc</td><td>关闭场景</td></tr>
                </table>

                <h2>🔊 如果没声音</h2>
                <table>
                  <tr><td class="k">查看器要用 python.exe</td><td>双击 <b>打开场景查看器.bat</b>（已配好）；用 pythonw 启动会被系统的独立音频会话静音</td></tr>
                  <tr><td class="k">音量合成器</td><td>右键小喇叭 → 打开音量合成器 → 看 python / QtWebEngineProcess 是否被静音</td></tr>
                </table>

                <h2>🕐 她会自己做的事</h2>
                <table>
                  <tr><td class="k">闲置一会儿</td><td>随机待机动作（发呆 / 微笑 / 无聊）</td></tr>
                  <tr><td class="k">22:00 - 06:00</td><td>微醺 / 困倦的语气与动作</td></tr>
                  <tr><td class="k">关系值提升</td><td>称谓、语气、主动程度会变化</td></tr>
                </table>
                <p class="tip">右击任务栏托盘图标 → 退出 Romasha，才能完全关闭她。</p>
                """)
                lay.addWidget(tb)
                brow = _PB("关闭")
                brow.clicked.connect(w.hide)
                lay.addWidget(brow)
                self._help_dlg = w
            w.adjustSize()
            try:
                g = QApplication.primaryScreen().availableGeometry()
                w.move(g.center().x() - w.width() // 2, g.center().y() - w.height() // 2)
            except Exception:
                pass
            w.show(); w.raise_(); w.activateWindow()
            print("\U0001F4D8 [\u624b\u518c]: \u5df2\u6253\u5f00\u884c\u52a8\u624b\u518c", flush=True)
        except Exception as e:
            print("[\u624b\u518c] \u6253\u5f00\u5931\u8d25: %s" % e, flush=True)

    def open_ai_settings(self):
        from PyQt5.QtWidgets import (QWidget as _W, QTabWidget as _TW, QFormLayout as _FL,
                                     QLineEdit as _LE, QPushButton as _PB, QHBoxLayout as _HB,
                                     QVBoxLayout as _VB, QLabel as _LB, QCheckBox as _CB,
                                     QSpinBox as _SB, QComboBox as _CBX, QGroupBox as _GB)
        try:
            d = getattr(self, "_set_dlg", None)
            if d is None:
                d = _W(self)
                d.setWindowTitle("Romasha 设置")
                d.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
                d.setStyleSheet("""
                    QWidget { background: #2a1c26; color: #ffe6ee;
                              font-family: 'Microsoft YaHei'; font-size: 13px; }
                    QTabWidget::pane { border: 1px solid #ffb6c1; border-radius: 8px; top: -1px; }
                    QTabBar::tab { background: #3a2733; color: #ffd9e2; padding: 6px 14px;
                                   border-top-left-radius: 7px; border-top-right-radius: 7px; margin-right: 2px; }
                    QTabBar::tab:selected { background: #ffb6c1; color: #3a2230; font-weight: 700; }
                    QGroupBox { border: 1px solid rgba(255,182,193,0.45); border-radius: 8px;
                                margin-top: 10px; padding: 10px 8px 6px; }
                    QGroupBox::title { color: #ffb3c8; subcontrol-origin: margin; left: 10px; padding: 0 4px; }
                    QLabel { color: #ffd9e2; }
                    QLineEdit, QSpinBox, QComboBox { background: #1b1219; border: 1px solid #ffb6c1;
                                border-radius: 6px; padding: 5px 7px; color: #ffe6ee; min-width: 300px; }
                    QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #ff9db5; }
                    QCheckBox { color: #ffe6ee; padding: 3px 0; }
                    QPushButton { background: #ffb6c1; color: #3a2230; border: none;
                                  border-radius: 7px; padding: 7px 22px; font-weight: 700; }
                    QPushButton:hover { background: #ffd9e2; }
                    QPushButton#ghost { background: rgba(255,182,193,0.18); color: #ffd9e2; }
                """)
                root = _VB(d)
                tabs = _TW()
                d._f = {}

                # ---------- Tab 1: AI 对话 ----------
                t1 = _W(); f1 = _FL(t1)
                for _k, _lab, _ph in (("api_type", "接口类型", "openai / anthropic / gemini / ollama"),
                                      ("base_url", "接口地址", "https://api.example.com/v1"),
                                      ("api_key", "API Key", "sk-..."),
                                      ("target_model", "模型名", "deepseek-chat")):
                    e = _LE(str(llm_brain.config.get(_k, "") or ""))
                    e.setPlaceholderText(_ph)
                    if _k == "api_key":
                        e.setEchoMode(_LE.Password)
                    d._f[_k] = e
                    f1.addRow(_LB(_lab), e)
                f1.addRow(_LB(""), _LB("提示：接口地址/Key 改完需重开程序才生效"))

                # ---------- Tab 2: 语音 ----------
                t2 = _W(); f2 = _FL(t2)
                d._cb_voice = _CB("启用语音")
                d._cb_voice.setChecked(bool(llm_brain.config.get("voice_enabled", False)))
                f2.addRow(_LB(""), d._cb_voice)
                for _k, _lab, _ph in (("sovits_url", "GPT-SoVITS 地址", "http://127.0.0.1:9880/"),
                                      ("cosy_url", "CosyVoice 地址", "http://127.0.0.1:9880/api/tts")):
                    e = _LE(str(llm_brain.config.get(_k, "") or ""))
                    e.setPlaceholderText(_ph)
                    d._f[_k] = e
                    f2.addRow(_LB(_lab), e)
                _eng = _CBX(); _eng.addItems(["sovits", "cosyvoice"])
                try:
                    _eng.setCurrentText(str(llm_brain.config.get("tts_engine", "sovits")))
                except Exception:
                    pass
                d._cbx_engine = _eng
                f2.addRow(_LB("语音引擎"), _eng)

                # ---------- Tab 3: 启动与行为 ----------
                t3 = _W(); v3 = _VB(t3)
                g1 = _GB("启动"); fg = _FL(g1)
                d._cb_auto = _CB("开机自动启动（随 Windows 启动）")
                d._cb_auto.setChecked(self._autostart_get())
                fg.addRow(_LB(""), d._cb_auto)
                v3.addWidget(g1)
                g2 = _GB("行为"); fg2 = _FL(g2)
                d._cb_touch = _CB("允许触摸互动")
                d._cb_touch.setChecked(bool(llm_brain.config.get("touch_enabled", True)))
                d._cb_track = _CB("眼睛跟随鼠标")
                d._cb_track.setChecked(bool(llm_brain.config.get("track_enabled", True)))
                fg2.addRow(_LB(""), d._cb_touch)
                fg2.addRow(_LB(""), d._cb_track)
                d._sp_fps = _SB(); d._sp_fps.setRange(10, 60)
                try:
                    d._sp_fps.setValue(int(llm_brain.config.get("pet_fps", 30)))
                except Exception:
                    d._sp_fps.setValue(30)
                fg2.addRow(_LB("帧率 (FPS)"), d._sp_fps)
                d._sp_bub = _SB(); d._sp_bub.setRange(60, 200)
                try:
                    d._sp_bub.setValue(int(llm_brain.config.get("bubble_size", 100)))
                except Exception:
                    d._sp_bub.setValue(100)
                fg2.addRow(_LB("气泡大小 (%)"), d._sp_bub)
                v3.addWidget(g2)
                _drop = _CBX()
                _drop.addItem("（关闭掉落）", "")
                for _o in sorted(getattr(outfit_manager, "OUTFITS", {}).keys()):
                    _drop.addItem(_o, _o)
                _want = str(llm_brain.config.get("strip_outfit", "towel") or "")
                _ix = _drop.findData(_want)
                _drop.setCurrentIndex(_ix if _ix >= 0 else 0)
                d._cbx_strip = _drop
                g3 = _GB("掉落"); fg3 = _FL(g3)
                fg3.addRow(_LB("可掉落的衣服"), _drop)
                v3.addWidget(g3)
                v3.addStretch(1)

                # ---------- Tab 4: 关于 ----------
                t4 = _W(); f4 = _FL(t4)
                _base = os.path.dirname(os.path.abspath(__file__))
                f4.addRow(_LB("程序目录"), _LB(_base))
                f4.addRow(_LB("配置文件"), _LB(os.path.join(_base, "config.json")))
                f4.addRow(_LB("说明"), _LB("设置保存后写入 config.json；\n部分项（接口地址/帧率）需重开程序生效。"))

                tabs.addTab(t1, "AI 对话")
                tabs.addTab(t2, "语音")
                tabs.addTab(t3, "启动与行为")
                tabs.addTab(t4, "关于")
                root.addWidget(tabs)

                row = _HB()
                b_save = _PB("保存")
                b_close = _PB("关闭"); b_close.setObjectName("ghost")
                b_open_ini = _PB("打开配置文件"); b_open_ini.setObjectName("ghost")
                b_open_ini.clicked.connect(lambda: os.startfile(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "config.json")))

                def _do_save():
                    try:
                        _ch = []
                        for _k, _w in d._f.items():
                            _v = _w.text().strip()
                            if llm_brain.config.get(_k) != _v:
                                llm_brain.config[_k] = _v
                                _ch.append(_k)
                        for _k, _w in (("voice_enabled", d._cb_voice),
                                       ("touch_enabled", d._cb_touch),
                                       ("track_enabled", d._cb_track)):
                            _v = bool(_w.isChecked())
                            if bool(llm_brain.config.get(_k, None)) != _v:
                                llm_brain.config[_k] = _v
                                _ch.append(_k)
                        for _k, _w in (("pet_fps", d._sp_fps), ("bubble_size", d._sp_bub)):
                            _v = int(_w.value())
                            if llm_brain.config.get(_k) != _v:
                                llm_brain.config[_k] = _v
                                _ch.append(_k)
                        _v = str(d._cbx_engine.currentText())
                        if llm_brain.config.get("tts_engine") != _v:
                            llm_brain.config["tts_engine"] = _v
                            _ch.append("tts_engine")
                        _v = str(d._cbx_strip.currentData() or "")
                        if str(llm_brain.config.get("strip_outfit", "")) != _v:
                            llm_brain.config["strip_outfit"] = _v
                            _ch.append("strip_outfit")
                        # 开机自启（注册表，立即生效）
                        _want_auto = bool(d._cb_auto.isChecked())
                        if _want_auto != self._autostart_get():
                            if self._autostart_set(_want_auto):
                                _ch.append("\u5f00\u673a\u81ea\u542f" if _want_auto else "\u5f00\u673a\u81ea\u542f(\u5173)")
                        llm_brain.save_config()
                        try:
                            _m = d._f["target_model"].text().strip()
                            if _m:
                                llm_brain.TARGET_MODEL = _m
                        except Exception:
                            pass
                        d.setWindowTitle("Romasha \u8bbe\u7f6e - \u5df2\u4fdd\u5b58 \u2713")
                        print("\u2699\ufe0f [\u8bbe\u7f6e]: \u5df2\u4fdd\u5b58\uff08%s\uff09"
                              % (", ".join(_ch) or "\u65e0\u53d8\u5316"), flush=True)
                    except Exception as _e:
                        print("[\u8bbe\u7f6e] \u4fdd\u5b58\u5931\u8d25: %s" % _e, flush=True)

                b_save.clicked.connect(_do_save)
                b_close.clicked.connect(d.hide)
                row.addWidget(b_open_ini)
                row.addStretch(1)
                row.addWidget(b_save)
                row.addWidget(b_close)
                root.addLayout(row)
                self._set_dlg = d
            d.adjustSize()
            try:
                _g = QApplication.primaryScreen().availableGeometry()
                d.move(_g.center().x() - d.width() // 2, _g.center().y() - d.height() // 2)
            except Exception:
                pass
            d.show(); d.raise_(); d.activateWindow()
            print("\u2699\ufe0f [\u8bbe\u7f6e]: \u5df2\u6253\u5f00\u8bbe\u7f6e\u7a97\u53e3\uff08\u5c4f\u5e55\u5c45\u4e2d\uff09", flush=True)
        except Exception as _e:
            print("[\u8bbe\u7f6e] \u6253\u5f00\u7a97\u53e3\u5931\u8d25: %s" % _e, flush=True)

    def _fg_exe(self):
        """当前【前台窗口】所属进程的可执行文件名（小写）；失败返回空串。"""
        try:
            import ctypes, ctypes.wintypes as _wt
            u = ctypes.windll.user32
            hwnd = u.GetForegroundWindow()
            if not hwnd:
                return ""
            pid = _wt.DWORD(0)
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return ""
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid.value)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ""
            try:
                buf = ctypes.create_unicode_buffer(1024)
                size = _wt.DWORD(1024)
                if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    return os.path.basename(buf.value).lower()
            finally:
                k.CloseHandle(h)
        except Exception:
            pass
        return ""

    def _push_gm_ui(self):
        try:
            armed = bool(llm_brain.config.get("game_mode_enabled", True))
            hide = bool(llm_brain.config.get("game_mode_hide", False))
            self.browser.page().runJavaScript(
                "window.setGameModeUI && window.setGameModeUI(%s);" % ("true" if armed else "false"))
            self.browser.page().runJavaScript(
                "window.setGmHideUI && window.setGmHideUI(%s);" % ("true" if hide else "false"))
        except Exception:
            pass

    # ================================================================
    # 【参数快照】掉落前把她的全部参数存一份，之后逐项原样还原。
    # 这是唯一"绝对不会还原错"的办法：不需要知道哪个参数管什么，
    # 只要把数值放回去，她就和掉落前一模一样。
    # ================================================================
    def _l2d_param_ids(self):
        if getattr(self, "_param_ids_cache", None):
            return self._param_ids_cache
        try:
            import json as _json
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "web", "model", "romasha_talk.cdi3.json")
            j = _json.load(io.open(p, encoding="utf-8"))
            ids = [(x.get("Id") or x.get("Name")) for x in (j.get("Parameters") or [])]
            self._param_ids_cache = [i for i in ids if i]
        except Exception:
            self._param_ids_cache = []
        return self._param_ids_cache

    # ================================================================
    # 【每套衣服的"标准状态"】
    # 问题：换走再换回来时，之前那套留下的、不在衣服参数表里的那些参数
    #       没有复位 -> 浴巾就穿不回去（变图1那种）。
    # 解法：第一次穿这套时把【全部参数】存下来当标准；以后每次穿这套，
    #       整份照标准还原 —— 也就是"把她穿回去"。
    # ================================================================
    def _outfit_snapshot_step(self, name):
        try:
            import json as _json
            ids = self._l2d_param_ids()
            if not name:
                return
            js = ("(function(){var m=window.romashaModel;if(!m)return 'NO_MODEL';"
                  "var cm=m.internalModel.coreModel;var ids=cm._parameterIds||[];"
                  "if(!ids.length)return 'NO_IDS';var o={};"
                  "for(var i=0;i<ids.length;i++){try{o[ids[i]]=cm.getParameterValueById(ids[i]);}catch(e){}}"
                  "return JSON.stringify(o);})()")

            def _cb(r):
                print("\U0001F4E5 [标准状态] 收到回传: %s" % str(r)[:120], flush=True)
                try:
                    d = _json.loads(r or "{}")
                    if not isinstance(d, dict) or not d:
                        print("[标准状态] 回传不是有效参数表，跳过", flush=True)
                        return
                    snaps = getattr(self, "_outfit_snapshots", None)
                    if snaps is None:
                        snaps = self._outfit_snapshots = {}
                    if name not in snaps:
                        snaps[name] = d
                        print("\U0001F4F8 [换装] 已记录「%s」的标准状态（%d 个参数）" % (name, len(d)), flush=True)
                except Exception as e:
                    print("[换装] 标准状态处理失败: %s" % e, flush=True)
            print("\U0001F4E4 [标准状态] 正在读取「%s」当前参数…" % name, flush=True)
            self.browser.page().runJavaScript(js, _cb)
        except Exception as e:
            print("[换装] 标准状态出错: %s" % e, flush=True)

    def _take_param_snapshot(self):
        try:
            import json as _json
            ids = self._l2d_param_ids()
            pass  # 参数名由 JS 自取，Python 不再需要
            js = ("(function(){var m=window.romashaModel;if(!m)return 'NO_MODEL';"
                  "var cm=m.internalModel.coreModel;var ids=cm._parameterIds||[];"
                  "if(!ids.length)return 'NO_IDS';var o={};"
                  "for(var i=0;i<ids.length;i++){try{o[ids[i]]=cm.getParameterValueById(ids[i]);}catch(e){}}"
                  "return JSON.stringify(o);})()")
            self.browser.page().runJavaScript(js, self._save_param_snapshot)
        except Exception:
            pass

    def _save_param_snapshot(self, r):
        try:
            import json as _json
            d = _json.loads(r or "{}")
            if d:
                self._param_snapshot = d
                print("\U0001F4F8 [快照] 已存下她 %d 个参数，掉落结束后原样还原。" % len(d), flush=True)
        except Exception:
            pass

    def _save_config_flag(self, key, value):
        """把某个开关写回 config.json（其它字段原样保留）。"""
        try:
            import json as _json
            cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            cfg = dict(llm_brain.config)
            cfg[key] = value
            with open(cp, "w", encoding="utf-8") as f:
                _json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[game-mode] save config failed: %s" % e, flush=True)

    def _game_mode_tick(self):
        # ① 白名单：前台窗口的进程名在 config 的 game_exe_list 里
        try:
            exes = [str(x).strip().lower() for x in (llm_brain.config.get("game_exe_list") or []) if str(x).strip()]
        except Exception:
            exes = []
        fg = self._fg_exe() if exes else ""
        hit = bool(fg) and (fg in exes)
        import time as _t
        if hit:
            self._last_game_seen = _t.time()
        # ② 只有"开关打开 + 检测到游戏在跑"才进入休眠。
        #    开开关本身不会让她有任何变化（这就是上次语义搞错的地方）。
        try:
            armed = bool(llm_brain.config.get("game_mode_enabled", True))
        except Exception:
            armed = True
        busy = bool(armed and hit)
        if hit:
            self._last_game_seen = _t.time()
        if busy != getattr(self, "_game_mode", False):
            self._game_mode = busy
            why = "手动" if manual else ("前台游戏 " + fg)
            self._apply_game_mode(busy, why)

    def _apply_game_mode(self, on, why=""):
        hide = bool(llm_brain.config.get("game_mode_hide", False))
        self._sleep = bool(on)          # nativeEvent 会据此把整窗设为"点击穿透"
        try:
            if on and hide:
                # 完全隐藏：她在窗口系统里不存在 -> 零干扰、占用最低
                self.setMask(QRegion(0, 0, 0, 0))
            elif not on:
                r = getattr(self, "_last_good_region", None)
                self.setMask(r if (r is not None and not r.isEmpty()) else QRegion(0, 0, 0, 0))
            # on 且"保持可见"：遮罩不动，靠 nativeEvent 全透传，她照样看得见
        except Exception:
            pass
        try:
            self.browser.page().runJavaScript(
                "window.setSleepMode && window.setSleepMode(%s, %s);"
                % ("true" if on else "false", "true" if hide else "false"))
            self.browser.page().runJavaScript(
                "window.setGameModeUI && window.setGameModeUI(%s);" % ("true" if on else "false"))
        except Exception:
            pass
        if on:
            print("\U0001F634 [游戏模式]: 已进入休眠（%s；%s）"
                  % (why or "游戏", "完全隐藏" if hide else "保持可见但完全点穿"),
                  flush=True)
        else:
            print("\U0001F31E [游戏模式]: 已退出休眠，她恢复响应。", flush=True)

    def _poll_alpha(self):
        try:
            self.browser.page().runJavaScript(
                "(function(){var p=window.__alphaPayload;window.__alphaPayload=null;"
                "var g=window.__gmPayload;window.__gmPayload=null;"
                "var c=window.__uiCmd;window.__uiCmd=null;"
                "return (p||'')+'\u0001'+(g||'')+'\u0001'+(c||'');})()",
                self._on_poll_payload)
        except Exception:
            pass

    def _on_poll_payload(self, payload):
        try:
            txt = str(payload or "")
            parts = txt.split('\u0001')
            a = parts[0] if len(parts) > 0 else ''
            g = parts[1] if len(parts) > 1 else ''
            c = parts[2] if len(parts) > 2 else ''
            # UI 指令（换装等）走这条可靠通道，避免被遮罩信号合并吞掉
            if c:
                # 【去重保险】同一条 UI 指令 600ms 内只处理一次 ——
                # 万一以后哪条通道也变成双发，这里能挡住。
                try:
                    import time as _t
                    now = _t.time()
                    if c == getattr(self, "_last_ui_cmd", "") and (now - getattr(self, "_last_ui_cmd_t", 0) < 0.6):
                        c = ""
                    else:
                        self._last_ui_cmd = c
                        self._last_ui_cmd_t = now
                except Exception:
                    pass
            if c:
                try:
                    self.on_html_signal(c)
                except Exception as e:
                    print("[ui-cmd] failed: %s" % e, flush=True)

            # 【掉落动作同步】开局那段路不会经过 apply_outfit，所以这里兜底：
            # 只要当前衣服的掉落动作和上次推的不一样，就补推一次。
            # （否则开局时 window.__dropMotion 是空的 -> 拖她不会掉落）
            try:
                import json as _json
                _cur = (llm_brain.config.get("saved_outfit") or "").strip()
                _want = outfit_manager.drop_motion(_cur) or ""
                if _cur and getattr(self, "_pushed_drop_for", None) != _cur:
                    self._pushed_drop_for = _cur
                    self.browser.page().runJavaScript(
                        "window.__dropMotion = %s;" % _json.dumps(_want))
                    self.browser.page().runJavaScript(
                        "window.__dropReal = %s;" % ("true" if (outfit_manager.OUTFIT_DROP.get(_cur) or {}).get("real") else "false"))
                    print("\U0001F457 [\u6389\u843d] \u5df2\u540c\u6b65\u300c%s\u300d\u7684\u6389\u843d\u52a8\u4f5c: %s" % (_cur, _want or "(\u65e0)"), flush=True)
            except Exception:
                pass
            if g:
                g = g.strip().lower()
                if g.startswith("arm:"):
                    val = (g[4:] == "on")
                    llm_brain.config["game_mode_enabled"] = val
                    self._save_config_flag("game_mode_enabled", val)
                    print("[game-mode] auto-detect armed = %s" % val, flush=True)
                elif g.startswith("hide:"):
                    val = (g[4:] == "on")
                    llm_brain.config["game_mode_hide"] = val
                    self._save_config_flag("game_mode_hide", val)
                    print("[game-mode] sleep style hide = %s" % val, flush=True)
                self._game_mode = None
                self._game_mode_tick()
            if a:
                self._set_alpha_bitmap(a)
        except Exception:
            pass

    def _set_alpha_bitmap(self, payload):
        try:
            import base64 as _b64
            parts = payload.split(":", 5)
            div, gw, gh = int(parts[0]), int(parts[1]), int(parts[2])
            blob = parts[3]
            model_bounds = parts[4] if len(parts) > 4 else "(无)"
            ui_rects = parts[5] if len(parts) > 5 else "(无)"
            raw = _b64.b64decode(blob)
            if div < 1 or gw < 1 or gh < 1 or len(raw) * 8 < gw * gh:
                return
            self._alpha_div = div
            self._alpha_gw = gw
            self._alpha_gh = gh
            self._alpha_bits = raw
            if not getattr(self, "_alpha_logged", False):
                self._alpha_logged = True
                print("🎯 [命中测试] 已启用逐像素 alpha 判定（%dx%d 栅格，1/%d 分辨率）"
                      % (gw, gh, div), flush=True)
            # 诊断：从位图反推"可点区域"在 CSS 像素下的包围盒（便于核对位置）
            if os.environ.get("ROMASHA_HIT_DEBUG") and not getattr(self, "_alpha_box_logged", False):
                self._alpha_box_logged = True
                minx = miny = 1 << 30
                maxx = maxy = -1
                for gy in range(gh):
                    base = gy * gw
                    for gx in range(gw):
                        i = base + gx
                        if (i >> 3) < len(raw) and (raw[i >> 3] >> (i & 7)) & 1:
                            if gx < minx: minx = gx
                            if gx > maxx: maxx = gx
                            if gy < miny: miny = gy
                            if gy > maxy: maxy = gy
                if maxx >= 0:
                    print("🔍 [命中] 位图里的可点区域 = CSS(%d,%d)-(%d,%d)  窗口=%dx%d"
                          % (minx * div, miny * div, (maxx + 1) * div, (maxy + 1) * div,
                             self.width(), self.height()), flush=True)
                    print("🔍 [命中] 模型自报 getBounds = %s   <- 两者应完全重合" % model_bounds,
                          flush=True)
                    print("🔍 [命中] 已并入的网页 UI 矩形 = %s" % ui_rects, flush=True)
        except Exception:
            return

    def _alpha_hit(self, lx, ly):
        """返回 True/False；返回 None 表示"已关闭/无位图"，请走兜底。

        几何已校准并实测通过：她身上的点 -> 可点；旁边的点不属于窗口 -> 桌面。
        如需退回旧的"包围盒竖带"行为，设环境变量 ROMASHA_ALPHA_HIT=0。
        """
        if os.environ.get("ROMASHA_ALPHA_HIT") == "0":
            return None
        bits = getattr(self, "_alpha_bits", None)
        if not bits:
            return None
        div = self._alpha_div
        gx = int(lx // div)
        gy = int(ly // div)
        if gx < 0 or gy < 0 or gx >= self._alpha_gw or gy >= self._alpha_gh:
            return False
        idx = gy * self._alpha_gw + gx
        bi = idx >> 3
        if bi >= len(bits):
            return False
        return bool(bits[bi] & (1 << (idx & 7)))

    def _fallback_hit(self, lx, ly):
        """没有 alpha 位图时的兜底：包围盒正中 50% 宽的竖带。"""
        try:
            from PyQt5.QtCore import QPoint
            r = getattr(self, "_last_good_region", None)
            if r is None or r.isEmpty():
                return False
            b = r.boundingRect()
            if not b.contains(QPoint(int(lx), int(ly))):
                return False
            cx = b.x() + b.width() / 2.0
            return abs(lx - cx) <= max(12.0, b.width() * 0.25)
        except Exception:
            return False

    def _deactivate_ui(self):
        """窗口失去激活（用户点了桌面/切到别的程序）时，收起输入框与面板。"""
        try:
            self.browser.page().runJavaScript(
                "window.closePetUI && window.closePetUI();")
        except Exception:
            pass

    def _screen_to_local_css(self, sx, sy):
        """把 WM_NCHITTEST 给的屏幕坐标换算成"网页 CSS 像素"下的窗口内坐标。

        不能直接用 mapFromGlobal：lParam 来自 Win32（设备像素），而 Qt 用的是
        逻辑像素，本机 125% 缩放下两者差一个系数；而且进程间的 DPI 感知状态
        还不一定一致。所以用窗口自身的两个宽度来自标定：
            CSS = (屏幕坐标 - Win32窗口左上) * Qt窗口宽 / Win32窗口宽
        这样无论缩放/感知如何都成立。
        """
        import ctypes.wintypes as _wt
        r = _wt.RECT()
        ctypes.windll.user32.GetWindowRect(int(self.winId()), ctypes.byref(r))
        rw = max(1, r.right - r.left)
        rh = max(1, r.bottom - r.top)
        return ((sx - r.left) * self.width() / float(rw),
                (sy - r.top) * self.height() / float(rh))

    def nativeEvent(self, event_type, message):
        # WM_NCHITTEST(0x0084)：Windows 每次鼠标移动/按键前都会问
        # "这个点算不算你的客户区"。回 HTTRANSPARENT(-1) 等于"这点没有窗口"。
        try:
            et = event_type
            if isinstance(et, (bytes, bytearray)):
                et = et.decode("ascii", "ignore")
            if et == "windows_generic_MSG":
                import ctypes.wintypes as _wt
                msg = _wt.MSG.from_address(int(message))
                if msg.message == 0x0312:   # WM_HOTKEY（Ctrl+Alt+G 手动切游戏模式）
                    self._manual_game = not getattr(self, "_manual_game", False)
                    self._game_mode = None
                    self._game_mode_tick()
                    return (True, 0)
                if msg.message == 0x0006:   # WM_ACTIVATE
                    # 低 16 位为 0 = 失去激活，说明用户去点桌面或别的程序了。
                    # 她的窗口是全屏+点击穿透的，网页收不到"点了桌面"的事件，
                    # 所以这里由 Python 转发给网页，让它收起输入框与面板。
                    if (int(msg.wParam) & 0xFFFF) == 0:
                        self._deactivate_ui()
                if msg.message == 0x0084:
                    lp = int(msg.lParam)
                    sx = ctypes.c_short(lp & 0xFFFF).value
                    sy = ctypes.c_short((lp >> 16) & 0xFFFF).value
                    # 【游戏模式】休眠时整窗透传：绝不吞掉游戏的任何一次点击
                    if getattr(self, "_sleep", False):
                        return (True, -1)
                    # 【关键】拖动期间整窗都算"可点"，不查位图。
                    # 拖动时她永远追不上光标，光标必然滑出她的像素范围；
                    # 若此时回 HTTRANSPARENT，Windows 会把后续鼠标事件交给桌面，
                    # 拖动就当场断掉 —— 表现就是"移到边边就动不了她"。
                    if getattr(self, "_dragging", False):
                        import time as _time
                        now = _time.time()
                        if now - getattr(self, "_drag_t", 0) > 5.0:
                            self._dragging = False      # 兜底：DRAG_END 丢了也不会永久占屏
                        else:
                            self._drag_t = now
                            return (True, 1)
                    lx, ly = self._screen_to_local_css(sx, sy)
                    hit = self._alpha_hit(lx, ly)
                    if hit is None:
                        hit = self._fallback_hit(lx, ly)
                    # 诊断日志默认关闭；需要排查时设 ROMASHA_HIT_DEBUG=1
                    if os.environ.get("ROMASHA_HIT_DEBUG") and getattr(self, "_hit_dbg", 0) < 2000:
                        self._hit_dbg = getattr(self, "_hit_dbg", 0) + 1
                        print("🔍 [命中] 屏幕(%d,%d) -> 本地(%.0f,%.0f)  窗口%dx%d 位图=%s -> %s"
                              % (sx, sy, lx, ly, self.width(), self.height(),
                                 "有" if getattr(self, "_alpha_bits", None) else "无",
                                 "可点" if hit else "穿走"), flush=True)
                    return (True, 1 if hit else -1)
        except Exception:
            pass
        return super().nativeEvent(event_type, message)

    def on_html_signal(self, title):
        if title == "EVENT:READY":
            self.showNormal()
            self.apply_initial_state()

            try:
                                              
                                 
                scale = float(llm_brain.config.get("scale", 0.5))
                x = float(llm_brain.config.get("pos_x", -1))
                y = float(llm_brain.config.get("pos_y", 100))

                scr = QApplication.primaryScreen().geometry()
                if not (0.1 <= scale <= 1.5):
                    print("⚠️ [立绘]: 存档里的缩放 %s 不合理（会看不见她），已自动复位。" % scale)
                    scale = 0.5
                if x < -1 or x > scr.width() - 40:
                    x = -1.0
                if y < 0 or y > scr.height() - 80:
                    y = 100.0
                llm_brain.config["scale"] = scale
                llm_brain.config["pos_x"] = x
                llm_brain.config["pos_y"] = y

                           
                self.is_tracking_enabled = bool(llm_brain.config.get("track_enabled", True))
                self.is_touch_enabled = bool(llm_brain.config.get("touch_enabled", True))

                track_str = "true" if self.is_tracking_enabled else "false"
                touch_str = "true" if self.is_touch_enabled else "false"

                                  
                init_js = f"window.applySavedState({scale}, {x}, {y}, {track_str}, {touch_str});"
                self.browser.page().runJavaScript(init_js)
                self.refresh_touch_state()

                                  
                bubble_size = llm_brain.config.get("bubble_size", 1)
                self.browser.page().runJavaScript(f"window.setBubbleSize({bubble_size});")

            except Exception as e:
                print(f"状态恢复异常: {e}")

                                     
            if llm_brain.config.get("is_first_encounter", True):
                intro_text = "故事刚刚开始：她刚刚击败龙人少女，又遭遇了迪亚德的羞辱与监控，正一个人在房间里心力交瘁、极度迷茫……(试着对她搭话来开启命运的齿轮吧)"

                                         
                def show_delayed_intro():
                    print(f"\n🌟 [命运指引]: {intro_text}")
                                             
                    bubble_html = f"<span style='color:#6031e2; font-weight:bold; font-size: var(--sub-font-size);'>🌟 {intro_text}</span>"
                    self.show_system_notification(bubble_html, 10000)

                                                           
                QTimer.singleShot(2000, show_delayed_intro)

                                               
            self.mouse_timer.start(50)
            self.idle_timer.start(1000)
            QTimer.singleShot(1200, self.push_relationship_stats)
            QTimer.singleShot(8000, self.check_model_ready)
            return

                            
        if title == "EVENT:AUDIO_END":
            self.on_speech_finished()
            return

        if title.startswith("STATS:REQUEST"):
            self.push_relationship_stats()
            return

        if title.startswith("GALLERY:REQUEST"):
            self.push_gallery_manifest()
            return

        if title.startswith("MEMORY:REQUEST"):
            # 【回想 -> 独立场景查看器】不再塞进桌宠那个小窗口里
            try:
                import subprocess as _sp
                _base = os.path.dirname(os.path.abspath(__file__))
                _exe = os.path.join(_base, "venv", "Scripts", "pythonw.exe")
                if not os.path.isfile(_exe):
                    _exe = sys.executable
                _sp.Popen([_exe, os.path.join(_base, "scene_viewer.py")], cwd=_base)
                print("\U0001F3AC [\u56de\u60f3]: \u5df2\u6253\u5f00\u72ec\u7acb\u573a\u666f\u67e5\u770b\u5668", flush=True)
                return
            except Exception as _e:
                print("\U0001F3AC [\u56de\u60f3]: \u6253\u5f00\u67e5\u770b\u5668\u5931\u8d25(%s)\uff0c\u6539\u7528\u5185\u7f6e\u5217\u8868" % _e, flush=True)
            self.push_memory_list()
            # 兜底时才把中心卡片显示出来（正常路径是打开独立查看器）
            try:
                self.browser.page().runJavaScript(
                    "if(window.galleryEl){window.galleryEl.style.display='block';}")
            except Exception:
                pass
            return

        if title.startswith("MEMORY:OK:"):
            print(f"📖 [回想房]: 前端已渲染 {title.split(':', 2)[2]} 个回想条目。")
            return

        if title.startswith("SCENE:OK:"):
            print("🎬 [动态场景]: 已开始播放 -> %s（独立画面，不影响桌宠）" % title.split(":", 2)[2])
            return

        if title.startswith("SCENE:FAIL:"):
            print("⚠️ [动态场景]: 场景加载失败 -> %s" % title.split(":", 2)[2])
            return

        if title.startswith("STATS:OK:"):
            print(f"\n📊 [关系面板]: 前端已确认收到数据（{title.split(':', 2)[2]} 项）。")
            return

        if title.startswith("GALLERY:OK:"):
            print(f"🎨 [画册]: 前端已渲染 {title.split(':', 2)[2]} 张缩略图。")
            return

        if title.startswith("MODELS:REQUEST"):
            self.push_model_list()
            return

        if title.startswith("HSCENES:REQUEST"):
            self.push_h_scene_list()
            return

        if title.startswith("SCENE:PLAY:"):
            sid = title.split(":")[2] if len(title.split(":")) > 2 else ""
            print("🎬 [Scene]: 收到播放请求 -> %s" % sid)
            ok = scene_player.play_scene(self.browser, sid)
            if not ok:
                print("⚠️ [Scene]: 播放失败，找不到 %s（world_data/scenes/ 里有这文件吗？）" % sid)
            return

        if title.startswith("MODEL:SWITCH:"):
            self.switch_live2d_model(title.split(":", 2)[2])
            return

        if title.startswith("MODELS:OK:"):
            print(f"🧍 [立绘]: 前端已渲染 {title.split(':', 2)[2]} 个立绘选项。")
            return

        if title.startswith("OUTFIT:REQUEST"):
            self.push_outfit_list()
            return

        if title == "HELP:OPEN":
            self.open_action_manual()
            return

        if title == "SETTINGS:OPEN":
            # 打开独立的、屏幕居中的设置窗口（不再做在她的小窗口里）
            self.open_ai_settings()
            return

        if title.startswith("SETTINGS:SAVE:"):
            try:
                import json as _json
                _d = _json.loads(title.split(":", 2)[2])
                _changed = []
                for _k in ("api_type", "base_url", "api_key", "target_model",
                           "sovits_url", "cosy_url"):
                    if _k in _d and llm_brain.config.get(_k) != _d[_k]:
                        llm_brain.config[_k] = _d[_k]
                        _changed.append(_k)
                llm_brain.save_config()
                # 模型名可能是模块级变量，一并更新
                try:
                    if "target_model" in _d and _d["target_model"]:
                        llm_brain.TARGET_MODEL = _d["target_model"]
                except Exception:
                    pass
                self.browser.page().runJavaScript(
                    "try{var m=document.getElementById('set-msg');"
                    "if(m)m.textContent='\u5df2\u4fdd\u5b58\uff08%s \u9879\uff09';}catch(e){}"
                    % ("\u66f4\u65b0 " + str(len(_changed)) if _changed else "\u65e0\u53d8\u5316"))
                print("\u2699\ufe0f [\u8bbe\u7f6e]: \u5df2\u4fdd\u5b58 AI \u914d\u7f6e\uff08%s\uff09" % (", ".join(_changed) or "\u65e0\u53d8\u5316"), flush=True)
            except Exception as _e:
                print("[\u8bbe\u7f6e] \u4fdd\u5b58\u5931\u8d25: %s" % _e, flush=True)
            return

        if title == "OUTFIT:RESTORE":
            # 【脱下来就要穿上】掉落看完了 -> 按标准状态整份穿回
            try:
                import json as _json
                _cur = (llm_brain.config.get("saved_outfit") or "").strip() or None
                _snap = (getattr(self, "_outfit_snapshots", None) or {}).get(_cur)
                if _snap:
                    for _k, _v in _snap.items():
                        self.set_parameter(_k, _v)
                    print("\U0001F457 [\u7a7f\u56de] \u6389\u843d\u7ed3\u675f\uff0c\u5df2\u6309\u6807\u51c6\u72b6\u6001\u628a\u300c%s\u300d\u7a7f\u56de\uff08%d \u4e2a\u53c2\u6570\uff09" % (_cur, len(_snap)), flush=True)
                elif _cur:
                    self.apply_outfit(_cur, react=False)
                    print("\U0001F457 [\u7a7f\u56de] \u6389\u843d\u7ed3\u675f\uff0c\u5df2\u91cd\u65b0\u5957\u4e0a\u300c%s\u300d" % _cur, flush=True)
            except Exception as _e:
                print("[\u7a7f\u56de] \u5931\u8d25: %s" % _e, flush=True)
            return

        if title.startswith("OUTFIT:SET:"):
            # 玩家手动换装时的两件清理，缺一不可：
            #   1) 取消待执行的"滑落后自动穿回"（否则 20 秒后覆盖你的选择）
            #   2) 终止正在播的场景（场景会切模型，释放时会把模型换回来，
            #      导致你刚选的衣服看起来"没生效/没重置"）
            try:
                if getattr(self, "_restore_timer", None):
                    self._restore_timer.stop()
                    self._restore_timer = None
                    print("[换装] 已取消待执行的自动穿回（以你手动选择为准）", flush=True)
            except Exception:
                pass
            _pick = title.split(":", 2)[2]
            if _pick in self.ACCESSORY_KEYS:
                self.toggle_accessory(_pick)      # 配饰 = 开关，不换衣服
            else:
                self.apply_outfit(_pick, react=True)
            return

        if title.startswith("HAIR:SET:"):
            self.apply_hair(title.split(":", 2)[2])
            return

        if title.startswith("OUTFITS:OK:"):
            print(f"👗 [换装]: 前端已渲染 {title.split(':', 2)[2]} 套衣服。")
            return

        if title.startswith("POSE:RESET"):
            self.reset_live2d_pose()
            return

                             
        if title.startswith("EVENT:LOAD_ERROR:"):
            err = title.split(":", 2)[2]
            try:
                err = unquote(err)
            except Exception:
                pass
            print(f"⚠️ [模型加载失败]: {err}")
            return

                                  
        if title.startswith("GAMEMODE:"):
            v = title.split(":", 1)[1].strip().lower()
            self._manual_game = (v == "on")
            try:
                import time as _t
                self._last_game_seen = _t.time()
            except Exception:
                pass
            self._game_mode = None
            self._game_mode_tick()
            return

        if title.startswith("ALPHA:"):
            self._set_alpha_bitmap(title.split(":", 1)[1])
            return

        if title.startswith("MASK:"):
            rects_data = title.split(":", 1)[1]
            region = QRegion()
            for rect_str in rects_data.split('|') if rects_data else []:
                try:
                    x, y, w, h = map(float, rect_str.split(','))
                    region = region.united(QRegion(QRect(int(x - 12), int(y - 12), int(w + 24), int(h + 24))))
                except Exception:
                    continue
            if not region.isEmpty():
                self._last_good_region = region
                self.setMask(region)
            elif getattr(self, "_last_good_region", None) is not None:
                # 【修正】空区域通常意味着她暂时被拖到窗口外了。
                # 这时绝不能 clearMask()：整个窗口会失去遮罩 ——
                # 她既看不见也点不到，而且桌面点击会被这个全屏窗口全部吃掉。
                # 保留上一次的有效区域，等下一帧热区回来再更新。
                self.setMask(self._last_good_region)
            else:
                self.clearMask()
            return

        if title == "DRAG_START":
            # 拖动期间整窗可接收鼠标（原版就是 clearMask 这么做的）；
            # 同时置标志位，让 WM_NCHITTEST 也放行整窗，两者必须一致，
            # 否则光标一旦滑出她的像素范围，拖动就会中途断掉。
            self._dragging = True
            try:
                import time as _time
                self._drag_t = _time.time()
            except Exception:
                pass
            # Let the model travel outside its previous hit region while it
            # is being dragged. The mask is rebuilt once on release.
            self.clearMask()
            return

        if title == "DRAG_END":
            self._dragging = False
            return

                               
        if title.startswith("DRAG_STATE:") or title.startswith("WHEEL_STATE:"):
            try:
                parts = title.split(":")
                              
                llm_brain.config["scale"] = float(parts[1])
                llm_brain.config["pos_x"] = float(parts[2])
                llm_brain.config["pos_y"] = float(parts[3])
                                            
                                                  
                self.auto_save_timer.start(1500)
            except Exception as e:
                pass                

                                       
            if title.startswith("DRAG_STATE:"):
                self.vision_idle_seconds = 0
                if self.is_tracking_enabled:
                    self.browser.page().runJavaScript("window.toggleTracking(true);")
            return

        if title.startswith("CHAT:"):
            user_text = title.split(":", 1)[1]
            self.reset_afk()

            if user_text.strip() == '/reset':
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('「不可逆的抉择：世界线重置」')
                msg_box.setText("真的要让她忘记这一切吗？\n你们将回到最初始的陌生人状态。")
                msg_box.setIcon(QMessageBox.Warning)
                                     
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web/favicon.ico')
                if os.path.exists(icon_path):
                    msg_box.setWindowIcon(QIcon(icon_path))
                yes_btn = msg_box.addButton("确定", QMessageBox.YesRole)
                no_btn = msg_box.addButton("取消", QMessageBox.NoRole)
                msg_box.setDefaultButton(no_btn)
                msg_box.exec_()
                if msg_box.clickedButton() == yes_btn:
                                                           
                    self.brain_worker.is_cancelled = True
                    with self.brain_worker.task_queue.mutex:
                        self.brain_worker.task_queue.queue.clear()

                                            
                    self.tts_worker.is_cancelled = True

                    with self.tts_worker.task_queue.mutex:
                        self.tts_worker.task_queue.queue.clear()

                    self.is_waiting_for_voice = False
                    self.browser.page().runJavaScript(
                        "if(typeof window.stopRomashaVoice === 'function') window.stopRomashaVoice();")
                    self.pending_tags.clear()
                    self.touch_temp_locked = False
                    self.refresh_touch_state()
                    self.is_story_mode = False
                    self.story_window.clear_story_content()
                    self.story_window.hide()

                                   
                    self.brain_worker.task_queue.put(("/SYSTEM_RESET_MEMORY", ""))

                            
                    self.current_context_html = ""
                    self.current_display_text = ""
                    self.target_display_text = ""
                    self.accumulated_text = ""            

                    self.show_system_notification("<span style='color:#888; font-size: var(--sub-font-size);'><i>(记忆已被重置，迎来了崭新的初见...)</i></span>", 3000)
                                               
                    self.story_window.name_btn.setText("👤 当前玩家: 未命名")
                    self.manual_outfit_lock = False             


                                                                
                                          
                                                                
                                            
                    self.set_parameter('ParamCheek', 0.0)
                    self.set_parameter('angry', 0.0)

                                                                          
                    idx = motion_manager.get_motion_index('talk')
                    if idx is not None:
                        self.current_idle_motion = idx
                                                                
                                                                
                                                            
                        self.set_idle_motion(idx)

                                                       
                                                            
                    llm_brain.config["intimacy"] = 0
                    outfit_manager.restore_state(None, None)
                    llm_brain.config["saved_outfit"] = ""
                    llm_brain.config["saved_hair"] = ""
                    llm_brain.config["saved_outfit_period"] = ""
                    llm_brain.config["night_outfit_roll_key"] = ""
                    llm_brain.config["night_outfit_result"] = ""
                    llm_brain.config["last_recent_chat_time"] = 0
                    llm_brain.save_config()
                    self.apply_initial_state()

                return

            if user_text.startswith('/auto '):
                                    
                player_name = llm_brain.config.get("player_name", "")
                if not player_name:
                    dialog = NameEditDialog("", self)
                    if dialog.exec_() == QDialog.Accepted and dialog.get_name():
                        name = dialog.get_name()
                        llm_brain.config["player_name"] = name
                        llm_brain.save_config()
                        self.story_window.name_btn.setText(f"👤 当前玩家: {name}")
                    else:
                        self.show_system_notification("<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(取消了推演...)</i></span>", 1500)
                        return

                level = user_text.split(' ')[1].strip()
                if level in ["0", "1", "2", "3"]:
                    self.is_story_mode = True             
                    self.story_window.level_combo.setCurrentIndex(int(level))                     
                    self.story_level = level
                                            
                    llm_brain.chat_history = [msg for msg in llm_brain.chat_history if
                                              not msg.get("content", "").startswith("[系统机制")]
                    story_manager.save_recent_chat_history(llm_brain.chat_history, max_items=16)
                    self.show_system_notification(
                        f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(已切入世界线推演模式，参与度: {level}...)</i></span>",
                        3000)

                                                       
                    self.start_new_thought(f"/STORY_TICK_{level}_")
                return

            if user_text.startswith('/choice ') and getattr(self, 'is_story_mode', False):
                choice_text = user_text.replace('/choice ', '').strip()
                                           
                llm_brain.chat_history = [msg for msg in llm_brain.chat_history if
                                          not msg.get("content", "").startswith("[系统机制")]
                story_manager.save_recent_chat_history(llm_brain.chat_history, max_items=16)
                                    
                current_level = str(self.story_window.level_combo.currentIndex())
                self.start_new_thought(f"/STORY_TICK_{current_level}_{choice_text}")
                return

            if user_text.startswith('/track '):
                state_val = user_text.split(' ')[1]
                state_bool = state_val != "0"
                                 
                self.is_tracking_enabled = state_bool
                state_str = "false" if not state_bool else "true"
                self.browser.page().runJavaScript(f"window.toggleTracking({state_str});")

                                      
                llm_brain.config["track_enabled"] = state_bool
                llm_brain.save_config()

                         
                action_desc = "重新锁定了你的身影" if state_bool else "不再追随你的动作"
                print(f"\n👁️ [空间感知]: Romasha的视线{action_desc}。")

                         
                bubble_desc = "她似乎注意到了你在这边..." if state_bool else "她移开了视线，不再关注你的举动..."
                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 1500)                   
                return

                                     
            if user_text.startswith('/touch '):
                state_val = user_text.split(' ')[1]
                state_bool = state_val != "0"
                self.is_touch_enabled = state_bool
                                                                  
                                                                                       
                self.refresh_touch_state()

                                      
                llm_brain.config["touch_enabled"] = state_bool
                llm_brain.save_config()

                         
                action_desc = "仿佛重新建立起了真实的触感，能感受到彼此的温度" if state_bool else "之间仿佛隔了一层不可触及的空气墙"
                print(f"\n👆 [无声羁绊]: 你们{action_desc}。")

                         
                bubble_desc = "她似乎能真切感受到你的存在..." if state_bool else "触碰的感知似乎被隔绝了..."
                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 1500)                   
                return

                                     
            if user_text.startswith('/voice '):
                val = user_text.split(' ')[1].strip().lower()

                if val in ["0", "1"]:
                    state_bool = val == "1"
                    llm_brain.config["voice_enabled"] = state_bool
                    llm_brain.save_config()

                                 
                    if state_bool:
                        print(f"\n💭 [感官羁绊]: 周围安静了下来，你终于又能听见她清晰的声音了。")
                        bubble_desc = "你靠近了一些，试着倾听她的声音..."
                    else:
                        print(f"\n💭 [感官羁绊]: 环境变得嘈杂，你只能通过她的眼神和口型来理解她。")
                        bubble_desc = "周围有些吵闹，你默默注视着她..."

                elif val in ["cosyvoice", "sovits"]:
                    llm_brain.config["tts_engine"] = val
                    llm_brain.config["voice_enabled"] = True               
                    llm_brain.save_config()
                    print(f"\n💭 [灵魂调律]: 冥冥之中，她发声的方式与声线中蕴含的温度，似乎发生了极其微妙的改变。")
                    bubble_desc = f"一阵轻微的恍惚后，她的声音听起来似乎有些不同了：{val}..."
                else:
                    return          

                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 5000)                   
                return

                                  
            if user_text.startswith('/size '):
                try:
                    size_val = int(user_text.split(' ')[1].strip())
                    if size_val in [0, 1, 2]:
                        llm_brain.config["bubble_size"] = size_val
                        llm_brain.save_config()
                        self.browser.page().runJavaScript(f"window.setBubbleSize({size_val});")
                        size_desc = ['稍微拉远', '恰到好处', '更加贴近'][size_val]
                        print(f"\n📏 [认知焦距]: 伴随着你注意力的集中，眼前的思绪与话语变得{size_desc}了。")

                        bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>(视界已调整为适宜的大小...)</i></span>"
                        self.show_system_notification(bubble_html, 1500)                   
                except Exception:
                    pass
                return

                                     
            if user_text.startswith('/chapter '):
                try:
                    chap_val = int(user_text.split(' ')[1].strip())
                    if chap_val >= 1:
                        llm_brain.config["current_chapter"] = chap_val
                        llm_brain.save_config()

                                 
                        print(f"\n📖 [命运流转]: 世界的齿轮已拨动，当前推演时间线跃迁至：第 {chap_val} 章。")

                                
                        bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(时间的刻度跳动了，你们来到了新的阶段：第 {chap_val} 章...)</i></span>"
                        self.show_system_notification(bubble_html, 2000)
                except Exception:
                    print("⚠️ [命运流转]: 章节刻度没有被正确拨动。若要切换世界线阶段，请使用 /chapter 2 这样的写法。")
                return

                                    
            if user_text.startswith('/ja '):
                val = user_text.split(' ')[1].strip()
                if val in ["0", "1"]:
                    state_bool = val == "1"
                    llm_brain.config["tts_translate_to_ja"] = state_bool
                    llm_brain.save_config()

                                
                    if state_bool:
                        print(f"\n🌐 [语言中枢]: 她的发声回路切换为了古老的异国语调 (日语翻译已开启)。")
                        bubble_desc = "她的口型似乎在尝试一种古老而优雅的发音..."
                    else:
                        print(f"\n🌐 [语言中枢]: 她的发声回路恢复了你所熟悉的语言 (日语翻译已关闭)。")
                        bubble_desc = "她的语调恢复了正常的频率..."

                    bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                    self.show_system_notification(bubble_html, 1500)                   
                return

                                     
                       
            self.current_context_html = f"<span style='color:#48a1fa; font-size: var(--main-font-size);'>你: {user_text}</span><br>"
            self.last_text_finish_time = datetime.datetime.now()                    
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(她倾听着你的话语...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
                          
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                                         
                                                                 
                               
                                                               
                                        

                                
                                                                                                                                                                                                                 
                  
                                           

                            
            self.start_new_thought(user_text)
            return

        if title.startswith("TOUCH:"):
            part = title.split(":")[1]
            self.reset_afk()
                                         
            self.touch_temp_locked = True
            self.refresh_touch_state()

            '''
            touch_prompts = {
                "head": "*你温柔地摸了摸她的头*",
                "face": "*你轻轻戳了戳她的脸颊*",
                "bust": "*你不小心碰到了她的胸部*",
                "belly": "*你搂住了她的腰*",
                "hip": "*你不小心碰到了她的臀部*",  # 两侧的判定
                "crotch": "*你不小心碰到了她的隐私部位*",  # 正中心的判定
                "leg": "*你碰到了她的腿*",
                "hand_right": "*你牵起了她的右手*",  # 对应屏幕左侧
                "hand_left": "*你握住了她的左手*",  # 对应屏幕右侧
                "unknown": "*你轻轻碰了碰她*"
            }
            action_text = touch_prompts.get(part, "*你触碰了她*")
            '''
            action_text = self.get_touch_prompt(part)
            instant_line = self.react_to_touch(part)

                                         
            self.current_context_html = f"<span style='color:#fd92a1; font-size: var(--main-font-size);'>{action_text}</span><br>"
            if instant_line:
                bubble_html = self.current_context_html + f"<span style='color:#ffc0d0; font-size: var(--sub-font-size);'>{instant_line}</span>"
            else:
                bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(感受中...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
                          
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

            self.start_new_thought(action_text)

    def start_new_thought(self, prompt_text):
                                               
                                 
        self.static_mood_timer.stop()
        self.speech_end_timer.stop()                               

                              
        if prompt_text.startswith("/STORY_TICK_"):
                        
            parts = prompt_text.split("_", 3)
            level = parts[2]
            choice_text = parts[3] if len(parts) > 3 and parts[3] else "开启世界线推演"
            print(
                f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 📖 [命运编织]: 世界线正在向新的分歧点推演 (参与度: {level})...")
                                        
            self.story_window.prepare_new_chapter(f"▶ 抉择: {choice_text} (参与度: {level})")
                              
        elif prompt_text.startswith("[系统机制"):
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 🍃 [时光流逝]: {prompt_text[6:19]}...")
        else:
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 👤 你: {prompt_text}")

        interrupted_text = ""
        if self.accumulated_text:
            print("💬 [观察]: 她的话音戛然而止，注意力瞬间被你刚才的举动吸引。")
            clean_accumulated = re.sub(r'\[.*?\]', '', self.accumulated_text).strip()
            if len(clean_accumulated) > 2:
                interrupted_text = clean_accumulated

                          
        self.accumulated_text = ""
        self.target_display_text = ""
        self.current_display_text = ""
        self.processed_tags.clear()
        self.pending_tags.clear()              
        self.is_waiting_for_voice = llm_brain.config.get("voice_enabled", True)
                             
        if self.is_waiting_for_voice:
            self.browser.page().runJavaScript("window.setMotionHoldMode('until_release');")
        else:
            self.browser.page().runJavaScript("window.setMotionHoldMode('fixed');")

                             
        self.browser.page().runJavaScript(
            "if(typeof window.stopRomashaVoice === 'function') window.stopRomashaVoice();")

                                     
        self.tts_worker.is_cancelled = True
        with self.tts_worker.task_queue.mutex:
            self.tts_worker.task_queue.queue.clear()
                                                       

        self.brain_worker.interrupt_and_submit(prompt_text, interrupted_text)

    def recover_taol_fall(self):
                               
        if getattr(self, 'is_story_mode', False):
            return

                                      
        sys_prompt = "[系统机制：距离刚才浴巾意外滑落已经过去了整整10秒。你现在急忙蹲下重新捡起并紧紧裹好了浴巾。请必须输出 [wear_towel] 标签，并伴随极其娇羞、甚至带有哭腔或羞愤的动作（如 [mood_talk_ero]）与慌乱的话语/心声。]"

                      
                                       
        self.current_context_html = "<span style='color:#fd92a1; font-size: var(--main-font-size);'><i>(短暂的慌乱后，她急急忙忙重新裹好了浴巾...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(满脸通红手忙脚乱中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

                                 
        self.start_new_thought(sys_prompt)

    def on_task_finished(self):
        if self.accumulated_text.strip():
                                                        
                                    
                                                        
            if getattr(self, 'is_story_mode', False):
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🌸 剧情推演结束，处理分支中...")
                full_text = self.accumulated_text

                                                                        
                                                                            
                                             
                options_match = re.search(r'[<＜]\s*options\s*[>＞](.*?)([<＜]/\s*options\s*[>＞]|$)', full_text,
                                          flags=re.DOTALL | re.IGNORECASE)
                self.pending_story_options = []
                options_raw = ""
                fallback_match = None

                if options_match:
                    options_raw = options_match.group(1).strip()
                else:
                                                                        
                    fallback_match = re.search(r'(1\.\s*.*)$', full_text, re.DOTALL)
                    if fallback_match:
                        options_raw = fallback_match.group(1).strip()
                        options_raw = re.sub(r'[<＜]/?\s*options\s*[>＞]?', '', options_raw, flags=re.IGNORECASE).strip()

                if options_raw:
                                                   
                                                        
                                                         
                    if re.search(r'\d+\.', options_raw):
                        opts = re.split(r'\d+\.\s*', options_raw)
                    elif re.search(r'[-*]\s+', options_raw):
                        opts = re.split(r'[-*]\s+', options_raw)
                    else:
                        opts = options_raw.split('\n')

                    self.pending_story_options = [opt.strip() for opt in opts if opt.strip()]

                                           
                print(
                    f"🎯 [系统诊断]: 成功提取到 {len(self.pending_story_options)} 个选项 -> {self.pending_story_options}")

                                              
                display_text = re.sub(r'[<＜]\s*options\s*[>＞].*?([<＜]/\s*options\s*[>＞]|$)', '', full_text,
                                      flags=re.DOTALL | re.IGNORECASE)
                                                            
                if not options_match and fallback_match:
                    display_text = display_text.replace(fallback_match.group(1), "").strip()

                display_text = re.sub(r'\[(act_|mood_|wear_|hair_).*?\]', '', display_text)

                                
                                          
                                                        
                say_matches = re.findall(r'\[say:\s*"(.*?)"\]', full_text, re.DOTALL)
                tts_text = "。".join(say_matches)

                if tts_text:
                            
                    clean_tts_print = re.sub(r'^.*?<\|endofprompt\|>', '', tts_text)
                                                               
                    clean_tts_print = re.sub(r'\[.*?\]', '', clean_tts_print).strip()
                    print(f"\n🗣️ [剧情高光台词]: {clean_tts_print}")

                                                               
                    bubble_html = f"<span style='color:#fd92a1; font-weight:bold; font-size: var(--main-font-size);'>「{clean_tts_print}」</span><br>"
                                                                                            
                    safe_html = bubble_html.replace("'", "\\'").replace("\n", "<br>")
                    self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                                                    
                display_text = re.sub(r'\[say:\s*"[^"]*?<\|endofprompt\|>(.*?)"\]', r'“\1”', display_text,
                                      flags=re.DOTALL)
                display_text = re.sub(r'\[say:\s*"(.*?)"\]', r'“\1”', display_text, flags=re.DOTALL)
                                             
                display_text = re.sub(r'\[.*?\]', '', display_text).strip()

                                    
                                                        
                                                                                             
                self.story_window.update_chapter_text(display_text)

                novel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_data", "novel_log.txt")
                os.makedirs(os.path.dirname(novel_path), exist_ok=True)
                with open(novel_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- 【记录时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】 ---\n")
                                  
                    f.write(self.story_window.target_text)

                         
                                  
                if self.is_waiting_for_voice:
                    if tts_text:
                        self.tts_worker.task_queue.put(tts_text)
                    else:
                        self.is_waiting_for_voice = False
                        self.speech_end_timer.start(2000)
                                                
                else:
                                                  
                                             
                                           
                    duration_ms = 2000
                    self.speech_end_timer.start(duration_ms)

                                                        
                                  
                                                        
            else:
                                                
                if self.accumulated_text.strip():
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🌸 Romasha: {self.accumulated_text}")
                                              
                    if self.is_waiting_for_voice:
                                                     
                        self.tts_worker.task_queue.put(self.accumulated_text)
                    else:
                                             
                        self.target_display_text = self.final_clean_text
                        if self.pending_tags:
                            self.flush_pending_tags()

                                                                
                        duration_ms = max(4000, len(self.final_clean_text) * 250)
                                                                                
                                                  
                        self.speech_end_timer.start(duration_ms)

                           
        self.accumulated_text = ""
                                           
        if self.touch_temp_locked:
                                      
            self.touch_temp_locked = False
            self.refresh_touch_state()

                                              
    def handle_stream_chunk(self, chunk):
        self.accumulated_text += chunk

                  
        tags = re.findall(r'\[(.*?)\]', self.accumulated_text)
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in self.processed_tags:
                self.processed_tags.add(tag_lower)
                                                     
                if tag_lower.startswith('intimacy_'):
                    self.execute_tag(tag_lower)
                elif tag_lower.startswith('set_name_'):                  
                    self.execute_tag(tag)                                
                                   
                elif tag_lower.startswith('move_to_'):
                    self.execute_tag(tag)               
                                         
                elif tag_lower.startswith('sys_chapter_up'):
                    self.execute_tag(tag_lower)
                                                      
                                                            
                elif tag_lower.startswith(('act_', 'mood_', 'wear_', 'hair_')):
                                                               
                                                        
                    if getattr(self, 'is_story_mode', False):
                        self.execute_tag(tag_lower)
                    else:
                                              
                        if self.is_waiting_for_voice:
                            self.pending_tags.append(tag_lower)                       
                        else:
                            self.execute_tag(tag_lower)

                                                    
                                  
                                                    
                     
        clean_text = re.sub(r'<options>.*?(</options>|$)', '', self.accumulated_text, flags=re.DOTALL)

                                        
        voice_tags = r'breath|quick_breath|laughter|cough|clucking|accent|noise|hissing|sigh|vocalized-noise|lipsmack|mn'
        regex_pattern = fr'\[(act_|mood_|wear_|hair_|intimacy_|set_name_|move_to_|sys_chapter_up|{voice_tags}).*?\]'
        clean_text = re.sub(regex_pattern, '', clean_text, flags=re.IGNORECASE)

                                                     
        clean_text = re.sub(r'\[say:\s*"[^"]*?<\|endofprompt\|>(.*?)"\]', r'“\1”', clean_text)
        clean_text = re.sub(r'\[say:\s*"(.*?)"\]', r'“\1”', clean_text)

                                             
        clean_text = re.sub(r'^.*?<\|endofprompt\|>', '', clean_text)

                             
        final_text = re.sub(r'\[[^\]]*$', '', clean_text).strip()

                                  
                                               
                                                                   
                                                           
                                                                    
                                                                      
                                                                             

                                                    
                                
                                                    
        if getattr(self, 'is_story_mode', False):
                                
            self.story_window.update_streaming_text(final_text)

                              
            bubble_html = "<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在进行世界线深度推演，请在日志面板查看...)</i></span>"
            self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\", true);")

        else:
                             
            self.final_clean_text = final_text

                                                  
            if self.is_waiting_for_voice:
                         
                bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(微启双唇，正在酝酿要说的话...)</i></span>"
                safe_html = bubble_html.replace("'", "\\'")
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")
            else:
                self.target_display_text = self.final_clean_text

                                  
    def typewriter_tick(self):
                                         
        if getattr(self, 'is_showing_notification', False):
            return

                            
        if self.current_display_text != self.target_display_text:
            self.is_typing = True
                                 
            if not self.target_display_text.startswith(self.current_display_text):
                self.current_display_text = self.target_display_text
            else:
                                            
                next_char_index = len(self.current_display_text)
                if next_char_index < len(self.target_display_text):
                    self.current_display_text += self.target_display_text[next_char_index]

                                      
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text
            safe_html = final_html.replace("'", "\\'")

                                                     
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

        else:
                                  
                                      
            if getattr(self, 'is_typing', False):
                self.is_typing = False
                self.last_text_finish_time = datetime.datetime.now()
                safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
                final_html = self.current_context_html + safe_text
                safe_html = final_html.replace("'", "\\'")
                                     
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")

                                 
    def execute_tag(self, tag):
                        
        if tag.lower().startswith('set_name_'):
            new_name = tag[9:].strip()                       
            if new_name:
                llm_brain.config["player_name"] = new_name
                llm_brain.save_config()
                print(f"\n📝 [羁绊铭记]: 已将你的称呼更新为：{new_name}")

                                     
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(她在心里默默记下了你的名字：{new_name})</i></span><br>"
                self.current_context_html += bubble_html
            return

                                 
        if tag.lower().startswith('move_to_'):
            new_loc = tag[8:].strip()                      
            if new_loc:
                                                            
                                                   
                                                            
                          
                                       
                                  
                                                              
                if new_loc not in map_manager.map_instance.flat_locations:
                    map_manager.map_instance.register_dynamic_location(
                        new_loc,
                        lore=f"{new_loc}：这是在互动过程中最近抵达并确认存在的新地点，目前仍缺少正式地图记录。"
                    )
                    print(f"📍 [动态地点建档]: 已自动为新地点【{new_loc}】建立地图档案。")
                          
                llm_brain.config["current_location"] = new_loc
                llm_brain.save_config()
                print(f"\n🚶‍♀️ [步履回响]: 伴随着轻微的脚步声，她离开了原地，朝着【{new_loc}】走去。")

                                     
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(她改变了位置，现在来到了：{new_loc}...)</i></span><br>"
                self.current_context_html += bubble_html

                                     
                                    
                sys_bubble_html = f"<span style='color:#3498db; font-weight:bold; font-size: var(--main-font-size);'>🚶‍♀️ 她似乎有了新的去意，正朝着【{new_loc}】走去...</span>"
                self.show_system_notification(sys_bubble_html, 4000)
            return

                                 
        if tag.lower().startswith('sys_chapter_up'):
            current_chap = llm_brain.config.get("current_chapter", 1)
                           
            if current_chap < 5:
                next_chap = current_chap + 1
                llm_brain.config["current_chapter"] = next_chap
                llm_brain.save_config()

                print(f"\n🌌 [命运回响]:剧本弧光完成，命运齿轮转动，已自动推进至【第 {next_chap} 章】的推演节点。")

                                             
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(命运的篇章已翻过，进入：第 {next_chap} 章...)</i></span><br>"
                self.current_context_html += bubble_html

                                     
                sys_bubble_html = f"<span style='color:#6031e2; font-weight:bold; font-size: var(--main-font-size);'> 🌌 命运的齿轮转动，已自动进入第 {next_chap} 阶段...</span>"
                self.show_system_notification(sys_bubble_html, 4000)
            return

                          
        if tag.startswith('intimacy_'):
            try:
                                                
                val_str = tag.split('_', 1)[1]
                change_val = int(val_str)
                current_int = llm_brain.config.get("intimacy", 0)
                                      
                new_int = max(-100, min(100, current_int + change_val))

                llm_brain.config["intimacy"] = new_int
                llm_brain.save_config()

                                  
                symbol = "+" if change_val >= 0 else ""
                print(f"💖 [关系动态]: 亲密度 {symbol}{change_val} (当前: {new_int}/100)")

                color = "#ffb6c1" if change_val >= 0 else "#6031e2"
                                                                 
                                            
                intimacy_html = f"<span style='color:{color}; font-size: var(--sub-font-size);'><i>[亲密度 {symbol}{change_val}]</i></span><br>"
                self.current_context_html += intimacy_html
            except Exception as e:
                pass

                    
        if tag.startswith('hair_'):
            hair_style = tag.split('_', 1)[1]
            try:
                                      
                params = outfit_manager.get_outfit_params(outfit_manager._current_outfit, hair_style)
                for param_id, val in params.items():
                    self.set_parameter(param_id, val)
                                    
                current_period = getattr(self, "current_time_period", "unknown")
                if current_period != "unknown":
                    self.persist_current_outfit_state(current_period)
            except Exception as e:
                pass

        elif tag.startswith('wear_'):
            outfit_name = tag.split('_', 1)[1]
            try:
                params = outfit_manager.get_outfit_params(outfit_name)
                for param_id, val in params.items():
                    self.set_parameter(param_id, val)

                                                       
                self.manual_outfit_lock = True
                                   
                current_period = getattr(self, "current_time_period", "unknown")
                if current_period != "unknown":
                    self.persist_current_outfit_state(current_period)
            except Exception as e:
                pass


        elif tag.startswith('mood_'):
            mood_name = tag.split('_', 1)[1]
                                                   
                                                    
                                       

                               
            if getattr(self, 'is_story_mode', False):
                print(f"🎬 [物理引擎]: 罗玛莎情绪切换 -> {mood_name}")

            try:
                idx = motion_manager.get_motion_index(mood_name)
                if idx is not None:
                    self.current_idle_motion = idx
                                                            
                                                         
                    self.set_idle_motion(idx)
                                         
                    if mood_name in ['neutral', 'wait', 'wait_haji']:
                        self.is_current_mood_static = True
                    else:
                        self.is_current_mood_static = False
                                                                 
            except Exception as e:
                pass



        elif tag.startswith('act_'):
            now_ts = time.monotonic()
            if tag == self.last_act_tag and (now_ts - self.last_act_time) < 1.2:
                return
            self.last_act_tag = tag
            self.last_act_time = now_ts
            action_name = tag.split('_', 1)[1]

                               
            if getattr(self, 'is_story_mode', False):
                print(f"🎬 [物理引擎]: 罗玛莎触发瞬间动作 -> {action_name}")

                           
            if action_name == 'taol_fall':
                print("\n💦 [突发状况]: 浴巾好像松开了！她慌乱地试图遮掩...")
                self.taol_recover_timer.start(8000)                   
            try:
                idx = motion_manager.get_motion_index(action_name)
                if idx is not None:
                    self.trigger_motion('BaseMotions', idx)
                                                                  
            except Exception as e:
                pass

    def flush_pending_tags(self):

        for tag in self.pending_tags:
            self.execute_tag(tag)
        self.pending_tags.clear()

                                    
                                          
                              
                                                           
                                               

    def on_speech_finished(self):

                                          
        self.browser.page().runJavaScript(
            "if(typeof window.releaseRomashaMotion === 'function') window.releaseRomashaMotion();"
        )
                          
                         
        self.revert_to_idle_motion()

                                    
                                      
        if getattr(self, 'is_current_mood_static', False):
                                                       
            delay_ms = 5000 if llm_brain.config.get("voice_enabled", True) else 8000
            self.static_mood_timer.start(delay_ms)

                                            
        if getattr(self, 'is_story_mode', False) and hasattr(self,
                                                                 'pending_story_options') and self.pending_story_options:
            self.story_window.show_options(self.pending_story_options)
            self.pending_story_options = []

    def trigger_motion(self, group, index):
        self.browser.page().runJavaScript(f"window.playRomashaMotion('{group}', {index});")

                            
    def set_idle_motion(self, index):
        self.browser.page().runJavaScript(f"window.setRomashaIdleMotion({index});")

    def set_parameter(self, param_id, value):
        self.browser.page().runJavaScript(f"window.setRomashaParam('{param_id}', {value});")

    def closeEvent(self, event):
                                            
        self.motion_revert_timer.stop()
        self.typewriter_timer.stop()
        self.notification_timer.stop()
        self.static_mood_timer.stop()
        self.taol_recover_timer.stop()
        self.auto_save_timer.stop()
        self.speech_end_timer.stop()
        self.idle_timer.stop()
        self.time_check_timer.stop()
        self.mouse_timer.stop()

        self.brain_worker.is_cancelled = True
        self.tts_worker.is_cancelled = True
        with self.brain_worker.task_queue.mutex:
            self.brain_worker.task_queue.queue.clear()
        with self.tts_worker.task_queue.mutex:
            self.tts_worker.task_queue.queue.clear()
        self.brain_worker.running = False
        self.tts_worker.running = False
        self.brain_worker.wait()
        self.tts_worker.wait()

        story_manager.save_recent_chat_history(llm_brain.chat_history, max_items=16)
                                                    
        llm_brain.save_config()
        print("\n💾 [羁绊铭记]: 你们之间的距离与视角，已默默留存在了记忆中，期待下次相遇。")

        event.accept()

    def play_voice(self, b64_audio, success, status=""):
        self.is_waiting_for_voice = False         

                                           
        self.flush_pending_tags()

        if success:
            if b64_audio:
                                                                
                self.browser.page().runJavaScript(f"window.playRomashaVoice('{b64_audio}');")
            else:
                                    
                                                         
                self.speech_end_timer.start(2000)
        else:
                      
            if status == "connection_error":
                                          
                llm_brain.config["voice_enabled"] = False
                llm_brain.save_config()

                print("\n💭 [感官适应]: 你决定不再强求听清每一个字，而是专心注视着她。(若想再次尝试倾听，可对她输入 /voice 1)")
                bubble_html = self.current_context_html + "<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(环境有些喧嚣，你注视着她微动的双唇，读懂了她的话语...)</i></span><br>"
            else:
                                  
                bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(你努力分辨着她微弱的声音...)</i></span><br>"

            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")
                             
            duration_ms = max(4000, len(self.final_clean_text) * 250)
            self.speech_end_timer.start(duration_ms)

                                                    
                               
                                                    
        if getattr(self, 'is_story_mode', False):
                                        
                                                      
            unlock_js = """
                if(window.bubbleTimeout) clearTimeout(window.bubbleTimeout); 
                window.bubbleTimeout = setTimeout(() => { document.getElementById('chat-bubble').style.opacity = 0; }, 6000);
                """
            self.browser.page().runJavaScript(unlock_js)
        else:
                                         
                                                     
            self.target_display_text = self.final_clean_text

if __name__ == '__main__':
    # Prevent a second desktop pet instance when the launcher is clicked twice.
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _instance_mutex = kernel32.CreateMutexW(None, False, 'RomashaLive2DDesktopPetSingleton')
    if not _instance_mutex or ctypes.get_last_error() == 183:
        sys.exit(0)
                            
    print("\n" + "=" * 50)

                                   
    now_hour = datetime.datetime.now().hour
    if 5 <= now_hour < 12:
        time_tag, time_desc = "晨光微露", "清晨的微光中"
    elif 12 <= now_hour < 18:
        time_tag, time_desc = "午后静谧", "温暖的午后"
    elif 18 <= now_hour < 23:
        time_tag, time_desc = "夜色温柔", "夜幕降临"
    else:
        time_tag, time_desc = "夜半幽静", "深夜的寂静中"

    print(f"🌸 [{time_tag}] {time_desc}，正在等待她慢慢回过神来...")
    print("   (她似乎有些迷糊，需要几秒的时间才能完全清醒，请耐心等待)")

    try:
                             
                                                         
        current_int = llm_brain.config.get("intimacy", 0)              
        memory_manager.retrieve_relevant_memories("初次相遇的预热", current_int)             
        print(f"✨ [{time_tag}] 她慢慢睁开了眼睛，你看到了她的身影。")
    except Exception as e:
        print(f"⚠️ [{time_tag}] 刚醒来似乎有些头晕，但并不影响你们的相遇: {e}")

    print("=" * 50 + "\n")

    app = QApplication(sys.argv)
    # 【关键】默认"最后一个窗口关闭 -> 程序退出"。她的窗口是 Qt.Tool，
    # 不算正常窗口，所以关掉设置/剧情/改名等任何普通窗口，整个程序会直接
    # 退出（表现就是莫名其妙的闪退）。这里关掉这个行为，程序只住托盘。
    try:
        app.setQuitOnLastWindowClosed(False)
        print("\U0001F6E1\ufe0f [\u7a33\u5b9a\u4fdd\u62a4]: \u5df2\u5173\u95ed\u201c\u6700\u540e\u4e00\u4e2a\u7a97\u53e3\u5173\u95ed\u5c31\u9000\u51fa\u201d\u884c\u4e3a\uff08\u9632\u95ea\u9000\uff09", flush=True)
    except Exception as _e:
        print("[\u7a33\u5b9a\u4fdd\u62a4] \u8bbe\u7f6e\u5931\u8d25: %s" % _e, flush=True)
    romasha = RomashaDesktop()
    try:
        app.aboutToQuit.connect(romasha._graceful_shutdown)
        print("\U0001F6E1\ufe0f [\u9000\u51fa\u4fdd\u62a4]: \u5df2\u6ce8\u518c\u7edf\u4e00\u9000\u51fa\u6e05\u7406\uff08\u9632\u6b62\u9000\u51fa\u65f6\u5d29\u6e83\uff09", flush=True)
    except Exception as _e:
        print("[\u9000\u51fa\u4fdd\u62a4] \u6ce8\u518c\u5931\u8d25: %s" % _e, flush=True)
    sys.exit(app.exec_())
