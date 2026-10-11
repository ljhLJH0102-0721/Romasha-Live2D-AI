                       
import memory_manager
import sys
import os
import re
import random
import time
import shutil
import gc
import datetime

                                            
                          
                                            
if os.path.exists("./romasha_test_sandbox_db"):
    try:
        shutil.rmtree("./romasha_test_sandbox_db")
        print("🧹 [系统初始化] 启动前清理：已成功销毁上一次残留的沙盒数据！")
    except Exception as e:
        print(f"⚠️ [系统初始化] 清理历史沙盒失败: {e}")

from PyQt5.QtCore import Qt, QUrl, QTimer, QSize, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit,
                             QHBoxLayout, QPushButton, QTabWidget, QTextEdit,
                             QLabel, QListWidget, QGroupBox, QMessageBox, QDialog,
                             QSlider, QSpinBox, QCheckBox, QSplitter, QComboBox,
                             QScrollArea, QPlainTextEdit, QSizePolicy, QGridLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QTextCursor              
from openai import OpenAI                

                                            
                  
                                            
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

          
import outfit_manager
import motion_manager
import llm_brain
import world_info
import story_manager

                                            
                    
                                            
sandbox_client = memory_manager.chromadb.PersistentClient(path="./romasha_test_sandbox_db")
sandbox_ef = memory_manager.embedding_functions.DefaultEmbeddingFunction()
sandbox_collection = sandbox_client.get_or_create_collection(
    name="sandbox_memories", embedding_function=sandbox_ef
)


def mocked_save_config():
    pass


def mocked_add_memory(user_text, ai_text):
    if not user_text or not ai_text: return
    timestamp = str(int(time.time() * 1000))
    memory_content = f"[沙盒录入] 我：{user_text}\n回应：{ai_text}"
    sandbox_collection.add(
        documents=[memory_content],
        metadatas=[{"timestamp": timestamp}],
        ids=[f"sandbox_{timestamp}"]
    )


memory_manager.add_memory = mocked_add_memory


                                            
              
                                            
class VirtualTrackPad(QLabel):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setStyleSheet("background-color: #1e1e1e; color: #00ff00; border: 2px solid #444; border-radius: 8px;")
        self.setText("🖱️ 虚拟触控板\n(在此区域内滑动测试跟随)")
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(150)
        self.is_tracking_enabled = True

    def mouseMoveEvent(self, event):
        if not self.is_tracking_enabled: return
        x, y = event.x(), event.y()
        mapped_x = int((x / self.width()) * 1920)
        mapped_y = int((y / self.height()) * 1080)
        self.parent_window.exec_js(f"window.updateGlobalMouse({mapped_x}, {mapped_y});")

    def leaveEvent(self, event):
        if not self.is_tracking_enabled: return
        self.parent_window.exec_js("window.updateGlobalMouse(960, 540);")


                                            
                               
                                            
class ApiTestWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_type, base_url, api_key, model, system_prompt, user_text):
        super().__init__()
        self.api_type = api_type
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.user_text = user_text

    def run(self):
        try:
                                                         
            messages = []
            if self.system_prompt.strip():
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": self.user_text})
            full_reply = ""

            if self.api_type == "openai":
                client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=60.0)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.7
                )
                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            full_reply += delta
                            self.chunk_received.emit(delta)
                self.finished.emit(full_reply)

            elif self.api_type == "ollama":
                import requests
                import json

                url = self.base_url.rstrip('/')
                if not url.endswith('/api/chat'):
                    url = f"{url}/api/chat"

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.7}
                }
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                with requests.post(url, json=payload, headers=headers, stream=True, timeout=60.0) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                delta = data["message"]["content"]
                                full_reply += delta
                                self.chunk_received.emit(delta)
                self.finished.emit(full_reply)

        except Exception as e:
            self.error.emit(str(e))


                                            
       
                                            
