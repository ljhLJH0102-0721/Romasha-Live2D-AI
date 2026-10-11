                  
import os
import sys
import json
import datetime
import shutil
import re
import threading               

                            
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

                                      
WORLD_DATA_DIR = os.path.join(app_dir, "world_data")
SUMMARY_FILE = os.path.join(WORLD_DATA_DIR, "story_summary.txt")
MAX_SUMMARY_LENGTH = 6000                            
NOVEL_LOG_FILE = os.path.join(WORLD_DATA_DIR, "novel_log.txt")
CHRONICLE_FILE = os.path.join(WORLD_DATA_DIR, "final_aligned_story_chronicle.txt")
RECENT_CHAT_FILE = os.path.join(WORLD_DATA_DIR, "recent_chat_history.json")

_file_lock = threading.Lock()                  

def _now_iso():

    return datetime.datetime.now().isoformat()

def _ensure_dir():

    if not os.path.exists(WORLD_DATA_DIR):
        os.makedirs(WORLD_DATA_DIR)

def load_recent_chat_history(max_items=16):


















    _ensure_dir()
    empty_result = {
        "history": [],
        "meta": {
            "last_saved_at": None,
            "session_started_at": None,
            "elapsed_minutes": 0.0,
            "is_stale": False
        }
    }
    if not os.path.exists(RECENT_CHAT_FILE):
        return empty_result

    try:
        with open(RECENT_CHAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

                                            
        if isinstance(data, list):
            raw_history = data
            last_saved_at = None
            session_started_at = None
        elif isinstance(data, dict):
            raw_history = data.get("history", [])
            last_saved_at = data.get("last_saved_at")
            session_started_at = data.get("session_started_at")
        else:
            return empty_result
        if not isinstance(raw_history, list):
            raw_history = []

        cleaned = []
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            ts = item.get("ts")
            if role in ("user", "assistant") and isinstance(content, str):
                cleaned.append({
                    "role": role,
                    "content": content,
                    "ts": ts if isinstance(ts, str) else None
                })

                                
        if max_items is not None and max_items > 0:
            cleaned = cleaned[-max_items:]

        elapsed_minutes = 0.0
        is_stale = False
        if last_saved_at:
            try:
                last_dt = datetime.datetime.fromisoformat(last_saved_at)
                delta = datetime.datetime.now() - last_dt
                elapsed_minutes = round(delta.total_seconds() / 60.0, 2)
                                            
                                              
                is_stale = delta.total_seconds() > 30 * 60
            except Exception:
                pass
        return {
            "history": cleaned,
            "meta": {
                "last_saved_at": last_saved_at,
                "session_started_at": session_started_at,
                "elapsed_minutes": elapsed_minutes,
                "is_stale": is_stale
            }
        }

    except Exception as e:
        print(f"⚠️ [世界法则] 读取最近对话历史失败: {e}")
        return empty_result


def save_recent_chat_history(history, max_items=16):







    _ensure_dir()
    with _file_lock:
        try:
            if not isinstance(history, list):
                history = []

                                                     
            old_session_started_at = None
            if os.path.exists(RECENT_CHAT_FILE):
                try:
                    with open(RECENT_CHAT_FILE, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    if isinstance(old_data, dict):
                        old_session_started_at = old_data.get("session_started_at")
                except Exception:
                    pass

            cleaned = []
            for item in history:
                if not isinstance(item, dict):
                    continue
                role = item.get("role")
                content = item.get("content")
                ts = item.get("ts")
                if role in ("user", "assistant") and isinstance(content, str):
                    cleaned.append({
                        "role": role,
                        "content": content,
                        "ts": ts if isinstance(ts, str) else _now_iso()
                    })

            if max_items is not None and max_items > 0:
                cleaned = cleaned[-max_items:]

            payload = {
                "session_started_at": old_session_started_at or _now_iso(),
                "last_saved_at": _now_iso(),
                "history": cleaned
            }
            with open(RECENT_CHAT_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"⚠️ [世界法则] 保存最近对话历史失败: {e}")


def clear_recent_chat_history():



    with _file_lock:
        if os.path.exists(RECENT_CHAT_FILE):
            try:
                os.remove(RECENT_CHAT_FILE)
                print("🧹 [剧情重置] 最近对话缓存已被清空。")
            except Exception as e:
                print(f"⚠️ [世界法则] 清空最近对话历史失败: {e}")

def format_recent_chat_for_summary(history):



    if not history:
        return ""

    lines = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = "我" if msg.get("role") == "user" else "Romasha"
        content = msg.get("content", "")
        clean_content = re.sub(r'\[.*?\]', '', content)
        clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content).strip()
        if clean_content:
            lines.append(f"{role}: {clean_content}")

    return "\n".join(lines)

def get_summary():

    _ensure_dir()
    if not os.path.exists(SUMMARY_FILE):
        return ""
    try:
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️ [世界法则] 读取总结失败: {e}")
        return ""

def save_summary(text):

    _ensure_dir()
    with _file_lock:          
        try:
            with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            print(f"⚠️ [世界法则] 保存总结失败: {e}")

def append_to_summary(new_entry):

    _ensure_dir()
    with _file_lock:          
        try:
            with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
                f.write(new_entry + "\n")
        except Exception as e:
            print(f"⚠️ [世界法则] 追加日记失败: {e}")

def rewrite_summary(full_text):

    _ensure_dir()
    with _file_lock:          
        try:
            with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
                f.write(full_text + "\n")
        except Exception as e:
            print(f"⚠️ [世界法则] 重写总结失败: {e}")

def clear_summary():

    with _file_lock:                         
        if os.path.exists(SUMMARY_FILE):
            try:
                os.remove(SUMMARY_FILE)
                print("🌀 [剧情重置] 当前的剧情摘要已被清空，世界线回归起点。")
            except Exception as e:
                print(f"⚠️ [世界法则] 抹除总结失败: {e}")

def archive_novel_log():

    with _file_lock:             
        if os.path.exists(NOVEL_LOG_FILE):
            try:
                               
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"novel_log_archive_{timestamp}.txt"
                archive_path = os.path.join(WORLD_DATA_DIR, archive_name)

                           
                os.rename(NOVEL_LOG_FILE, archive_path)
                print(f"📦 [岁月史书]: 上一个周期的推演记录已归档为 {archive_path}")
            except Exception as e:
                print(f"⚠️ [世界线收束]: 归档推演记录失败: {e}")


def get_chronicle_context(chapter_num):





    if not os.path.exists(CHRONICLE_FILE):
        return "⚠️ 未找到剧情纪事本文件。"

    try:
        with open(CHRONICLE_FILE, "r", encoding="utf-8") as f:
            content = f.read()

                                                   
        bg_match = re.search(r'\[背景设定与未明日常\](.*?)(?=\[第.章\])', content, re.DOTALL)
        bg_text = bg_match.group(1).strip() if bg_match else "未找到背景设定。"

                   
        chapters = ["一", "二", "三", "四", "五"]
        if 1 <= chapter_num <= 5:
            chap_str = chapters[chapter_num - 1]
                                   
            pattern = rf'\[第{chap_str}章\](.*?)(?=\[第.章\]|\Z)'
            chap_match = re.search(pattern, content, re.DOTALL)
            chap_text = chap_match.group(1).strip() if chap_match else "（当前章节的命运迷雾尚未散去，或者你已超越了已知的历史...）"

            return f"【世界背景与日常设定】\n{bg_text}\n\n【本章原定宿命轨迹 (第{chap_str}章)】\n{chap_text}"
        else:
                            
            return f"【世界背景与日常设定】\n{bg_text}\n\n【未知章节/后日谈】\n宿命的剧本已经写完，现在的未来完全是一片空白，将由你和玩家共同创造。"

    except Exception as e:
        print(f"⚠️ [世界法则] 读取剧情纪事失败: {e}")
        return ""