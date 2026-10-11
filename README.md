# Romasha Live2D AI

一个跑在 Windows 上的 **Live2D 桌宠 + 本地 AI 陪伴** 项目：把 Live2D 模型接到 LLM 上，做长期记忆、好感度、世界书、语音朗读与摸头互动。

> ⚠️ **本仓库只包含代码**。Live2D 模型、立绘、语音、世界数据、游戏素材**一律不包含**，也不包含任何游戏资源解密工具与成人内容生成脚本。请自备你有权使用的模型。

## 功能

| 模块 | 文件 | 说明 |
|---|---|---|
| 主程序 / 窗口 | `main.py` | Live2D 窗口、点击与拖动、位置与缩放 |
| 模型交互 | `motion_manager.py` | 动作播放、表情、待机随机动作 |
| 换装 | `outfit_manager.py` | 通过模型参数切换服装/发型/配件 |
| 对话大脑 | `llm_brain.py`、`api.py` | 接入 OpenAI 兼容接口（自填 API Key） |
| 长期记忆 | `memory_manager.py`、`make_memory_data.py`、`view_memories.py` | 记忆抽取、检索与查看 |
| 好感度 / 关系 | `relationship_manager.py`、`persona.py` | 亲密度成长、人设与语气 |
| 世界书 | `lorebook_manager.py`、`world_info.py` | 设定注入、按关键词触发 |
| 剧情 / 场景 | `story_manager.py`、`scene_adapter.py`、`scene_player.py`、`scene_viewer.py` | 剧情推进与场景播放（内容由使用者自备） |
| 地图 | `map_manager.py` | 位置与章节管理 |
| 语音 | `make_voice_ref.py` | 生成参考音频，配合第三方 TTS |
| 工具脚本 | `make_thumbs.py`、`test_motions.py`、`test_system_engine.py` | 缩略图、动作与系统自测 |

## 快速开始

```bash
pip install -r requirements.txt

# 1) 复制一份配置模板，填入你自己的 API Key
#    仓库不含 config.json（已被 .gitignore 排除）
# 2) 把你自己的 Live2D 模型放进 web/ 目录（结构见下方说明）
# 3) 启动
```

Windows 下可直接双击 `启动Romasha.vbs`；`打开场景查看器.bat` 打开场景查看器，`关闭Romasha.bat` 关闭。

### 目录约定（需自备）

```
web/                     Live2D 模型与前端资源（本仓库不提供）
world_data/              世界/剧情数据（本仓库不提供）
voice_ref/               语音参考音频（本仓库不提供）
config.json              你的本地配置与密钥（本仓库不提供）
```

## 第三方组件与来源

本项目**部分代码参考/引用了公开资料与其他开源项目**，相应部分仍遵循其原始许可证，版权归原作者所有：

- **Live2D Cubism SDK / pixi-live2d-display** —— 模型渲染，遵循 Live2D 官方许可（使用模型前请确认其授权）
- **GPT-SoVITS**（MIT）—— 语音合成参考实现（配置项 `sovits_*`）
- **CosyVoice**（Apache-2.0）—— 语音合成参考实现（配置项 `cosy_*`）
- 其余参考来源：若你是某段代码的原作者，**请联系我**，我会补上署名或直接移除该部分。

## 免责声明

- 本仓库**不包含**任何 Live2D 模型、游戏素材、游戏资源解密工具或成人内容生成脚本
- 请勿将本项目用于侵犯他人著作权；使用任何模型/素材前请自行确认授权
- 项目按「现状」提供，不保证可用性

## License

本仓库**自有代码**以 MIT 许可发布（见 `LICENSE`）；第三方组件保留其原始许可证。
