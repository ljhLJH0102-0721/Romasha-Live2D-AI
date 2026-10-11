                 
import sys
import os
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QListWidget, QPushButton, QLabel,
                             QListWidgetItem, QTabWidget, QSlider, QGroupBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

import motion_manager
import outfit_manager


class MotionTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Romasha 全功能物理调试控制台 (加载中...)")
        self.resize(1200, 800)
        self.is_ready = False

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

                                                    
                         
                                                    
        self.browser = QWebEngineView()
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.browser.page().setBackgroundColor(Qt.lightGray)
        self.browser.titleChanged.connect(self.on_html_signal)

        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'web', 'index.html'))
        self.browser.load(QUrl.fromLocalFile(html_path))
        main_layout.addWidget(self.browser, stretch=2)

                                                    
                                
                                                    
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("font-size: 13px;")
        main_layout.addWidget(self.tabs, stretch=1)

                              
        self.tab_motion = QWidget()
        motion_layout = QVBoxLayout(self.tab_motion)

        motion_label = QLabel("<b>🎮 瞬间/常态动作测试</b><br>点击下方列表立刻播放：")
        motion_layout.addWidget(motion_label)

        self.motion_list = QListWidget()
        self.motion_list.itemClicked.connect(self.on_motion_clicked)
        for act_name, info in motion_manager.MOTIONS.items():
            item = QListWidgetItem(f"[{act_name}] - {info['desc']}")
            item.setData(Qt.UserRole, info['index'])
            self.motion_list.addItem(item)
        motion_layout.addWidget(self.motion_list)

        reset_btn = QPushButton("🔄 恢复默认待机 (talk)")
        reset_btn.clicked.connect(lambda: self.play_motion(motion_manager.get_motion_index('talk')))
        motion_layout.addWidget(reset_btn)

        self.tabs.addTab(self.tab_motion, "🏃 动作")

                              
        self.tab_outfit = QWidget()
        outfit_layout = QVBoxLayout(self.tab_outfit)

              
        outfit_label = QLabel("<b>👗 服装切换 (Outfits)</b>")
        outfit_layout.addWidget(outfit_label)
        self.outfit_list = QListWidget()
        self.outfit_list.itemClicked.connect(self.on_outfit_clicked)
                                
        for outfit_name in outfit_manager.OUTFITS.keys():
            self.outfit_list.addItem(QListWidgetItem(f"[{outfit_name}]"))
        outfit_layout.addWidget(self.outfit_list)

              
        hair_label = QLabel("<b>💇‍♀️ 发型切换 (Hairstyles)</b>")
        outfit_layout.addWidget(hair_label)
        self.hair_list = QListWidget()
        self.hair_list.setFixedHeight(80)             
        self.hair_list.itemClicked.connect(self.on_hair_clicked)
        for hair_name in outfit_manager.HAIRSTYLES.keys():
            self.hair_list.addItem(QListWidgetItem(f"[{hair_name}]"))
        outfit_layout.addWidget(self.hair_list)

        self.tabs.addTab(self.tab_outfit, "👗 换装")

                                
        self.tab_param = QWidget()
        param_layout = QVBoxLayout(self.tab_param)

                           
        cheek_group = QGroupBox("😊 脸红程度 (ParamCheek)")
        cheek_layout = QVBoxLayout()
        self.cheek_slider = QSlider(Qt.Horizontal)
        self.cheek_slider.setRange(0, 100)
        self.cheek_slider.valueChanged.connect(lambda v: self.set_param('ParamCheek', v / 100.0))
        cheek_layout.addWidget(self.cheek_slider)
        cheek_group.setLayout(cheek_layout)
        param_layout.addWidget(cheek_group)

                      
        angry_group = QGroupBox("💢 生气程度 (angry)")
        angry_layout = QVBoxLayout()
        self.angry_slider = QSlider(Qt.Horizontal)
        self.angry_slider.setRange(0, 100)
        self.angry_slider.valueChanged.connect(lambda v: self.set_param('angry', v / 100.0))
        angry_layout.addWidget(self.angry_slider)
        angry_group.setLayout(angry_layout)
        param_layout.addWidget(angry_group)

              
        clear_emotion_btn = QPushButton("😶 一键消除面部余温")
        clear_emotion_btn.setMinimumHeight(40)
        clear_emotion_btn.clicked.connect(self.clear_emotions)
        param_layout.addWidget(clear_emotion_btn)

        param_layout.addStretch()           
        self.tabs.addTab(self.tab_param, "😳 面部参数")

                                                    
    def on_html_signal(self, title):
        if title == "EVENT:READY":
            self.is_ready = True
            self.setWindowTitle("Romasha 物理调试控制台 - ✅ 模型已就绪")
                    
            self.play_motion(motion_manager.get_motion_index('talk'))
            self.apply_outfit('uniform_tight')
            print("✨ 前端引擎加载完毕！")

    def on_motion_clicked(self, item):
        if not self.is_ready: return
        index = item.data(Qt.UserRole)
        act_name = item.text().split(']')[0][1:]
        print(f"▶️ 播放动作: {act_name}")
        self.play_motion(index)

    def on_outfit_clicked(self, item):
        if not self.is_ready: return
        outfit_name = item.text().strip('[]')
        print(f"👗 切换服装: {outfit_name}")
        self.apply_outfit(outfit_name)

    def on_hair_clicked(self, item):
        if not self.is_ready: return
        hair_name = item.text().strip('[]')
        print(f"💇‍♀️ 切换发型: {hair_name}")
                             
        current_outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "uniform_tight"
        params = outfit_manager.get_outfit_params(current_outfit, hair_name)
        for param_id, val in params.items():
            self.set_param(param_id, val)

    def play_motion(self, index):
        self.browser.page().runJavaScript(f"window.playRomashaMotion('BaseMotions', {index});")

    def apply_outfit(self, outfit_name):
        params = outfit_manager.get_outfit_params(outfit_name)
        for param_id, val in params.items():
            self.set_param(param_id, val)

    def set_param(self, param_id, value):
        self.browser.page().runJavaScript(f"window.setRomashaParam('{param_id}', {value});")

    def clear_emotions(self):
        print("🔄 已清除面部情绪")
        self.cheek_slider.setValue(0)
        self.angry_slider.setValue(0)
        self.set_param('ParamCheek', 0.0)
        self.set_param('angry', 0.0)


if __name__ == '__main__':
    print("🚀 启动全功能物理测试台...")
    app = QApplication(sys.argv)
    tester = MotionTester()
    tester.show()
    sys.exit(app.exec_())