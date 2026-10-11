                     
import os
import sys
import json
import re
import threading
import requests
from openai import OpenAI

import map_manager

_lore_lock = threading.Lock()


                      
LORE_UNLOCK_CHAPTER = {

                                                         
                                   
    "罗玛莎_人物": 1,
    "斯皮娜（幼年/俘虏状态）_人物": 1,
    "白袍女（司令官身份）_人物": 1,
    "博士（高层身份）_人物": 1,
    "盖因（医生/老师）_人物": 1,
    "卡珠娅_人物": 1,
    "巴尼拉_人物": 1,
    "温妮_人物": 1,
    "迪亚德_人物": 1,
    "苏特_人物": 1,
    "第四分队_组织": 1,
    "0番队_组织": 1,
    "海兰达_组织": 1,

    "ID权限_机制": 1,
    "宵禁_机制": 1,
    "AI警备_机制": 1,
    "光子尼亚_道具": 1,        
    "数据银行_机制": 1,
    "传送装置_机制": 1,
    "卡牌战斗系统_机制": 1,
    "认知阻碍_机制": 1,
    "情感抑制装置_机制": 1,
    "释放日（正常版）_机制": 1,
    "星座分类_机制": 1,

                                                         
                               
    "斯皮娜的故乡_地点": 2,
    "吉吉_人物": 2,
    "兹阿_人物": 2,
    "察尔_人物": 2,
    "龙人_种族": 2,
    "龙化_机制": 2,
    "哥布林_怪物": 2,
    "矩阵复制个体_机制": 2,
    "旧文明系统_机制": 2,
    "病毒（真实设定）_机制": 2,
    "理想样本_设定": 2,

                                                       
                                
    "玛隆_人物": 3,          
    "地下都市C区块_地点": 3,
    "游郭控室_地点": 3,
    "老板娘_人物": 3,
    "米泽尔_人物": 3,
    "天波（主持人）_人物": 3,
    "阿格罗_人物": 3,
    "萨尔贝_人物": 3,
    "N-UI（紧急支援AI）_人物": 3,
    "小丑组织_组织": 3,

    "升格制度_机制": 3,
    "标记传送装置_机制": 3,
    "身元引受人_机制": 3,
    "电子药品_道具": 3,
    "双子卡_道具": 3,

                                                           
                                      
    "奉仕活动_机制": 4,
    "病毒清除作战_机制": 4,
    "精液作战_机制": 4,               
    "奉仕部队_组织": 4,
    "废弃体_机制": 4,
    "邦卡_人物": 4,

    "全裸谢罪_事件": 4,
    "释放日失序_事件": 4,
    "全域广播_事件": 4,
    "逆向程序_道具": 4,

                                                       
                             
    "协同卡_道具": 5,                               
    "里萨勒长官_人物": 5,
    "半兽化斯皮娜_人物": 5,
    "马里甘（multi link）_机制": 5,
    "重启世界_机制": 5,
    "母体_怪物": 5
}


if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

WORLD_DATA_DIR = os.path.join(app_dir, "world_data")
STATIC_LORE_FILE = os.path.join(WORLD_DATA_DIR, "static_lore.json")
DYNAMIC_LORE_FILE = os.path.join(WORLD_DATA_DIR, "dynamic_lore.json")


def _ensure_dir():
    if not os.path.exists(WORLD_DATA_DIR):
        os.makedirs(WORLD_DATA_DIR)


                                            
             
                                            