class SystemEngineTester(QMainWindow):
    def __init__(self):
        super().__init__()

        self.target_display_text = ""
        self.current_display_text = ""
                               
        self.current_context_html = "<span style='color:#ccc;'><i>(系统核心已唤醒...)</i></span><br>"
        self.processed_tags = set()

                         
        self.tag_execution_queue = []
        self.tag_timer = QTimer(self)
        self.tag_timer.timeout.connect(self.process_next_tag)
        self.tag_timer.start(100)                     

        self.script_queue = []
        self.is_script_running = False

                                                    
                    
                                                    
                                          
                                                            
                            
        self.full_future_story_cache = None

        self.init_ui()

        self.typewriter_timer = QTimer(self)
        self.current_idle_motion = motion_manager.get_motion_index('talk')
        self.motion_revert_timer = QTimer(self)
        self.motion_revert_timer.setSingleShot(True)
        self.motion_revert_timer.timeout.connect(self.revert_to_idle_motion)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)
        self.typewriter_timer.start(40)

                             
        self.static_mood_timer = QTimer(self)
        self.static_mood_timer.setSingleShot(True)
        self.static_mood_timer.timeout.connect(self.resolve_static_mood_mock)

    def init_ui(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.resize(1600, 1000)
        self.setWindowTitle("Romasha 终极系统测试控制台 V4.0 (高分屏自适应/防冲突版) 🛠️")

                               
        self.setStyleSheet("""
            * { font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 14px; }
            QPushButton { padding: 8px 12px; border-radius: 4px; background-color: #ecf0f1; border: 1px solid #bdc3c7; }
            QPushButton:hover { background-color: #d5dbdb; }
            QGroupBox { font-weight: bold; padding-top: 15px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #2c3e50; }
        """)

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

                           
        self.browser = QWebEngineView()
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.browser.page().setBackgroundColor(Qt.transparent)
                       
        self.browser.titleChanged.connect(self.on_html_signal)
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'web', 'index.html'))
        self.browser.load(QUrl.fromLocalFile(html_path))
        main_layout.addWidget(self.browser, stretch=7)

                            
        right_panel = QSplitter(Qt.Vertical)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 10px 15px; font-weight: bold; }")
        self.setup_tabs()
        right_panel.addWidget(self.tabs)

               
        log_group = QGroupBox("🖥️ 底层 JS Interface 实时监听器")
        log_layout = QVBoxLayout()
        self.param_log = QListWidget()
        self.param_log.setStyleSheet(
            "background-color: #0d0d0d; color: #4af626; font-family: Consolas; font-size: 13px; padding: 5px;")

        btn_clear_log = QPushButton("🧹 清空指令日志")
        btn_clear_log.clicked.connect(self.param_log.clear)

        log_layout.addWidget(self.param_log)
        log_layout.addWidget(btn_clear_log)
        log_group.setLayout(log_layout)
        right_panel.addWidget(log_group)

        right_panel.setSizes([750, 250])
        main_layout.addWidget(right_panel, stretch=6)

    def setup_tabs(self):
        self.init_stream_tab()
        self.init_matrix_tab()
        self.init_time_tab()
        self.init_vision_tab()
        self.init_sequencer_tab()
        self.init_memory_tab()
        self.init_api_sandbox_tab()

                                                
                        
                                                
    def init_stream_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<b>🏷️ 标签与弹幕构建 (底层加入排队机制，绝不吞指令)：</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        def create_tag_group(title, prefix, item_list):
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(f"<b>{title}:</b>"))
            cb = QComboBox()
            cb.addItem(f"--- 选择 {title} ---")
            for item in item_list: cb.addItem(item)
            cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn = QPushButton("插入 ⬇️")
            btn.clicked.connect(lambda: self.inject_tag_to_input(prefix, cb.currentText()))
            hbox.addWidget(cb, stretch=2);
            hbox.addWidget(btn, stretch=1)
            scroll_layout.addLayout(hbox)

        create_tag_group("常驻情绪", "mood", ["talk", "talk_alc", "talk_ero", "neutral", "wait", "wait_haji"])
        create_tag_group("瞬间动作", "act", list(motion_manager.MOTIONS.keys()))
        create_tag_group("强制换装", "wear", list(outfit_manager.OUTFITS.keys()))
        create_tag_group("强制发型", "hair", list(outfit_manager.HAIRSTYLES.keys()))

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        self.mock_input = QTextEdit()
        self.mock_input.setPlaceholderText("例: [intimacy_+1][wear_swimsuit][act_smallamazing] 笨蛋...你干嘛！")
        self.mock_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.mock_input, stretch=1)

        hbox_bottom = QHBoxLayout()
        self.chk_network = QCheckBox("🐌 弱网环境模拟 (测试气泡防抖)")
        hbox_bottom.addWidget(self.chk_network)

        btn_send = QPushButton("🚀 压入渲染防冲突队列")
        btn_send.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        btn_send.clicked.connect(self.simulate_llm_stream)
        hbox_bottom.addWidget(btn_send)
        layout.addLayout(hbox_bottom)

        self.tabs.addTab(tab, "📡 串流弹幕")

                                                
                       
                                                
    def _get_slider_config(self, param_id):
        integer_params = ['hearchange', 'buraONFOFF', 'pantsuONFOFF', 'minzokucloth',
                            'bunny', 'mizugiONOFF', 'bath_taol_ON', 'taolONOFF',
                            'gaze_ON', 'underhear', 'nipplepierce']
        if param_id == 'formchange': return (-1, 1, 1)
        elif param_id in integer_params: return (0, 30, 1)
        elif 'Angle' in param_id or 'move' in param_id.lower() or 'yure' in param_id.lower() \
                or param_id.endswith('X') or param_id.endswith('Y') or param_id.endswith('Z') \
                or 'X2' in param_id or param_id in ['ParamEyeBallX', 'ParamEyeBallY']:
            return (-300, 300, 10)
        elif param_id in ['ParamBreath', 'eyeOpenL', 'eyeOpenR', 'ParamMouthOpenY']:
            return (0, 10, 10)
        else: return (0, 10, 10)

    def init_matrix_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("<b>🛠️ Live2D 底层全变量直控矩阵 (116项参数全量同步)：</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        matrix_content = QWidget()
        main_vbox = QVBoxLayout(matrix_content)

        self.param_sliders = {}
        self.param_dividers = {}

        romasha_params_dict = {
            "👗 パーツの切り替え (部件切换)": [
                ("formchange", "换装"), ("negligeeONOFF", "睡袍换装"), ("negligeeinnerONOFF", "睡袍内衣切换"),
                ("leotard_ON", "紧身衣换装"), ("mizugiONOFF", "泳装换装"), ("mizugiSUKE", "泳装湿透表现"),
                ("minzokucloth", "民族服装换装"), ("minzoku_bust_ON", "民族胸布换装"), ("minzoku_westONOFF", "民族腰布开关"),
                ("FudeONOFF", "兜帽开关"), ("fundoshi_ONOFF", "兜裆布开关"), ("bunny", "兔女郎套装换装"),
                ("bunnycuffsONOFF", "兔女郎袖口开关"), ("bunny_bust_porori", "兔女郎胸部掀起"), ("bunnybodyONOFF", "兔女郎身体开关"),
                ("bunnyamiamiONOFF", "兔女郎网袜换装"), ("bunnyneckONOFF", "兔女郎领结开关"), ("bunnyearONOFF", "兔女郎耳朵开关"),
                ("bath_taol_ON", "浴巾切换"), ("bath_taol_fall", "浴巾滑落"), ("taolONOFF", "毛巾切换"),
                ("gaze_ON", "毛巾变更"), ("taolnure", "毛巾湿透"), ("underhear", "阴毛切换"),
                ("milk_on", "母乳切换"), ("milk_move", "母乳流动"), ("nipplepierce", "乳环切换"),
                ("bigbust", "巨乳切换"), ("tatuONOFF", "淫纹切换"), ("tatuCHIKACHIKA", "淫纹闪烁"),
                ("pantsuONFOFF", "内裤切换"), ("seieki_ON", "精液显示"), ("buraONFOFF", "胸罩切换")
            ],
            "😊 表情 (面部与神态)": [
                ("ParamAngleX", "脸部角度 X"), ("ParamAngleY", "脸部角度 Y"), ("ParamAngleZ", "脸部角度 Z"),
                ("highlightONOFF", "高光开关"), ("highlightR_yureX", "右高光摇晃X"), ("highlightR_yureY", "右高光摇晃Y"),
                ("matugeL_yure", "左睫毛摇晃"), ("matugeR_yure", "右睫毛摇晃"), ("highlightL_yureX", "左高光摇晃X"),
                ("highlightL_yureY", "左高光摇晃Y"), ("eyeOpenL", "左眼 开闭"), ("eyeOpenR", "右眼 开闭"),
                ("ParamEyeBallX", "眼球 X"), ("ParamEyeBallY", "眼球 Y"), ("hitomi_from", "瞳孔变形"),
                ("smile_eye", "喜悦眼表现"), ("ParamBrowLAngle", "左眉 角度"), ("ParamBrowRAngle", "右眉 角度"),
                ("ParamBrowLForm", "左眉 变形"), ("ParamBrowRForm", "右眉 变形"), ("ParamEyeLSmile", "左眼变形"),
                ("ParamEyeRSmile", "右眼变形"), ("mouth_scale", "嘴巴缩放"), ("ParamMouthOpenY", "嘴巴 开闭"),
                ("ParamMouthForm", "嘴巴 变形"), ("ParamMouthForm2", "嘴巴变形2"), ("ParamCheek", "害羞"),
                ("ase", "汗"), ("namida", "泪"), ("heart_eye_ONOFF", "爱心眼"), ("eye_guruguru", "圈圈眼"),
                ("cheek_D_ON", "Q版腮红"), ("cheek_on", "腮红"), ("angry", "生气"),
                ("blessONOFF", "吐息显示"), ("bless_move", "呼吸移动")
            ],
            "💪 腕差分 (手臂姿势切换)": [
                ("elboR_ONOFF", "右肘开关"), ("elboL_ONOFF", "左肘开关"), ("armL_top_ONOFF", "左上臂开关"),
                ("nadenadeleft", "抚摸放下手臂开关"), ("nadehand_angle", "抚摸手的旋转"), ("nadenadeleft_angle", "抚摸手臂的旋转"),
                ("nadenadeleft_mage", "抚摸手的弯曲"), ("arm_device_ONOFF", "设备手臂开关"), ("arm_device_allangle", "设备手臂整体旋转"),
                ("hand_device_angle", "设备手腕旋转"), ("hand_device_yure_hitosashi", "设备食指摇晃"), ("hand_device_nigiri", "设备手指握紧"),
                ("arm_device_angle", "设备手肘旋转"), ("arm_device_yure", "设备手臂摇晃"), ("attentionright", "注意手臂开关"),
                ("attention_angle", "注意手臂旋转"), ("attention_hand_angle", "注意手的旋转"), ("attention_hand_mage", "注意手的弯曲"),
                ("attention_yubi_mage", "注意食指的弯曲"), ("amazingrightONFOFF", "惊讶手臂开关"), ("amazing_arm_angle", "惊讶手臂旋转"),
                ("amazing_hand_angle", "惊讶手的旋转"), ("amazing_hand_mage", "惊讶手的弯曲")
            ],
            "🌬️ パーツの揺れ (物理与抖动)": [
                ("hearchange", "发型切换"), ("aho_yure", "呆毛摇晃"), ("ribon_yure", "蝴蝶结摇晃"),
                ("tie_yure", "领带摇晃"), ("skirt_yure", "裙子摇晃"), ("minzoku_bigbust_yure", "民族胸布巨乳摇晃"),
                ("minzoku_bust_R", "民族胸布摇晃R"), ("minzoku_bust_L", "民族胸布摇晃L"), ("minzoku_hudo_yure", "民族兜帽摇晃"),
                ("neglige_ribon_yure", "睡袍蝴蝶结摇晃"), ("negulige_skirt_yure", "睡袍裙子摇晃"),
                ("ParamHairFront2", "头发摇晃 前1"), ("ParamHairFront3", "头发摇晃 前2"), ("ParamHairFront4", "头发摇晃 前3"),
                ("ParamHairFront5", "头发摇晃 前4"), ("ParamHairFront6", "头发摇晃 前5"), ("ParamHairFront7", "头发摇晃 前6"),
                ("ParamHairFront8", "头发摇晃 前7"), ("ParamHairFront9", "头发摇晃 前8"), ("ParamHairBack", "头发摇晃 后"),
                ("ParamHairSide", "头发摇晃 侧"), ("ParamHairSide2", "头发摇晃 侧2"), ("mitsuami_yure", "麻花辫摇晃"),
                ("sidetale_yure", "头发摇晃 侧马尾"), ("pony_tale", "头发摇晃 马尾辫"), ("longhear_yure", "头发摇晃 长发")
            ],
            "🏃 体の動き (身体躯干移动)": [
                ("all", "整体调整"), ("allmoveX", "整体移动X"), ("allmoveY", "整体移动Y"),
                ("bust_bura__X", "胸罩胸部动作X"), ("bust_bura_Y", "胸罩胸部动作Y"), ("bustX", "胸部动作X"), ("bust_Y", "胸部动作Y"),
                ("bigbustX", "巨乳动作X"), ("bigbustY", "巨乳动作Y"), ("ParamBodyAngleX", "身体旋转 X"),
                ("ParamBodyAngleX2", "身体旋转 X2"), ("ParamBodyAngleY", "身体旋转 Y"), ("ParamBodyAngleZ", "身体旋转 Z"),
                ("legR_angle", "右腿旋转"), ("legL_angle", "左腿旋转"), ("handR_move", "右手动作"),
                ("handR_angle", "右手旋转"), ("armR_angle", "右臂旋转"), ("elboR_angle", "右肘旋转"),
                ("elboR_mage", "右肘弯曲"), ("armR_mage", "右臂弯曲"), ("handL_move", "左手动作"),
                ("handL_angle", "左手旋转"), ("elboL_mage", "左肘弯曲"), ("arm_L_mageX", "左臂弯曲X"),
                ("arm_L_mageY", "左臂弯曲Y"), ("armL_angle", "左臂旋转"), ("skirt_makure", "掀裙子切换"),
                ("skirt_castoff", "裙子消失"), ("skiry_custm_ON", "改造裙子显示"), ("mekure", "掀裙子"),
                ("ParamBreath", "呼吸")
            ]
        }

        for group_name, params_list in romasha_params_dict.items():
            group_box = QGroupBox(group_name)
            grid = QGridLayout()
            row, col = 0, 0

            for param_id, param_name_cn in params_list:
                lbl = QLabel(f"{param_name_cn}\n({param_id})")
                lbl.setStyleSheet("font-size: 11px; color: #444;")
                slider = QSlider(Qt.Horizontal)
                s_min, s_max, s_div = self._get_slider_config(param_id)
                slider.setRange(s_min, s_max)

                self.param_sliders[param_id] = slider
                self.param_dividers[param_id] = s_div

                val_lbl = QLabel("0.0")
                val_lbl.setFixedWidth(35)
                val_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #d35400;")

                slider.valueChanged.connect(lambda v, p=param_id, l=val_lbl: self.matrix_param_changed(p, v, l))

                grid.addWidget(lbl, row, col * 3)
                grid.addWidget(slider, row, col * 3 + 1)
                grid.addWidget(val_lbl, row, col * 3 + 2)

                col += 1
                if col > 1:
                    col = 0
                    row += 1

            group_box.setLayout(grid)
            main_vbox.addWidget(group_box)

        scroll.setWidget(matrix_content)
        layout.addWidget(scroll, stretch=1)

        btn_reset = QPushButton("🔄 恢复当前服装/状态的默认参数")
        btn_reset.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        btn_reset.clicked.connect(self.reset_matrix_params)
        layout.addWidget(btn_reset)

        self.tabs.addTab(tab, "🛠️ 全量参数矩阵")

                                                
                         
                                                
    def init_time_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

                                                            
                                    
                                                            
        group_custom = QGroupBox("⏳ 精确时空跃迁 (测试生物钟延迟换装)")
        vbox1 = QVBoxLayout()

        hbox = QHBoxLayout()
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(6)

        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(15)

        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(12)

        btn_jump = QPushButton("🚀 强制跃迁")
        btn_jump.clicked.connect(
            lambda: self.simulate_time(
                self.month_spin.value(),
                self.day_spin.value(),
                self.hour_spin.value()
            )
        )

        hbox.addWidget(QLabel("月:"))
        hbox.addWidget(self.month_spin)
        hbox.addWidget(QLabel("日:"))
        hbox.addWidget(self.day_spin)
        hbox.addWidget(QLabel("时:"))
        hbox.addWidget(self.hour_spin)
        hbox.addWidget(btn_jump)
        vbox1.addLayout(hbox)

        grid_presets = QHBoxLayout()
        presets = [
            ("早晨 08:00\n(日常紧身)", 6, 15, 8),
            ("傍晚 19:00\n(连衣制服)", 6, 15, 19),
            ("深夜 23:00\n(睡衣/洗澡)", 6, 15, 23),
            ("冬季节日\n(圣诞节)", 12, 25, 14)
        ]
        for name, m, d, h in presets:
            btn = QPushButton(name)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, m=m, d=d, h=h: self.simulate_time(m, d, h))
            grid_presets.addWidget(btn)
        vbox1.addLayout(grid_presets)

        group_custom.setLayout(vbox1)
        layout.addWidget(group_custom, stretch=1)

                                                            
                        
                                                            
        group_intimacy = QGroupBox("💖 虚拟亲密度注入 (影响高权限判定)")
        vbox2 = QVBoxLayout()

        self.lbl_intimacy = QLabel(f"当前沙盒模拟好感度: {llm_brain.config.get('intimacy', 0)} / 100")
        self.lbl_intimacy.setStyleSheet("font-weight: bold; color: #d35400;")
        vbox2.addWidget(self.lbl_intimacy)

        self.slider_intimacy = QSlider(Qt.Horizontal)
        self.slider_intimacy.setRange(-100, 100)
        self.slider_intimacy.setValue(llm_brain.config.get("intimacy", 0))
        self.slider_intimacy.valueChanged.connect(self.update_sandbox_intimacy)
        vbox2.addWidget(self.slider_intimacy)

        group_intimacy.setLayout(vbox2)
        layout.addWidget(group_intimacy)

                                                            
                                      
                                                            
        group_story = QGroupBox("📚 命运编年史 / 章节跃迁 / 未来认知授权")
        story_layout = QVBoxLayout()

        self.lbl_story_state = QLabel("")
        self.lbl_story_state.setStyleSheet("font-weight: bold; color: #6031e2;")
        story_layout.addWidget(self.lbl_story_state)

        story_hbox = QHBoxLayout()
        self.chapter_spin = QSpinBox()
                                       
        self.chapter_spin.setRange(1, 20)
        self.chapter_spin.setValue(llm_brain.config.get("current_chapter", 1))

        btn_set_chapter = QPushButton("🌀 时光跳跃到该章节")
        btn_set_chapter.clicked.connect(self.jump_story_chapter_from_ui)

        btn_prev_chapter = QPushButton("⏪ 时光回溯 -1章")
        btn_prev_chapter.clicked.connect(lambda: self.shift_story_chapter(-1))

        btn_next_chapter = QPushButton("⏩ 时光飞逝 +1章")
        btn_next_chapter.clicked.connect(lambda: self.shift_story_chapter(1))

        story_hbox.addWidget(QLabel("目标章节:"))
        story_hbox.addWidget(self.chapter_spin)
        story_hbox.addWidget(btn_set_chapter)
        story_hbox.addWidget(btn_prev_chapter)
        story_hbox.addWidget(btn_next_chapter)
        story_layout.addLayout(story_hbox)

        self.chk_reveal_full_story = QCheckBox(
            "📖 本次测试中授权她知晓未来全部剧情（注入 final_aligned_story_chronicle.txt 全文）")
        self.chk_reveal_full_story.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.chk_reveal_full_story.stateChanged.connect(self.on_future_story_toggle)
        story_layout.addWidget(self.chk_reveal_full_story)

        btn_preview_chronicle = QPushButton("🔍 预览当前注入的章节上下文 / 完整编年史状态")
        btn_preview_chronicle.clicked.connect(self.preview_story_injection)
        story_layout.addWidget(btn_preview_chronicle)

        group_story.setLayout(story_layout)
        layout.addWidget(group_story)

        self.tabs.addTab(tab, "⏳ 时空状态")

                                     
        self.refresh_story_state_label()

                                                
                      
                                                
    def init_vision_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_vision = QGroupBox("👁️ 视线追踪硬件阻断")
        vbox1 = QVBoxLayout()
        hbox = QHBoxLayout()
        self.trackpad = VirtualTrackPad(self)
        hbox.addWidget(self.trackpad, stretch=2)

        vbox_btns = QVBoxLayout()
        self.btn_toggle_track = QPushButton("✅ 追踪已开启 (点击阻断)")
        self.btn_toggle_track.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_toggle_track.clicked.connect(self.toggle_vision_tracking)
        vbox_btns.addWidget(self.btn_toggle_track, stretch=1)

        btn_sleep = QPushButton("💤 强制触发挂机断线\n(+ wait_haji 动作)")
        btn_sleep.clicked.connect(self.trigger_vision_sleep)
        vbox_btns.addWidget(btn_sleep, stretch=1)
        hbox.addLayout(vbox_btns, stretch=1)

        vbox1.addLayout(hbox)
        group_vision.setLayout(vbox1)
        layout.addWidget(group_vision, stretch=1)

        group_touch = QGroupBox("👆 碰撞盒气泡反馈测试")
        grid = QGridLayout()
        parts = [
            ("摸头部", "head"), ("戳脸颊", "face"), ("碰胸部", "bust"),
            ("搂腰部", "belly"), ("碰臀部", "hip"), ("隐私区", "crotch"), ("牵右手", "hand_right")
        ]
        row, col = 0, 0
        for name_cn, tag in parts:
            btn = QPushButton(name_cn)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda chk, t=tag, n=name_cn: self.simulate_touch(t, n))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0; row += 1

        group_touch.setLayout(grid)
        layout.addWidget(group_touch, stretch=1)

        self.tabs.addTab(tab, "🖱️ 互动防线")

                                                
                      
                                                
    def init_sequencer_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        lbl_info = QLabel("<b>🎬 导演剧本模式：编写组合帧动作自动播放</b>")
        layout.addWidget(lbl_info)

        self.script_input = QPlainTextEdit()
        default_script = (
            "WEAR: swimsuit\nDELAY: 500\nACT: smallamazing\n"
            "BUBBLE: 咦...衣服怎么突然...\nDELAY: 2000\n"
            "ACT: hatujo\nBUBBLE: 笨、笨蛋！不许一直盯着看！"
        )
        self.script_input.setPlainText(default_script)
        layout.addWidget(self.script_input)

        hbox = QHBoxLayout()
        btn_run = QPushButton("▶️ 开始推演")
        btn_run.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;")
        btn_run.clicked.connect(self.run_script)

        btn_stop = QPushButton("⏹️ 强行拉闸阻断")
        btn_stop.setStyleSheet("background-color: #c0392b; color: white;")
        btn_stop.clicked.connect(self.trigger_interrupt)

        hbox.addWidget(btn_run); hbox.addWidget(btn_stop)
        layout.addLayout(hbox)
        self.tabs.addTab(tab, "🎬 剧本推演")

                                                
                    
                                                
    def init_memory_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hbox_controls = QHBoxLayout()
        btn_read_real = QPushButton("📖 嗅探真实海马体")
        btn_read_real.setStyleSheet("background-color: #2c3e50; color: white;")
        btn_read_real.clicked.connect(lambda: self.refresh_memory(mode="real"))

        btn_copy_real = QPushButton("📥 拷贝真实记忆至沙盒")
        btn_copy_real.setStyleSheet("background-color: #27ae60; color: white;")
        btn_copy_real.clicked.connect(self.copy_real_memory_to_sandbox)

        btn_read_sandbox = QPushButton("🧪 嗅探沙盒记忆区")
        btn_read_sandbox.setStyleSheet("background-color: #d35400; color: white;")
        btn_read_sandbox.clicked.connect(lambda: self.refresh_memory(mode="sandbox"))

        hbox_controls.addWidget(btn_read_real)
        hbox_controls.addWidget(btn_copy_real)
        hbox_controls.addWidget(btn_read_sandbox)
        layout.addLayout(hbox_controls)

        self.mem_list = QListWidget()
        layout.addWidget(self.mem_list)

        hbox_surgery = QHBoxLayout()
        self.mem_id_input = QTextEdit()
        self.mem_id_input.setPlaceholderText("输入要抹除的沙盒记忆 ID (例: sandbox_168...)...")
        self.mem_id_input.setFixedHeight(40)
        btn_del_mem = QPushButton("🗡️ 剔除此段沙盒记忆")
        btn_del_mem.clicked.connect(self.delete_specific_memory)
        hbox_surgery.addWidget(self.mem_id_input, stretch=2)
        hbox_surgery.addWidget(btn_del_mem, stretch=1)
        layout.addLayout(hbox_surgery)

        btn_clear_sandbox = QPushButton("🧨 全面核平沙盒记忆库")
        btn_clear_sandbox.clicked.connect(self.clear_sandbox)
        layout.addWidget(btn_clear_sandbox)

        self.tabs.addTab(tab, "🧠 记忆手术")

                                                
                                
                                                
    def init_api_sandbox_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<b>📡 动态 Prompt 组装嗅探器与 API 实机测试：</b>"))

        btn_view_lore = QPushButton("📖 独立窗口查看世界观底层封装数据")
        btn_view_lore.clicked.connect(self.show_lore_window)
        layout.addWidget(btn_view_lore)

        group_api = QGroupBox("🔑 真实 API 连通性测试 (读取 llm_brain 配置)")
        api_layout = QGridLayout()

        self.input_api_type = QComboBox()
        self.input_api_type.addItems(["openai", "ollama"])
        self.input_api_type.setCurrentText(llm_brain.config.get("api_type", "openai"))

        self.input_api_url = QLineEdit()
        self.input_api_url.setText(llm_brain.config.get("base_url", "https://api.openai.com/v1"))
        self.input_api_key = QLineEdit()
        self.input_api_key.setText(llm_brain.config.get("api_key", ""))
        self.input_api_key.setEchoMode(QLineEdit.Password)
        self.input_api_model = QLineEdit()
        self.input_api_model.setText(llm_brain.config.get("target_model", "gpt-3.5-turbo"))

        api_layout.addWidget(QLabel("API Type:"), 0, 0)
        api_layout.addWidget(self.input_api_type, 0, 1)
        api_layout.addWidget(QLabel("Base URL:"), 1, 0)
        api_layout.addWidget(self.input_api_url, 1, 1)
        api_layout.addWidget(QLabel("API Key:"), 2, 0)
        api_layout.addWidget(self.input_api_key, 2, 1)
        api_layout.addWidget(QLabel("Target Model:"), 3, 0)
        api_layout.addWidget(self.input_api_model, 3, 1)

        group_api.setLayout(api_layout)
        layout.addWidget(group_api)

        self.prompts_data = {
            "💬 普通对话": "你好呀，Romasha。",
            "🤚 触摸：摸头": "*你温柔地摸了摸她的头*",
            "🤚 触摸：戳脸颊": "*你轻轻戳了戳她的脸颊*",
            "🤚 触摸：碰胸部": "*你不小心碰到了她的胸部*",
            "🤚 触摸：搂腰": "*你搂住了她的腰*",
            "🤚 触摸：碰臀部": "*你不小心碰到了她的臀部*",
            "🤚 触摸：碰隐私部位": "*你不小心碰到了她的隐私部位*",
            "🤚 触摸：碰腿": "*你碰到了她的腿*",
            "🤚 触摸：牵右手": "*你牵起了她的右手*",
            "🤚 触摸：握左手": "*你握住了她的左手*",
            "🤚 触摸：未知触碰": "*你轻轻碰了碰她*",
            "💤 机制：3分钟未互动": "[系统机制：他已经离开你的身边整整 3 分钟了。请根据你此时的心情，输出一小段自言自语或内心独白（使用括号表示心声）。你可以维持刚才互动时的情绪余温，也可以改变动作。注意：你现在处于独处状态，请做自己的事，绝对不要试图对他搭话。]",
            "💤 机制：N分钟深度发呆 (例: 8分钟)": "[系统机制：他离开已经有 8 分钟了，你的视线早已从他原本所在的位置移开，不再看他。此时你可以选择让情绪渐渐平复（切换回talk），或者继续沉浸在自己的世界里小声嘀咕、发呆。请给出一小段心声或自言自语。注意：维持独处状态，不要对他搭话。]",
            "🧊 机制：静止动作破冰 (定格15秒后)": "[系统机制：你刚才已经维持静止发呆或小声嘀咕 15 秒了。请根据你此刻的情绪，决定切换回正常的动态常态动作（如 mood_talk, mood_talk_alc 等）。你可以小声嘟囔一句话、说一两句心声，也可以什么都不说只输出动作标签。]",
            "💦 机制：浴巾意外滑落 (隐藏彩蛋)": "[系统机制：由于长时间的安静，加上你的动作幅度，你身上裹着的浴巾突然意外滑落了！你完全没防备。请立刻输出带有 [act_taol_fall] 标签的动作反应，并伴随一句极其慌乱、娇羞的惊呼或心声。]",
            "💦 机制：浴巾滑落恢复 (10秒后)": "[系统机制：距离刚才浴巾意外滑落已经过去了整整10秒。你现在急忙蹲下重新捡起并紧紧裹好了浴巾。请必须输出 [wear_towel] 标签，并伴随极其娇羞、甚至带有哭腔或羞愤的动作（如 [mood_talk_ero]）与慌乱的话语/心声。]"
        }

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.prompts_data.keys()))
        self.preset_combo.currentTextChanged.connect(
            lambda title: self.api_input.setPlainText(self.prompts_data.get(title, ""))
        )
        layout.addWidget(self.preset_combo)

        self.api_input = QTextEdit()
        self.api_input.setPlainText(self.prompts_data["💬 普通对话"])
        self.api_input.setFixedHeight(80)
        layout.addWidget(self.api_input)

        hbox_options = QHBoxLayout()
        self.chk_raw_text_only = QCheckBox("🍃 极简模式：仅发送下方输入框文本 (屏蔽背景设定，省 Token)")
        self.chk_raw_text_only.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.lbl_token_estimate = QLabel("📊 预估消耗 Token: 0")
        self.lbl_token_estimate.setStyleSheet("color: #e67e22; font-weight: bold;")
        self.lbl_token_estimate.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hbox_options.addWidget(self.chk_raw_text_only)
        hbox_options.addWidget(self.lbl_token_estimate)
        layout.addLayout(hbox_options)

        hbox_btns = QHBoxLayout()
        btn_generate_prompt = QPushButton("🔍 仅嗅探构造的 Prompt")
        btn_generate_prompt.setStyleSheet("background-color: #16a085; color: white; font-weight: bold; padding: 5px;")
        btn_generate_prompt.clicked.connect(self.generate_full_prompt)

        btn_send_real = QPushButton("🚀 组装并发送真实 API 请求")
        btn_send_real.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 5px;")
        btn_send_real.clicked.connect(self.send_real_api_request)

        hbox_btns.addWidget(btn_generate_prompt)
        hbox_btns.addWidget(btn_send_real)
        layout.addLayout(hbox_btns)

        self.api_output = QTextEdit()
        self.api_output.setPlaceholderText("点击上方按钮后，这里将展示完整 Prompt 或真实的大模型流式返回结果...")
        self.api_output.setReadOnly(True)
        self.api_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        layout.addWidget(self.api_output)

        self.tabs.addTab(tab, "📡 提词探针")

                                                     

    def log_param(self, msg):
        self.param_log.insertItem(0, msg)
        self.param_log.scrollToBottom()

    def exec_js(self, js_code):
        self.browser.page().runJavaScript(js_code)

    def set_parameter(self, param_id, value):
        self.log_param(f"➤ JS: {param_id} -> {value}")
        self.exec_js(f"window.setRomashaParam('{param_id}', {value});")

                    
    def matrix_param_changed(self, param, slider_value, val_label=None):
        div = self.param_dividers.get(param, 10.0)
        val = slider_value / float(div)
        if val_label:
            if div > 1: val_label.setText(f"{val:.1f}")
            else: val_label.setText(f"{int(val)}")
        self.set_parameter(param, val)

    def reset_matrix_params(self):
        outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "uniform_tight"
        params = outfit_manager.get_outfit_params(outfit)

        for slider in self.param_sliders.values():
            slider.blockSignals(True)

        for p, slider in self.param_sliders.items():
            div = self.param_dividers.get(p, 10.0)
            if p in params:
                val = params[p]
                slider.setValue(int(val * div))
                self.set_parameter(p, float(val))
            else:
                slider.setValue(0)
                self.set_parameter(p, 0.0)

        for slider in self.param_sliders.values():
            slider.blockSignals(False)

        self.log_param("🔄 物理矩阵 116 项全量参数已被强制重置恢复。")

    def on_html_signal(self, title):
        if title == "EVENT:READY":
            self.log_param("🚀 收到前端就绪信号，正在应用初始外观设定...")
            QTimer.singleShot(500, self.apply_startup_state)

    def apply_startup_state(self):
        self.log_param("👗 自动穿戴: 连衣制服(uniform_dress) + 散发(loose)")
        params = outfit_manager.get_outfit_params("uniform_dress", "loose")
        for p, v in params.items(): self.set_parameter(p, v)

        for p, slider in self.param_sliders.items():
            slider.blockSignals(True)
            if p in params:
                div = self.param_dividers.get(p, 10.0)
                slider.setValue(int(params[p] * div))
            else:
                slider.setValue(0)
            slider.blockSignals(False)

                  
    def update_sandbox_intimacy(self, val):
        llm_brain.config["intimacy"] = val
        self.lbl_intimacy.setText(f"当前沙盒模拟好感度: {val} / 100")
        self.log_param(f"🛡️ 内存好感度漂移至: {val}")

    def _apply_delayed_outfit(self, target_outfit):
        self.log_param(f"⏳ 延迟完毕, 强制刷新模型服装: {target_outfit}")
        params = outfit_manager.get_outfit_params(target_outfit)
        for param_id, val in params.items(): self.set_parameter(param_id, val)

    def simulate_time(self, month, day, hour):
        self.log_param(f"⏰ 时空跳跃: {month}月{day}日 {hour}:00")

                                                            
                                      
                             
                                     
                                   
                                                            
        is_holiday = (month, day) in [(1, 1), (2, 14), (12, 25)]
        is_cold = month in [10, 11, 12, 1, 2, 3]
        current_intimacy = llm_brain.config.get("intimacy", 0)
        target_outfit = None

        if is_holiday:
            target_outfit = "ethnic_cloak" if is_cold else "ethnic_wear"
        elif hour >= 22 or hour <= 6:
            if outfit_manager._current_outfit not in ["sleepwear", "towel"]:
                if current_intimacy >= 60 and random.random() < 0.5:
                    target_outfit = "towel"
                else:
                    target_outfit = "sleepwear"
            else:
                target_outfit = outfit_manager._current_outfit
        elif hour >= 19:
            target_outfit = "uniform_dress"
        else:
            target_outfit = "uniform_tight"

        if target_outfit:
            if target_outfit != outfit_manager._current_outfit:
                self.current_context_html = "<span style='color:#ccc;'><i>(窸窸窣窣换衣服中...)</i></span><br>"
                self.exec_js(f"window.showBubble(\"{self.current_context_html}\");")
                self.log_param(f"⏳ 服装切换至 {target_outfit}, 进入 3 秒延时...")
                QTimer.singleShot(3000, lambda: self._apply_delayed_outfit(target_outfit))
                outfit_manager._current_outfit = target_outfit
            else:
                self.log_param(f"⚡ 目标服装已经是 [{target_outfit}]，无需重复切换。")

                                          
        self.log_param(f"📚 当前章节保持为: 第 {self.get_current_story_chapter()} 章（如需跳章，请使用下方章节跃迁控件）")

                                                        
                 
                                                        
    def get_current_story_chapter(self):

        return int(llm_brain.config.get("current_chapter", 1))

    def refresh_story_state_label(self):




        current_chapter = self.get_current_story_chapter()
        full_future_enabled = hasattr(self, "chk_reveal_full_story") and self.chk_reveal_full_story.isChecked()

        future_desc = "✅ 已授权知晓完整未来剧情" if full_future_enabled else "🔒 默认仅知晓当前章节上下文"
        text = f"当前章节: 第 {current_chapter} 章 | 未来剧情权限: {future_desc}"

        if hasattr(self, "lbl_story_state"):
            self.lbl_story_state.setText(text)

    def load_full_story_chronicle(self):




        if self.full_future_story_cache is not None:
            return self.full_future_story_cache

        try:
            chronicle_path = story_manager.CHRONICLE_FILE
            if not os.path.exists(chronicle_path):
                self.full_future_story_cache = ""
                self.log_param(f"⚠️ 未找到剧情纪事本: {chronicle_path}")
                return ""

            with open(chronicle_path, "r", encoding="utf-8") as f:
                self.full_future_story_cache = f.read().strip()

            self.log_param("📚 已读取 final_aligned_story_chronicle.txt 全文缓存。")
            return self.full_future_story_cache

        except Exception as e:
            self.log_param(f"❌ 读取完整剧情纪事本失败: {e}")
            self.full_future_story_cache = ""
            return ""

    def get_current_chapter_context(self):






        try:
            current_chapter = self.get_current_story_chapter()
            return story_manager.get_chronicle_context(current_chapter)
        except Exception as e:
            self.log_param(f"⚠️ 获取章节上下文失败: {e}")
            return "（章节上下文读取失败）"

    def set_story_chapter(self, chapter, reason=""):




        try:
            chapter = max(1, int(chapter))
        except Exception:
            chapter = 1

        llm_brain.config["current_chapter"] = chapter

        try:
            llm_brain.save_config()
        except Exception as e:
            self.log_param(f"⚠️ 保存章节配置失败: {e}")

        if hasattr(self, "chapter_spin"):
            self.chapter_spin.blockSignals(True)
            self.chapter_spin.setValue(chapter)
            self.chapter_spin.blockSignals(False)

        self.refresh_story_state_label()

        reason_text = f" ({reason})" if reason else ""
        self.log_param(f"📚 当前章节已切换为: 第 {chapter} 章{reason_text}")

                                       
        self.current_context_html = f"<span style='color:#6031e2;'><i>(命运刻度已拨动至第 {chapter} 章{reason_text}...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(章节状态已刷新)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.exec_js(f"window.showBubble('{safe_html}');")

    def shift_story_chapter(self, delta):

        current_chapter = self.get_current_story_chapter()
        target = max(1, current_chapter + int(delta))
        desc = "时光飞逝" if delta > 0 else "时光回溯"
        self.set_story_chapter(target, desc)

    def jump_story_chapter_from_ui(self):

        if hasattr(self, "chapter_spin"):
            self.set_story_chapter(self.chapter_spin.value(), "时光跳跃")

    def on_future_story_toggle(self):





        enabled = self.chk_reveal_full_story.isChecked()
        self.refresh_story_state_label()

        if enabled:
            self.log_param("📖 已开启完整未来剧情注入：本次测试将把 final_aligned_story_chronicle.txt 全文发送给她。")
        else:
            self.log_param("🔒 已关闭完整未来剧情注入：恢复为仅发送当前章节上下文。")

    def preview_story_injection(self):




        current_chapter = self.get_current_story_chapter()
        chapter_context = self.get_current_chapter_context()
        full_future_enabled = self.chk_reveal_full_story.isChecked()
        full_text = self.load_full_story_chronicle() if full_future_enabled else "（当前未启用完整未来剧情全文注入）"

        dialog = QDialog(self)
        dialog.setWindowTitle("剧情注入预览")
        dialog.resize(1000, 700)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        text_edit.setPlainText(
            f"================ 当前章节 ================\n"
            f"第 {current_chapter} 章\n\n"
            f"================ 默认注入：当前章节上下文 ================\n"
            f"{chapter_context}\n\n"
            f"================ 额外注入：完整未来剧情全文 ================\n"
            f"{full_text}"
        )
        layout.addWidget(text_edit)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)

        dialog.exec_()

                    
    def toggle_vision_tracking(self):
        is_on = not self.trackpad.is_tracking_enabled
        self.trackpad.is_tracking_enabled = is_on
        if is_on:
            self.btn_toggle_track.setText("✅ 追踪已开启 (点击阻断)")
            self.btn_toggle_track.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
            self.exec_js("window.toggleTracking(true);")
        else:
            self.btn_toggle_track.setText("❌ 追踪已阻断 (点击恢复)")
            self.btn_toggle_track.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
            self.exec_js("window.toggleTracking(false);")

    def trigger_vision_sleep(self):
        if self.trackpad.is_tracking_enabled: self.toggle_vision_tracking()
        idx = motion_manager.get_motion_index('wait_haji')
        self.exec_js(f"window.playRomashaMotion('BaseMotions', {idx});")
        self.current_context_html = "<span style='color:#ccc;'><i>(陷入发呆...)</i></span><br>"
        self.exec_js(f"window.showBubble(\"{self.current_context_html}\");")

    def simulate_touch(self, tag, name_cn):
                                       
        self.current_context_html = f"<span style='color:#fd92a1;'>*[系统测试]* {name_cn}</span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(感受中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.exec_js(f"window.showBubble('{safe_html}');")

                    
    def run_script(self):
        if self.is_script_running: return
        raw_lines = self.script_input.toPlainText().split('\n')
        self.script_queue = [line.strip() for line in raw_lines if line.strip()]
        self.is_script_running = True
        self.process_next_script_cmd()

    def process_next_script_cmd(self):
        if not self.is_script_running or not self.script_queue:
            self.is_script_running = False
            return

        cmd_line = self.script_queue.pop(0)
        delay_next = 100

        if cmd_line.startswith("DELAY:"):
            try: delay_next = int(cmd_line.split(":", 1)[1].strip())
            except: pass
        elif cmd_line.startswith("BUBBLE:"):
            text = cmd_line.split(":", 1)[1].strip()
            self.current_display_text = ""
            self.target_display_text = text
            self.current_context_html = "<span style='color:#e67e22;'>[剧本气泡]</span><br>"
        elif cmd_line.startswith("ACT:"):
            act = cmd_line.split(":", 1)[1].strip()
            self.tag_execution_queue.append(('act', act))
        elif cmd_line.startswith("WEAR:"):
            wear = cmd_line.split(":", 1)[1].strip()
            self.tag_execution_queue.append(('wear', wear))
        elif cmd_line.startswith("HAIR:"):
            hair = cmd_line.split(":", 1)[1].strip()
            self.tag_execution_queue.append(('hair', hair))

        QTimer.singleShot(delay_next, self.process_next_script_cmd)

                        
    def inject_tag_to_input(self, prefix, val):
        if "---" in val: return
        tag = f"[{prefix}_{val}]"
        current = self.mock_input.toPlainText()
        self.mock_input.setPlainText(tag + current)

    def simulate_llm_stream(self):
        raw_text = self.mock_input.toPlainText()
        if not raw_text: return

        self.current_display_text = ""
        self.processed_tags.clear()
        self.current_context_html = "<span style='color:#48a1fa;'>[本地文本列队]</span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(思考中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.exec_js(f"window.showBubble('{safe_html}');")

                
        tags = re.findall(r'\[([a-zA-Z0-9_]+)\]', raw_text)
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in self.processed_tags:
                self.processed_tags.add(tag_lower)

                if tag_lower.startswith('hair_'):
                    self.tag_execution_queue.append(('hair', tag_lower.split('_', 1)[1]))
                elif tag_lower.startswith('wear_'):
                    self.tag_execution_queue.append(('wear', tag_lower.split('_', 1)[1]))
                elif tag_lower.startswith('mood_'):
                    self.tag_execution_queue.append(('mood', tag_lower.split('_', 1)[1]))
                elif tag_lower.startswith('act_'):
                    self.tag_execution_queue.append(('act', tag_lower.split('_', 1)[1]))

        self.target_display_text = re.sub(r'\[.*?\]', '', raw_text).strip()

    def resolve_static_mood_mock(self):
                       
        self.log_param("🧊 [沙盒机制]: 15秒定格破冰触发，提示大模型说话。")
        self.current_context_html = "<span style='color:#ccc;'><i>(短暂的定格后，她似乎有了动作...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(调整状态...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.exec_js(f"window.showBubble('{safe_html}');")

                           
    def process_next_tag(self):
        if not self.tag_execution_queue: return

        tag_type, val = self.tag_execution_queue.pop(0)
        self.log_param(f"🏷️ 出列执行: {tag_type} -> {val}")

        if tag_type == 'hair':
            params = outfit_manager.get_outfit_params(outfit_manager._current_outfit, val)
            for p, v in params.items(): self.set_parameter(p, v)

        elif tag_type == 'wear':
            params = outfit_manager.get_outfit_params(val)
            for p, v in params.items(): self.set_parameter(p, v)

        elif tag_type == 'mood':
            idx = motion_manager.get_motion_index(val)
            if idx is not None:
                self.current_idle_motion = idx
                if not self.motion_revert_timer.isActive():
                    self.exec_js(f"window.playRomashaMotion('BaseMotions', {idx});")
                else:
                    self.log_param(f"⏳ 瞬间动作播放中，情绪 '{val}' 已在后台就绪待命...")

                                                   
                if val in ['neutral', 'wait', 'wait_haji']:
                    self.static_mood_timer.start(8000)
                    self.log_param(f"⏱️ 启动 15 秒沙盒破冰定时器 (触发 {val})")
                else:
                    self.static_mood_timer.stop()

        elif tag_type == 'act':
            idx = motion_manager.get_motion_index(val)
            if idx is not None:
                self.exec_js(f"window.playRomashaMotion('BaseMotions', {idx});")
                                  
                self.motion_revert_timer.start(4500)

                            
    def typewriter_tick(self):
        if self.chk_network.isChecked() and random.random() < 0.25: return

        if self.current_display_text != self.target_display_text:
            if not self.target_display_text.startswith(self.current_display_text):
                self.current_display_text = self.target_display_text
            else:
                next_idx = len(self.current_display_text)
                if next_idx < len(self.target_display_text):
                    self.current_display_text += self.target_display_text[next_idx]

                                     
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text
            safe_html = final_html.replace("'", "\\'")
            self.exec_js(f"window.showBubble('{safe_html}');")

    def trigger_interrupt(self):
        self.log_param("🛑 中断信号下达！清空动作队列。")
        self.is_script_running = False
        self.script_queue.clear()
        self.tag_execution_queue.clear()
        self.target_display_text = "（中止...）"
        self.current_display_text = "（中止...）"
        idx = motion_manager.get_motion_index('talk')                       
        self.exec_js(f"window.playRomashaMotion('BaseMotions', {idx});")

                    
    def refresh_memory(self, mode):
        self.mem_list.clear()
        try:
            if mode == "real":
                self.log_param("📖 提取真实海马体...")
                results = memory_manager.retrieve_relevant_memories("Romasha", llm_brain.config.get("intimacy", 0), n_results=10)
            else:
                self.log_param("🧪 提取沙盒隔离记忆...")
                if sandbox_collection.count() == 0:
                    results = ""
                else:
                    res = sandbox_collection.get()
                    docs = res.get('documents', [])
                    ids = res.get('ids', [])
                    results = "\n---\n".join([f"[ID: {ids[i]}] {docs[i]}" for i in range(len(docs))])

            if not results: self.mem_list.addItem(f"[{mode.upper()}] 无匹配记录。")
            else:
                for mem in results.split("\n---\n"): self.mem_list.addItem(mem)
        except Exception as e:
            self.mem_list.addItem(f"数据库错: {e}")

    def delete_specific_memory(self):
        mem_id = self.mem_id_input.toPlainText().strip()
        if not mem_id: return
        try:
            sandbox_collection.delete(ids=[mem_id])
            self.log_param(f"🗡️ 精确剔除记忆点: {mem_id}")
            self.refresh_memory("sandbox")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def clear_sandbox(self):
        try:
            sandbox_client.delete_collection("sandbox_memories")
            global sandbox_collection
            sandbox_collection = sandbox_client.get_or_create_collection(name="sandbox_memories",
                                                                         embedding_function=sandbox_ef)
            self.log_param("🧨 虚拟沙盒数据库已摧毁重建。")
            self.refresh_memory("sandbox")
        except Exception as e:
            self.log_param(f"抹除失败: {e}")

    def copy_real_memory_to_sandbox(self):
        try:
            real_col = memory_manager._get_collection()
            if real_col.count() == 0:
                self.log_param("⚠️ 真实记忆库为空，无数据可拷贝。")
                return
            real_data = real_col.get()
            sandbox_collection.add(
                documents=real_data['documents'], metadatas=real_data['metadatas'],
                ids=[f"sandbox_copied_{uid}" for uid in real_data['ids']]
            )
            self.log_param(f"📥 成功拷贝 {len(real_data['documents'])} 条记忆至沙盒！")
            self.refresh_memory("sandbox")
        except Exception as e:
            self.log_param(f"❌ 拷贝失败: {e}")

                                                                      
    def _build_prompts(self):
        user_text = self.api_input.toPlainText().strip()
        if not user_text:
            user_text = "（测试空输入）"

                      
        if hasattr(self, 'chk_raw_text_only') and self.chk_raw_text_only.isChecked():
            return "", user_text

        motions_list_str = "".join([f"- [act_{k}]: {v['desc']}\n" for k, v in motion_manager.MOTIONS.items()])

                                 
        moods_list_str = (
            "- [mood_talk]: 正常交流的动态常态 (有呼吸感和轻微摇摆)\n"
            "- [mood_talk_alc]: 脸红娇羞、不知所措的动态常态\n"
            "- [mood_talk_ero]: 极度委屈、含泪或深情的动态常态\n"
            "- [mood_neutral]: 【特定姿势定格】强制收回动作，变成最基础的呆立静止姿势 (可在玩“一二三木头人”、被罚站、或彻底放空归零等时使用)\n"
            "- [mood_wait]: 【当前姿势冻结】保持你前一秒的动作直接定格，完全屏息不动 (适合被吓到愣住、或者屏住呼吸等僵住的情境)\n"
            "- [mood_wait_haji]: 【当前姿势冻结+碎碎念】保持你前一秒的动作定格，但嘴巴微动 (适合在任何姿势下突然陷入纠结、小声嘀咕、赌气等)\n"
        )

        outfits_list_str = (
            "- [wear_uniform_tight]: 紧身制服 (日常居家/白天)\n"
            "- [wear_uniform_dress]: 连衣裙制服 (更文雅的日常)\n"
            "- [wear_sleepwear]: 睡衣 (夜晚睡觉时穿)\n"
            "- [wear_swimsuit]: 泳装 (去海边或游泳池时穿)\n"
            "- [wear_ethnic_wear]: 民族风服饰 (较为暴露，可以当做特殊节日的服装)\n"
            "- [wear_ethnic_cloak]: 民族风斗篷 (防风防寒，里面穿着民族风服饰，或为了遮挡身体感到害羞时穿)\n"
            "- [wear_towel]: 裹浴巾 (刚洗完澡时穿)\n"
            "- [wear_bunny]: 兔女郎装 (情趣/被特殊要求时)\n"
        )

        hairs_list_str = (
            "- [hair_loose]: 散开头发\n"
            "- [hair_bun]: 把头发盘起来 (丸子头/马尾)\n"
        )

        current_time_str = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
        current_outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "未知"
        current_intimacy = llm_brain.config.get("intimacy", 0)
        current_chapter = self.get_current_story_chapter()

                                                            
                      
                                                            
        memories = ""
        try:
            res = sandbox_collection.query(query_texts=[user_text], n_results=3)
            docs = res.get('documents', [[]])[0]
            if docs:
                memories = "\n---\n".join(docs)
        except Exception:
            pass

                                                            
                                     
                                                            
        chapter_context = self.get_current_chapter_context()

                                                            
                       
                                                             
                                              
                                                            
        full_future_story_enabled = hasattr(self, "chk_reveal_full_story") and self.chk_reveal_full_story.isChecked()
        full_future_story_text = self.load_full_story_chronicle() if full_future_story_enabled else ""

                                                         
                          
                                                     
                                                          
        is_voice_on = llm_brain.config.get("voice_enabled", True)
        tts_engine = llm_brain.config.get("tts_engine", "cosyvoice")
        use_cosyvoice = is_voice_on and (tts_engine == "cosyvoice")

        system_prompt = f"{llm_brain.persona.get_romasha_prompt(use_cosyvoice)}\n\n"
        system_prompt += f"【世界与背景档案】\n{world_info.get_full_lore()}\n\n"

                      
        system_prompt += f"【📚 命运编年史 (当前测试章节：第 {current_chapter} 章)】\n"
        system_prompt += f"{chapter_context}\n\n"

                         
        if full_future_story_enabled and full_future_story_text:
            system_prompt += (
                "【🚨 特殊测试授权：未来全剧情认知已解除封锁】\n"
                "注意：本轮测试中，你被系统明确授权，可以直接知晓、理解并讨论完整编年史中的全部剧情，"
                "包括尚未发生的未来章节、宿命走向、人物结局与世界真相。\n"
                "这会覆盖你平时“只能知道当前阶段剧情”的默认限制。\n"
                "以下是完整剧情纪事本全文，请你将其视为已被明确告知的信息，而不是模糊预感：\n\n"
                f"{full_future_story_text}\n\n"
            )

        system_prompt += f"【来自海马体的过往记忆 (读取沙盒)】\n{memories if memories else '（当前没有唤醒特定的过往回忆）'}\n\n"

        system_prompt += f"【你的当前物理状态】\n"
        system_prompt += f"- 现实时间：{current_time_str}\n"
        system_prompt += f"- 你当前正穿着：{current_outfit}\n"
        system_prompt += f"- 你当前所处章节：第 {current_chapter} 章\n"
        system_prompt += f"- 你当前对我的【亲密度】：{current_intimacy} / 100 \n"
        system_prompt += f"  (说明：负数代表厌恶/恐惧，0-30是陌生/戒备，30-60是朋友/信任，60-80是暧昧，80-100是极度依赖/深爱)\n"
        system_prompt += f"⚠️ 换装与发型规则：你可以根据聊天情境（例如我要你换衣服、你要去洗澡、睡觉或庆祝特殊节日）自主输出 [wear_xxx] 或 [hair_xxx] 标签换衣服或发型。如果没有换装或换发型的行为，【绝对禁止】输出这两个标签！保持现状即可。\n\n"

        system_prompt += f"【⚠️ 你的物理引擎边界（极其重要） ⚠️】\n"
        system_prompt += f"可用服装库：\n{outfits_list_str}\n"
        system_prompt += f"可用发型库：\n{hairs_list_str}\n"
        system_prompt += f"常驻情绪库（决定互动后的余温）：\n{moods_list_str}\n"
        system_prompt += f"瞬间动作库（决定第一反应）：\n{motions_list_str}\n"
        system_prompt += f"再次警告：绝不能创造上面三个列表以外的任何标签！"

        return system_prompt, user_text

    def generate_full_prompt(self):
        system_prompt, user_text = self._build_prompts()
        total_chars = len(system_prompt) + len(user_text)
        est_tokens = int(total_chars * 1.2)

        if hasattr(self, 'lbl_token_estimate'):
            self.lbl_token_estimate.setText(f"📊 字符数: {total_chars} | 预估 Token: ~{est_tokens}")

        current_chapter = self.get_current_story_chapter()
        full_future_enabled = hasattr(self, "chk_reveal_full_story") and self.chk_reveal_full_story.isChecked()

        header = (
            f"=============== [ Prompt 构造状态 ] ===============\n"
            f"当前章节: 第 {current_chapter} 章\n"
            f"完整未来剧情注入: {'已开启' if full_future_enabled else '未开启'}\n\n"
        )

        if not system_prompt:
            final_output = header
            final_output += f"=============== [ 🍃 极简省流模式 (未携带系统设定与记忆) ] ===============\n{user_text}\n"
        else:
            final_output = header
            final_output += f"=============== [ 发往 LLM 的 System 设定 ] ===============\n{system_prompt}\n"
            final_output += f"=============== [ 发往 LLM 的 User 输入 ] ===============\n{user_text}\n"

        self.api_output.setPlainText(final_output)
        self.log_param(
            f"🔍 Prompt 组装完毕 (第{current_chapter}章 | 完整未来注入: {'开' if full_future_enabled else '关'} | 预估Token: {est_tokens})。")

    def send_real_api_request(self):
        api_type = self.input_api_type.currentText().strip()
        base_url = self.input_api_url.text().strip()
        api_key = self.input_api_key.text().strip()
        model = self.input_api_model.text().strip()

        if api_type == "openai" and not api_key:
            QMessageBox.warning(self, "警告", "OpenAI 模式下 API Key 不能为空！")
            return

        btn_sender = self.sender()
        if btn_sender:
            btn_sender.setEnabled(False)
            btn_sender.setText("⏳ 请求中...")

        system_prompt, user_text = self._build_prompts()
        self.generate_full_prompt()
        self.api_output.append("\n\n=============== [ 🚀 正在请求 API，请稍候... ] ===============\n")
        self.log_param("📡 开始向填写的 API 接口发送实机测试请求...")

        self.api_worker = ApiTestWorker(api_type, base_url, api_key, model, system_prompt, user_text)
        self.api_worker.chunk_received.connect(self.on_api_chunk)
        self.api_worker.error.connect(self.on_api_error)
        self.api_worker.finished.connect(self.on_api_finished)
        self.api_worker.btn_sender = btn_sender
        self.api_worker.start()

    def on_api_chunk(self, chunk):
        cursor = self.api_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.api_output.setTextCursor(cursor)
        self.api_output.insertPlainText(chunk)
        self.api_output.ensureCursorVisible()

    def on_api_error(self, err_msg):
        self.api_output.append(f"\n\n❌ [API 请求失败]:\n{err_msg}")
        self.log_param(f"❌ API 测试报错: {err_msg}")
        self._restore_api_btn()

    def on_api_finished(self, full_text):
        self.api_output.append("\n\n✅ [API 流式请求完成]")
        self.log_param("✅ API 实机请求测试完毕。")
        self._restore_api_btn()

    def _restore_api_btn(self):
        if hasattr(self, 'api_worker') and self.api_worker.btn_sender:
            self.api_worker.btn_sender.setEnabled(True)
            self.api_worker.btn_sender.setText("🚀 组装并发送真实 API 请求")

    def revert_to_idle_motion(self):
        self.log_param(f"⏳ 瞬间动作播放结束，自动恢复常驻情绪 (ID: {self.current_idle_motion})")
        self.exec_js(f"window.playRomashaMotion('BaseMotions', {self.current_idle_motion});")

    def closeEvent(self, event):
        self.log_param("🛑 正在停止系统并尝试销毁沙盒...")
        self.tag_timer.stop()
        self.typewriter_timer.stop()

        global sandbox_client, sandbox_collection
        sandbox_collection = None
        sandbox_client = None
        gc.collect()

        try:
            shutil.rmtree("./romasha_test_sandbox_db")
            print("🗑️ 沙盒文件夹 ./romasha_test_sandbox_db 已被彻底抹除。")
        except Exception as e:
            print(f"⚠️ 退出时删除沙盒受阻 (Windows文件锁未释放): {e}")
            print("💡 别担心，下次启动程序时会自动执行强力清扫。")
        event.accept()

    def show_lore_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("世界观 / 当前章节 / 完整编年史检视")
        dialog.resize(1000, 750)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        current_chapter = self.get_current_story_chapter()
        chapter_context = self.get_current_chapter_context()
        full_story = self.load_full_story_chronicle()

        text_edit.setPlainText(
            "================ [ world_info.get_full_lore() ] ================\n"
            f"{world_info.get_full_lore()}\n\n"
            "================ [ 当前章节上下文 ] ================\n"
            f"当前章节: 第 {current_chapter} 章\n"
            f"{chapter_context}\n\n"
            "================ [ final_aligned_story_chronicle.txt 全文 ] ================\n"
            f"{full_story if full_story else '（未找到或读取失败）'}"
        )
        text_edit.setStyleSheet("font-size: 14px; line-height: 1.5;")
        layout.addWidget(text_edit)

        btn_close = QPushButton("关闭窗口")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)

        self.log_param("🌍 已弹出世界观 / 章节 / 编年史综合检视窗口。")
        dialog.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    outfit_manager._current_outfit = None
    tester = SystemEngineTester()
    tester.show()
    sys.exit(app.exec_())