def get_static_lore():

    _ensure_dir()
    if not os.path.exists(STATIC_LORE_FILE):
        return {}
    try:
        with open(STATIC_LORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [世界法则] 读取静态世界书失败: {e}")
        return {}


def get_dynamic_lore():

    _ensure_dir()
    if not os.path.exists(DYNAMIC_LORE_FILE):
        return {}
    try:
        with open(DYNAMIC_LORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [世界法则] 读取动态世界书失败: {e}")
        return {}


def save_dynamic_lore(data):

    _ensure_dir()
    with _lore_lock:                      
        try:
            with open(DYNAMIC_LORE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [世界法则] 动态世界书保存失败: {e}")


def clear_dynamic_lore():

    if os.path.exists(DYNAMIC_LORE_FILE):
        try:
            os.remove(DYNAMIC_LORE_FILE)
            print("🌀 [世界法则]: 所有命运的变动已被抹除，设定回归初始状态。")
        except Exception as e:
            print(f"⚠️ [世界法则] 抹除动态世界书失败: {e}")


                                            
                     
                                            
def scan_and_get_lore(text, current_chapter=1):




    if not text: return ""

    triggered_entries = []
                      
    safe_lore = get_filtered_lore_context(current_chapter)
    dynamic_lore = get_dynamic_lore()
               
    text_lower = text.lower()

    for key, data in safe_lore.items():
                   
        hit = any(kw.lower() in text_lower for kw in data.get("keywords", []))
        if hit:
                                       
            if key in dynamic_lore:
                dyn = dynamic_lore[key]
                if isinstance(dyn, dict):
                    content = dyn.get("content", "")
                else:
                    content = str(dyn)
                triggered_entries.append(f"- 【{key} (当前最新状态)】: {content}")
            else:
                content = data.get("content", "")
                triggered_entries.append(f"- 【{key} (基础设定)】: {content}")

                                 
                                       
    for key, content in dynamic_lore.items():
        if key not in safe_lore:
                                              
            real_name = key.split("_")[0] if "_" in key else key

            if isinstance(content, dict):
                real_content = content.get("content", "")
            else:
                real_content = str(content)

                                                    
                                                      
                                                       
            if "称呼" in key or real_name.lower() in text_lower:
                triggered_entries.append(f"- 【{key} (动态衍变/新发现)】: {real_content}")

    if triggered_entries:
        return "【💡 脑海中浮现的相关情报 (世界书)】\n" + "\n".join(triggered_entries) + "\n\n"
    return ""


                                            
                           
                                            
def update_lorebook_background(recent_history, config):





    def _task():
        try:
                                      
            current_chapter = config.get("current_chapter", 1)

                                                    
            safe_lore = get_filtered_lore_context(current_chapter)
            if not safe_lore: return                      

                    
            dialogue_text = ""
            for msg in recent_history:
                role = "我" if msg["role"] == "user" else "Romasha"
                clean_content = re.sub(r'\[.*?\]', '', msg['content'])
                clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content).strip()
                dialogue_text += f"{role}: {clean_content}\n"

                                                
            keys_str = ", ".join(safe_lore.keys())

                                           
            prompt = (
                f"你是一个客观的剧情状态记录员。请阅读以下最新发生的对话：\n"
                f"1. 判断以下已知实体（{keys_str}）的【持有状态】、【所处位置】、【生死存亡】或【人物关系】是否发生重大改变。\n"
                f"2. 🚨【新增法则】：如果对话中出现了一个【全新的重要人物】、【关键道具】或【新地点】（不在上述已知列表中），请为它创建一个新档案！\n"
                f"3. 🚨或者双方是否在对话中确立了新的【玩家与罗玛莎的亲昵专属称呼】。\n\n"
                f"【最新对话】:\n{dialogue_text}\n\n"
                f"【输出规则】:\n"
                f"1. 只有发生改变，或出现新实体时才需要更新。\n"
                f"2. 严格输出 JSON 格式。如果是新实体，键名【必须】带有后缀（如：'神秘短剑_道具'，'流浪商人_人物'，'废弃矿洞_地点'）。如果是称呼，键名必须包含'称呼'二字。\n"
                f"3. 格式为：{{\"实体名_类型\": \"精简描述其当前状态或设定\"}}。\n"
                f"4. 如果没有任何状态改变或新实体，请务必直接输出空的 JSON：{{}}\n"
                f"绝对不要输出任何 JSON 格式以外的废话。"
            )

            messages = [{"role": "user", "content": prompt}]
            api_type = config.get("api_type", "openai").lower()
            target_model = config.get("target_model", "")
            result_text = ""

            if api_type == "openai":
                client = OpenAI(api_key=config.get("api_key", ""), base_url=config.get("base_url", ""), timeout=60.0)
                response = client.chat.completions.create(model=target_model, messages=messages, temperature=0.1)
                result_text = response.choices[0].message.content.strip()
            elif api_type == "ollama":
                base_url = config.get("base_url", "").rstrip('/')
                if not base_url.endswith('/api/chat'): base_url = f"{base_url}/api/chat"
                payload = {"model": target_model, "messages": messages, "stream": False,
                           "options": {"temperature": 0.1}}
                headers = {"Content-Type": "application/json"}
                if config.get("api_key", ""): headers["Authorization"] = f"Bearer {config.get('api_key', '')}"
                resp = requests.post(base_url, json=payload, headers=headers, timeout=60.0)
                if resp.status_code == 200:
                    result_text = resp.json().get("message", {}).get("content", "").strip()

                             
            try:
                                             
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)

                updates = {}
                if json_match:
                                            
                    clean_json_str = json_match.group(0)
                    updates = json.loads(clean_json_str)

                if updates and isinstance(updates, dict):
                               
                    current_dynamic = get_dynamic_lore()
                    updated_count = 0

                    for k, v in updates.items():
                                                                    
                        valid_suffixes = ["_人物", "_地点", "_道具", "_机制", "_组织", "_怪物", "_事件"]
                        is_new_entity = any(k.endswith(suffix) for suffix in valid_suffixes)

                                                                    
                        if k in safe_lore or "称呼" in k or is_new_entity:                       
                                         
                                                                          
                                                  
                            if isinstance(v, str):
                                current_dynamic[k] = {
                                    "content": v,
                                    "keywords": [k.split("_")[0]]
                                }
                            else:
                                current_dynamic[k] = v
                            updated_count += 1

                    if updated_count > 0:
                        save_dynamic_lore(current_dynamic)
                                                                    
                                                  
                                                    
                                                                    
                                  
                                        
                                             
                                    
                        for entity_key, entity_val in updates.items():
                            if not isinstance(entity_key, str):
                                continue
                                                
                            if entity_key.endswith("_地点"):
                                location_name = entity_key.rsplit("_地点", 1)[0].strip()
                                if not location_name:
                                    continue
                                              
                                if isinstance(entity_val, dict):
                                    content = entity_val.get("content", "")
                                    keywords = entity_val.get("keywords", [location_name])
                                else:
                                    content = str(entity_val).strip()
                                    keywords = [location_name]
                                             
                                                         
                                map_manager.map_instance.update_dynamic_location(
                                    location_name=location_name,
                                    lore=content,
                                    related_characters=["Romasha"],
                                    keywords=keywords
                                )
                        print(f"\n📚 [世界法则]: 命运的轨迹已变动，世界书自动更新了 {updated_count} 条动态档案。")
            except json.JSONDecodeError:
                pass                        

        except Exception as e:
            print(f"⚠️ [世界法则]: 动态世界书后台更新失败: {e}")

    threading.Thread(target=_task, daemon=True).start()


def get_filtered_lore_context(current_chapter=1):



    static_lore = get_static_lore()
    dynamic_lore = get_dynamic_lore()

                
    merged_lore = {**static_lore, **dynamic_lore}
    safe_lore = {}

    for key, info in merged_lore.items():
                                 
        required_chapter = LORE_UNLOCK_CHAPTER.get(key, 1)
        if current_chapter < required_chapter:
            continue

        content = info.get("content", "") if isinstance(info, dict) else str(info)

                           
                                                  
                               

                    
                                           
        matches = list(re.finditer(r'\[(?:第(\d+)章解锁|Chapter(\d+))\]:', content))

        cut_index = len(content)         

        for match in matches:
                  
            chap_num_str = match.group(1) or match.group(2)
            tag_chapter = int(chap_num_str)

                                        
            if current_chapter < tag_chapter:
                cut_index = match.start()
                break                     

        safe_lore[key] = {
                     
            "content": content[:cut_index].strip(),
            "keywords": info.get("keywords", []) if isinstance(info, dict) else [key]
        }

    return safe_lore