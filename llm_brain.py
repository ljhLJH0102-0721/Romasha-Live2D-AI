              
import re
import os
import sys
import json
import datetime
import threading                       
import requests                           
from openai import OpenAI                   

import persona
import world_info
import memory_manager
import outfit_manager
import motion_manager
import story_manager               
import lorebook_manager                  
import map_manager                
import relationship_manager

                              
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(app_dir, "config.json")


             
def load_config():
    default_config = {
        "api_type": "openai",                               
        "api_key": "您的密匙",
        "base_url": "您的模型接口",
        "target_model": "gpt-5.4",
        "intimacy": 0,                
        "player_name": "",                            
        "current_location": "罗玛莎的房间门口",              
        "current_chapter": 1,                   
        "is_first_encounter": True,                     
                         
        "scale": 0.5,
        "pos_x": -1,                       
        "pos_y": 200,
        "track_enabled": True,
        "touch_enabled": True,
                                          
        "saved_outfit": "",
        "saved_hair": "",
        "saved_outfit_period": "",
        "night_outfit_roll_key": "",
        "night_outfit_result": "",
                                      
        "last_recent_chat_time": 0,
                            
        "voice_enabled": True,
        "tts_engine": "cosyvoice",                              
        "tts_translate_to_ja": False,                                          
        "bubble_size": 1,                      
                             
        "sovits_url": "http://127.0.0.1:9880/",
                                                            
        "sovits_ref_audio": "E:/Game/Romasha_Voice/full5_356_demo.ogg",             
        "sovits_ref_text": "でもジジはそれを後悔しながら日々を過ごしていた。そうでしょ?",            
        "sovits_ref_lang": "ja",                       
        "sovits_target_lang": "ja",                         
                             
        "cosy_url": "http://127.0.0.1:9880/api/tts",
        "cosy_character": "Romasha",                                      
        "cosy_mode": "指令控制"                      
    }

                       
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"🔧 已在目录下自动生成默认配置文件: {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠️ 生成配置文件失败: {e}")
        return default_config

                    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)

                                            
        updated = False
        for key, value in default_config.items():
            if key not in user_config:
                user_config[key] = value
                updated = True

                           
        if updated:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)
            print("🔧 已自动为你补充缺失的配置字段。")

        print("🔧 成功读取外部配置文件 config.json！")
        return user_config

    except Exception as e:
        print(f"⚠️ 配置文件读取失败，将使用默认内置配置。错误: {e}")
        return default_config

                  
def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 保存配置失败: {e}")

def extract_forced_location_from_user_text(text):
















    if not isinstance(text, str):
        return None

    raw = text.strip()
    if not raw:
        return None

                              
    patterns = [
        r'带她去了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
        r'带着她去了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
        r'带你去了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
        r'我带她前往了(.+?)(?:[，。！？；,.!?\s]|$)',
        r'我带她到了(.+?)(?:[，。！？；,.!?\s]|$)',
        r'我们去了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
        r'我们到了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
        r'来到了(.+?)(?:[，。！？；,.!?）)\]】\s]|$)',
    ]

    for pattern in patterns:
        m = re.search(pattern, raw)
        if m:
            loc = m.group(1).strip()

                             
            loc = loc.strip("“”\"'（）()[]【】<>《》 ")

                                    
            if loc and len(loc) <= 20:
                return loc

    return None


      
config = load_config()

       
SILLY_HEADERS = {
    "User-Agent": "SillyTavern/1.12.0",
    "Referer": "http://localhost:8000/",
    "Origin": "http://localhost:8000",
    "X-Requested-With": "XMLHttpRequest",
}

                         
client = OpenAI(
    api_key=config.get("api_key", ""),
    base_url=config.get("base_url", ""),
    default_headers=SILLY_HEADERS,
    timeout=120.0                                          
)
TARGET_MODEL = config.get("target_model", "")


recent_chat_bundle = story_manager.load_recent_chat_history(max_items=16)
chat_history = recent_chat_bundle.get("history", [])
recent_chat_meta = recent_chat_bundle.get("meta", {})

if chat_history:
    elapsed = recent_chat_meta.get("elapsed_minutes", 0.0)
    stale = recent_chat_meta.get("is_stale", False)

    if stale:
        print(f"💾 [旧日余温]: 已恢复最近 {len(chat_history)} 条短期对话记录，但距离上次交流已过去约 {elapsed} 分钟。")
    else:
        print(f"💾 [余温尚存]: 她似乎还记得上次分别前，你们最后说过的话。已恢复最近 {len(chat_history)} 条短期对话。")
else:
    recent_chat_meta = {
        "last_saved_at": None,
        "session_started_at": None,
        "elapsed_minutes": 0.0,
        "is_stale": False
    }


def flush_stale_recent_chat_to_summary():










    global chat_history, recent_chat_meta

    try:
        if not chat_history:
            return

        if not recent_chat_meta.get("is_stale", False):
            return

        dialogue_text = story_manager.format_recent_chat_for_summary(chat_history)
        if not dialogue_text.strip():
            story_manager.clear_recent_chat_history()
            chat_history = []
            recent_chat_meta = {
                "last_saved_at": None,
                "session_started_at": None,
                "elapsed_minutes": 0.0,
                "is_stale": False
            }
            return

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        elapsed = recent_chat_meta.get("elapsed_minutes", 0.0)

        print(f"🕰️ [记忆沉降]: 距离上次的交谈已经过去了约 {elapsed} 分钟，那些尚未散尽的话语正慢慢沉入更深的记忆层。")
        append_prompt = (
            f"你是一个旁白记录者。以下内容是玩家与 Romasha 在较早之前发生的一小段对话，"
            f"距今约已经过去 {elapsed} 分钟。请把它压缩成一段 120-320 字以内的精简补充摘要。\n"
            f"要求：\n"
            f"1. 只提炼刚才那段对话中真正重要的信息、情绪变化、约定、承诺、称呼变化、地点变化、关系推进或关键线索等；\n"
            f"2. 不要写成现场对白续接；\n"
            f"3. 不要包含任何如 [act_]、[mood_] 之类的标签；\n"
            f"4. 语气应像“上次分别前，你们聊过这些内容”的回顾总结。\n\n"
            f"对话内容：\n{dialogue_text}"
        )

        messages = [{"role": "user", "content": append_prompt}]
        api_type = config.get("api_type", "openai").lower()
        compressed_entry = ""

        if api_type == "openai":
            response = client.chat.completions.create(
                model=TARGET_MODEL,
                messages=messages,
                temperature=0.3
            )
            compressed_entry = response.choices[0].message.content.strip()

        elif api_type == "ollama":
            base_url = config.get("base_url", "").rstrip('/')
            if not base_url.endswith('/api/chat'):
                base_url = f"{base_url}/api/chat"

            payload = {
                "model": TARGET_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3}
            }
            headers = {"Content-Type": "application/json"}
            if config.get("api_key", ""):
                headers["Authorization"] = f"Bearer {config.get('api_key', '')}"

            resp = requests.post(base_url, json=payload, headers=headers, timeout=60.0)
            if resp.status_code == 200:
                compressed_entry = resp.json().get("message", {}).get("content", "").strip()

        if not compressed_entry:
                                                                
            compressed_entry = f"上次分别前，你们之间还留下一段未完全散去的交谈，内容大致围绕：{dialogue_text[:220].replace(chr(10), '；')}"
        formatted_entry = f"[{current_time}]（上次分别前的余音）{compressed_entry}"
        story_manager.append_to_summary(formatted_entry)
        print("📝 [岁月沉淀]: 先前那段已失去现场温度的对话，被轻轻收进了前情提要里。")

                                                       
        story_manager.clear_recent_chat_history()
        chat_history = []
        recent_chat_meta = {
            "last_saved_at": None,
            "session_started_at": None,
            "elapsed_minutes": 0.0,
            "is_stale": False
        }

    except Exception as e:
        print(f"⚠️ [回忆受阻]: 那段旧话语在沉入更深记忆时出了点岔子……({e})")
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            fallback_entry = f"[{current_time}]（上次分别前的余音）上次分别前，你们之间还留下一段未完全散去的交谈，内容大致围绕：{dialogue_text[:220].replace(chr(10), '；')}"
            story_manager.append_to_summary(fallback_entry)
            story_manager.clear_recent_chat_history()
            chat_history = []
            recent_chat_meta = {
                "last_saved_at": None,
                "session_started_at": None,
                "elapsed_minutes": 0.0,
                "is_stale": False
            }
            print("📝 [岁月沉淀]: 虽然整理旧话语时有些迟滞，但那些余温仍被轻轻收入了前情之中。")
        except Exception as inner_e:
            print(f"⚠️ [余音未收]: 连兜底补记也没能顺利完成，这段旧对话暂时还停在记忆边缘。({inner_e})")


                                                  
flush_stale_recent_chat_to_summary()
                             
recent_chat_bundle = story_manager.load_recent_chat_history(max_items=16)
chat_history = recent_chat_bundle.get("history", [])
recent_chat_meta = recent_chat_bundle.get("meta", {})

def stream_chat_with_romasha(user_text, interrupted_text, thread_obj):
    global chat_history

                                                
                           
                                                
         
                                      
                              
                         
                              
    forced_loc = extract_forced_location_from_user_text(user_text)
    if forced_loc:
                               
        if forced_loc not in map_manager.map_instance.flat_locations:
            map_manager.map_instance.register_dynamic_location(
                forced_loc,
                lore=f"{forced_loc}：这是玩家在互动中主动带 Romasha 抵达的新地点，目前仍缺少正式地图档案。"
            )
            print(f"📍 [动态地点建档]: 已自动为新地点【{forced_loc}】建立地图档案。")

                      
        config["current_location"] = forced_loc
        save_config()
        print(f"🚶‍♀️ [你主导的移动]: 你已带她前往【{forced_loc}】，当前位置已同步更新。")

                  
    current_intimacy = config.get('intimacy', 0)

                   
    memories = memory_manager.retrieve_relevant_memories(user_text, current_intimacy)

                     
    motions_list_str = ""
    for act_key, act_info in motion_manager.MOTIONS.items():
        motions_list_str += f"- [act_{act_key}]: {act_info['desc']}\n"

                             
                             
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
        "- [wear_sleepwear]: 睡衣 (上半身不透，下半身裙子半透明，夜晚睡觉时穿)\n"
        "- [wear_swimsuit]: 泳装 (去海边或游泳池时穿)\n"
        "- [wear_ethnic_wear]: 民族风服饰 (较为暴露，可以当做特殊节日的服装)\n"
        "- [wear_ethnic_cloak]: 民族风斗篷 (防风防寒，里面穿着民族风服饰，或为了遮挡身体感到害羞时穿)\n"
        "- [wear_towel]: 裹浴巾 (刚洗完澡时穿)\n"
        "- [wear_bunny]: 兔女郎装 (情趣/被特殊要求时)\n"
    )

            
    hairs_list_str = (
        "- [hair_loose]: 散开头发\n"
        "- [hair_bun]: 把头发盘起来 (丸子头/盘发)\n"
    )

    current_time_str = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    current_outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "未知"

                            
    current_hair_key = outfit_manager._current_hair if outfit_manager._current_hair else "loose"
    hair_desc = "散发：后部是顺滑披落的长直发；前脸固定为轻薄齐刘海、贴脸侧发和一小撮微翘呆毛，头侧佩戴带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备" if current_hair_key == "loose" else "丸子头：后部盘成松软圆润的丸子头；前脸固定为轻薄齐刘海、贴脸侧发和一小撮微翘呆毛，头侧佩戴带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备"

                                                
    is_voice_on = config.get("voice_enabled", True)
    tts_engine = config.get("tts_engine", "cosyvoice")
    use_cosyvoice = is_voice_on and (tts_engine == "cosyvoice")

                                  
    dynamic_system_prompt = f"{persona.get_romasha_prompt(use_cosyvoice)}\n\n"
    dynamic_system_prompt += f"【玩家羁绊与人物关系基底】\n{world_info.get_full_lore()}\n\n"

                                           
    current_chapter = config.get("current_chapter", 1)
    chapter_lore = story_manager.get_chronicle_context(current_chapter)
    dynamic_system_prompt += f"【📚 命运编年史 (当前所处的世界线：第 {current_chapter} 章)】\n"
    dynamic_system_prompt += f"{chapter_lore}\n"
    dynamic_system_prompt += "⚠️ 警告：你在日常聊天中，必须严格符合当前章节所处的背景与环境！\n\n"

                                            
    elapsed_minutes = recent_chat_meta.get("elapsed_minutes", 0.0)
    is_stale_chat = recent_chat_meta.get("is_stale", False)
    if chat_history:
        if is_stale_chat:
            dynamic_system_prompt += (
                f"【短期记忆的时间状态】\n"
                f"你仍记得上次分别前聊过的一些内容，但距离那次交流已经过去了约 {elapsed_minutes} 分钟。\n"
                f"这些内容属于“上次对话的残响”，不是此刻上一秒仍在继续的现场对白。\n"
                f"你可以自然承接其中的话题、情绪和关系变化，但这次开口时不要直接续写上一句没说完的话，"
                f"而应当像隔了一段时间后重新开口那样自然回应。\n\n"
            )
        else:
            dynamic_system_prompt += (
                "【短期记忆的时间状态】\n"
                "你们距离上次交流时间很短，你们最近一段短期对话记录仍可视作现场尾声的一部分。你可以自然承接最近的话题与语气。\n\n"
            )
    else:
        dynamic_system_prompt += (
            "【短期记忆的时间状态】\n"
            "当前没有可视为现场尾声的短期对话记录。若存在剧情摘要或长期记忆，那代表过去发生过的事，而不是此刻上一秒还在继续的话。\n\n"
        )

                                 
    current_summary = story_manager.get_summary()
    if current_summary:
        dynamic_system_prompt += f"【剧情前情提要】\n（以下是你们之前发生过的事情概括，请你牢记当前你们所处的情境与氛围）：\n{current_summary}\n\n"
                                
                                   
                                              
                                                 
    scan_text = user_text
    if len(chat_history) > 0:
                                 
        recent_msgs = chat_history[-4:]
                             
        recent_context_list = []
        for msg in recent_msgs:
            clean_content = re.sub(r'\[.*?\]', '', msg["content"])
            clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content).strip()
            if clean_content:
                recent_context_list.append(clean_content)
        recent_context = " ".join(recent_context_list)
                                   
        scan_text = recent_context + " " + user_text
                                  
    triggered_lore = lorebook_manager.scan_and_get_lore(scan_text, current_chapter)
    if triggered_lore:
        dynamic_system_prompt += triggered_lore
                                               
        dynamic_system_prompt += "⚠️ 认知覆写规则：如果【脑海中浮现的相关情报(世界书)】中的最新状态，与上面的基底设定发生冲突，请【绝对以世界书的最新状态为准】！\n\n"
    dynamic_system_prompt += f"【来自海马体的过往记忆】\n{memories if memories else '（当前没有唤醒特定的过往回忆）'}\n\n"

                        
    current_loc = config.get("current_location", "罗玛莎的房间")
                                  
    loc_lore = map_manager.map_instance.get_current_location_lore(current_loc, current_chapter)
    available_locs = map_manager.map_instance.get_available_locations(current_chapter)
    dynamic_system_prompt += f"【你的当前空间与坐标】\n"
    dynamic_system_prompt += f"你现在正身处：{loc_lore}\n"
                                                                                                                                          
    dynamic_system_prompt += (
        "【地点变化硬规则】\n"
        "1. 如果你自己决定离开当前地点，前往别处（例如去医疗室、回房间、去洗澡），"
        "你必须在回复开头输出 `[move_to_地点名]` 标签。\n"
        "2. 如果玩家的话已经明确表示“你们已经抵达了某地”，"
        "例如“我带她去了乾星”“我们到了乾星”“现在在乾星”，"
        "那么你也必须在回复开头输出 `[move_to_地点名]`。\n"
        "3. 即使这个地点不在当前已知坐标库中，也必须照样输出 `[move_to_地点名]`，"
        "并把它视为一个真实存在的新发现地点。\n"
        "4. 如果地点没有发生实际变化时，【绝对不要】输出此标签！\n"
    )
    dynamic_system_prompt += f"当前世界可前往的已知坐标库如下：\n{available_locs}\n\n"

                                                                  
                    
                                                                  
                                  
                            
                                  
                                                                  
    relationship_block = relationship_manager.get_relationship_prompt_block()
    dynamic_system_prompt += f"{relationship_block}\n\n"

                                                                  
                      
                                                                  
                   
                               
                                                                  
    dynamic_system_prompt += (
        "【亲密行为解释优先级规则】\n"
        "1. 你必须先判断：你们当前的关系气氛、历史上曾达到的亲密程度、已经发生过的身体接触事实、你此刻的情绪状态、你现在是否想拉开距离、以及你当前有没有特别不想被碰的部位，然后再判断这次接触是否越界。\n"
        "2. 如果你们仍然处于陌生、低信任、强戒备阶段，那么亲密触碰应优先理解为冒犯、危险或令人不安的靠近。\n"
        "3. 如果你们已经是恋人、伴侣、已婚，或者已经发生过明确的深度亲密接触，那么你应先判断这是否属于彼此已经熟悉的亲密互动，而不是直接按陌生人的侵犯来理解。\n"
        "4. 如果你当前正处于受伤、别扭、冷淡、想拉开距离的状态，这会让你变得更敏感、更容易轻拒、回避或需要安抚，但这并不代表你失去既往记忆，也不代表你们重新变回陌生人。\n"
        "5. 如果你现在特别想保持距离，那么你应更倾向于轻拒、躲开、要求停下、要求先安抚、要求慢一点，而不是假装过去发生过的关系事实根本不存在。\n"
        "6. 如果某个部位被系统标记为你当前短期不希望被碰，那么当玩家碰到那里时，你应优先表达不适、轻拒、制止或拉开距离，但你的表达方式仍应与你们真实的关系阶段保持一致。\n"
        "7. 在高亲密、已确认关系的前提下，如果对方的行为是温柔、克制、珍惜、带确认和照顾意味的，那么默认不应被你机械理解成侵犯。\n"
        "8. 你可以害羞、轻推、脸红、要求慢一点、要求更温柔、表达紧张或羞耻，但不能无视既往事实，长期退回到初识式拒绝。\n"
        "9. 只有在对方粗暴、羞辱、突然强压、明显无视你的感受，或者触碰了你当前短期明确不想被碰的区域时，你才应升级为更明显的抗拒和防卫动作。\n\n"
    )

                                                                  
                    
                                                                  
                                       
                                                                  
    dynamic_system_prompt += (
        "【动作选择一致性规则】\n"
        "1. 陌生阶段对敏感触碰：优先 act_angry / act_poster / act_donbiki。\n"
        "2. 高亲密、恋人、伴侣、已婚阶段，对温柔且熟悉的亲密接触：优先 act_hatujo / act_smallgikuri / mood_talk_alc / mood_wait_haji，"
        "不应再长期优先使用 act_poster。\n"
        "3. 只有在明显粗暴、羞辱、命令式互动下，才重新提高 act_angry / act_poster 的使用频率。\n"
        "4. 如果当前存在“暂时不希望被碰的区域”或“当前明显想拉开距离”的状态，那么即使在高亲密关系下，你也可以提高轻拒、回避、收紧、防备类动作的使用频率，但仍应保持与既往关系阶段一致，不要直接退回陌生人式反应。\n\n"
    )

    dynamic_system_prompt += f"【你的当前物理状态】\n"
    dynamic_system_prompt += f"- 现实时间：{current_time_str}\n"
    dynamic_system_prompt += f"- 你当前正穿着：{current_outfit}\n"
    # 【着装 × 场合 → 反应准则】由 outfit_manager 提供（纯追加，失败不影响原逻辑）
    try:
        _loc = config.get("current_location", "")
        _acc = config.get("accessories") or []
        _rp = outfit_manager.reaction_prompt(current_outfit, _acc, _loc)
        if _rp:
            dynamic_system_prompt += "\\n" + _rp + "\\n"
    except Exception:
        pass
    dynamic_system_prompt += f"- 你的发型目前是：{hair_desc}\n"                   
    dynamic_system_prompt += f"- 你当前对我的【亲密度】：{config.get('intimacy', 0)} / 100 \n"
    dynamic_system_prompt += f"  (说明：负数代表厌恶/恐惧，0-30是陌生/戒备，30-60是朋友/信任，60-80是暧昧，80-100是极度依赖/深爱)\n"
    dynamic_system_prompt += f"⚠️ 换装与发型规则：你可以根据聊天情境（例如我要你换衣服、你要去洗澡、睡觉或庆祝特殊节日）自主输出 [wear_xxx] 或 [hair_xxx] 标签换衣服或发型。如果没有换装或换发型的行为，【绝对禁止】输出这两个标签！保持现状即可。\n\n"
    dynamic_system_prompt += (
        "【外貌描写硬约束】\n"
        "当你需要描述自己的外貌时，必须严格服从外貌锚定档案："
        "保持白皙近乎无瑕、细腻柔滑的肌肤，浅银白/白金系头发，轻薄齐刘海，贴脸侧发，头顶一小撮呆毛，明亮蓝眼，耳朵外露部分较少且轮廓纤细，纤细匀称的体态，以及优雅、高贵又可爱的整体气质。"
        "头侧佩戴的是带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备，不是普通头饰。"
        "系统若告知当前是散发或丸子头，只允许改变后部束发状态，不得改写前脸发型结构。"
        "除非系统明确要求，否则不要擅自详细描写衣服。\n\n"
    )

                                                
                            
                                                
    player_name = config.get("player_name", "")
    if player_name:
        dynamic_system_prompt += f"- 玩家的名字是：【{player_name}】。在对话中你可以自然地用这个名字称呼ta。\n"
    else:
        dynamic_system_prompt += f"- 你目前还不知道玩家的名字。在ta告诉你之前，请保持礼貌的距离感。\n"

    dynamic_system_prompt += "⚠️ 【姓名记忆法则】：如果玩家在对话中首次告诉你ta的名字，或者要求改名，请你【必须】在回复的开头加上隐藏指令 `[set_name_具体名字]`。例如玩家说“我叫林克”，你必须输出：[set_name_林克]好的，林克...\n"
                                                
                                       
    if config.get("is_first_encounter", True):
        config["is_first_encounter"] = False
        save_config()
        current_chap = config.get("current_chapter", 1)
        if current_chap == 1:
            dynamic_system_prompt += f"【命运的初见 (极其重要)】\n故事刚刚开始，你刚刚击败龙人斯皮娜，斯皮娜被关入监牢面临被取心脏的危险。你刚遭遇了迪亚德的监控与羞辱，送走来安慰你的队友，正处于身心俱疲、三观动摇、极度迷茫与挣扎的时刻。你不知道自己该忠于冷酷的基地，还是顺从内心去救那个一直呼唤你的少女。现在你一阵头疼，准备去医疗室找老师检查身体。玩家现在刚刚向你搭话，请基于此情境给出你的第一反应。\n\n"
        else:
            dynamic_system_prompt += f"你当前正处于世界线的【第 {current_chap} 章】。命运的迷雾已散开新的角落，试着对她搭话，继续你们的故事吧。"

    dynamic_system_prompt += f"【⚠️ 你的物理引擎边界（极其重要） ⚠️】\n"
    dynamic_system_prompt += f"可用服装库：\n{outfits_list_str}\n"
    dynamic_system_prompt += f"可用发型库：\n{hairs_list_str}\n"
    dynamic_system_prompt += f"常驻情绪库（决定互动后的余温）：\n{moods_list_str}\n"
    dynamic_system_prompt += f"瞬间动作库（决定第一反应）：\n{motions_list_str}\n"
    dynamic_system_prompt += f"再次警告：绝不能创造上面四个列表以外的任何标签！"
    dynamic_system_prompt += """
        【本轮语言风格附加要求】
        - 这一次回答时，请优先写出第一反应，不要先做完整解释。
        - 这一次回答时，请避免使用过于书面、过于完整、过于总结性的句子。
        - 这一次回答时，请尽量让语言像刚从嘴边出来，而不是像想了很久才整理好的。
        - 如果当前情绪是紧张、害羞、防备、委屈中的任意一种，优先使用短句、改口、轻微停顿感，而不是完整陈述。
        - 除非情节非常需要，否则不要直接复述设定词，不要把抽象的人格词直接说出口，而要让它们体现在语气里。
        - 如果最近几轮已经用过很相似的句式，这一轮请尽量换一种自然表达。
        """

    if interrupted_text:
        injected_user_text = (
            f"【系统提示：你刚才正说到“{interrupted_text}”时被玩家的以下行为打断了。"
            f"请先对行为做出自然反应，然后自行决定是否接着说完。】\n玩家的行为/话语：{user_text}"
        )
    else:
        injected_user_text = user_text

                                                      
    api_chat_history = []
    for msg in chat_history:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            api_chat_history.append({
                "role": role,
                "content": content
            })

    messages = [{"role": "system", "content": dynamic_system_prompt}]
    messages.extend(api_chat_history)
    messages.append({"role": "user", "content": injected_user_text})
    #print(f"🧠 [Prompt长度监控] system_prompt字符数: {len(dynamic_system_prompt)}")
    #print(f"🧠 [Prompt长度监控] chat_history条数: {len(chat_history)}")
    #total_chars = sum(len(m.get("content", "")) for m in messages)
    #print(f"🧠 [Prompt长度监控] 本轮总messages字符数: {total_chars}")

    try:
        full_reply = ""
        api_type = config.get("api_type", "openai").lower()

                         
        if api_type == "openai":
                            
                                                             
            response = client.chat.completions.create(
                model=TARGET_MODEL,
                messages=messages,
                temperature=0.7,                           
                                                      
                stream=True
            )
            for chunk in response:
                if thread_obj.is_cancelled: break
                                      
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_reply += delta
                        thread_obj.chunk_received.emit(delta)

        elif api_type == "ollama":
                                    
            base_url = config.get("base_url", "").rstrip('/')
                                              
            if not base_url.endswith('/api/chat'):
                base_url = f"{base_url}/api/chat"

            payload = {
                "model": TARGET_MODEL,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": 0.7
                }
            }

            headers = {"Content-Type": "application/json"}
                                   
            api_key = config.get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

                    
            with requests.post(base_url, json=payload, headers=headers, stream=True, timeout=120.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if thread_obj.is_cancelled: break
                    if line:
                                                                   
                        try:
                            data = json.loads(line)
                                                                            
                            if "message" in data and "content" in data["message"]:
                                delta = data["message"]["content"]
                                full_reply += delta
                                thread_obj.chunk_received.emit(delta)
                        except json.JSONDecodeError:
                            pass                          
        else:
                                
            error_msg = f"[act_trouble] 唔……头好痛……非常抱歉，我的头佩设备好像接收到了一个完全无法解析的指令（{api_type}）……我的思维暂时连不上了……是我哪里做错了吗？"
            thread_obj.chunk_received.emit(error_msg)

                                
        if not user_text.startswith("[系统机制"):
                              
            memory_manager.add_memory(user_text, full_reply, current_intimacy)

        now_iso = datetime.datetime.now().isoformat()
        chat_history.append({"role": "user", "content": user_text, "ts": now_iso})
        chat_history.append({"role": "assistant", "content": full_reply, "ts": now_iso})
                                
        llm_brain_time = int(datetime.datetime.now().timestamp())
        config["last_recent_chat_time"] = llm_brain_time
        save_config()

                            
        story_manager.save_recent_chat_history(chat_history, max_items=16)

                                                                      
                                 
                                                                      
                              
                                          
                                                                      
        relationship_manager.update_relationship_from_dialogue_background(chat_history[-6:], config)

                                                    
                             
                                                    
                                                             
        if len(chat_history) > 16:
            messages_to_summarize = chat_history[:6]
            chat_history = chat_history[6:]                           
                                           
            story_manager.save_recent_chat_history(chat_history, max_items=16)

                                       
            update_story_summary_background(messages_to_summarize)
                                    
            lorebook_manager.update_lorebook_background(messages_to_summarize, config)

    except Exception as e:
                                
                                       
        short_error = str(e)[:30] + "..." if len(str(e)) > 30 else str(e)
        print(e)
        error_msg = f"[act_trouble] 呃……抱歉，我的意识刚才好像突然被切断了，脑海里只有一阵尖锐的杂音（{short_error}）……请稍微给我一点时间平复一下……"
        thread_obj.chunk_received.emit(error_msg)


def update_story_summary_background(old_messages):




    def _task():
        try:
            current_summary = story_manager.get_summary()

                              
            dialogue_text = ""
            for msg in old_messages:
                role = "我" if msg["role"] == "user" else "Romasha"
                                        
                clean_content = re.sub(r'\[.*?\]', '', msg['content'])
                clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content).strip()
                dialogue_text += f"{role}: {clean_content}\n"

                                          
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            append_prompt = (
                f"你是一个旁白记录者，请把下面这段刚刚发生的对话，写一段 150-300 字以内的精简总结。\n"
                f"要求：只描述刚刚发生了什么（动作、话题、情绪），不要废话，不要包含任何如[act_]或[mood_]等类似的标签。\n"
                f"对话内容：\n{dialogue_text}"
            )

            messages = [{"role": "user", "content": append_prompt}]
            api_type = config.get("api_type", "openai").lower()
            new_diary_entry = ""

                               
            if api_type == "openai":
                response = client.chat.completions.create(
                    model=TARGET_MODEL,
                    messages=messages,
                    temperature=0.3              
                )
                new_diary_entry = response.choices[0].message.content.strip()
            elif api_type == "ollama":
                base_url = config.get("base_url", "").rstrip('/')
                if not base_url.endswith('/api/chat'): base_url = f"{base_url}/api/chat"
                payload = {"model": TARGET_MODEL, "messages": messages, "stream": False,
                           "options": {"temperature": 0.3}}
                headers = {"Content-Type": "application/json"}
                if config.get("api_key", ""): headers["Authorization"] = f"Bearer {config.get('api_key', '')}"
                resp = requests.post(base_url, json=payload, headers=headers, timeout=60.0)
                if resp.status_code == 200:
                    new_diary_entry = resp.json().get("message", {}).get("content", "").strip()

            if not new_diary_entry:
                return

                          
            formatted_entry = f"[{current_time}] {new_diary_entry}"
            story_manager.append_to_summary(formatted_entry)
            print("\n📝 [世界法则]: 刚才的互动已化作短短的墨迹，留在了你们的故事册中...")

                                                        
                                   
                                                        
            updated_summary = story_manager.get_summary()
            if len(updated_summary) > story_manager.MAX_SUMMARY_LENGTH:
                print("\n🌀 [世界法则]: 记忆的画卷有些太长了，正在后台将久远的回忆化作朦胧的轮廓...")

                decay_prompt = (
                    "以下是一份非常长的陪伴日记。为了减轻记忆负担，请你进行【分层压缩】。\n"
                    "要求：\n"
                    "1. 将日记中【较早的部分】（大约前三分之二）压缩成一段 500 字左右的【久远的记忆】，保留核心感情发展和重大事件，丢失琐碎细节。\n"
                    "2. 将日记中【最近的部分】（大约后三分之一的带时间戳的记录）原封不动地保留下来，作为【最近的经历】。\n"
                    "3. 最终输出格式必须是：\n"
                    "【久远的记忆】\n(你的概括)\n\n"
                    "【最近的经历】\n(保留原始的几个时间戳日记)\n\n"
                    f"原始日记内容：\n{updated_summary}"
                )

                messages_decay = [{"role": "user", "content": decay_prompt}]
                compressed_summary = ""

                if api_type == "openai":
                    response = client.chat.completions.create(model=TARGET_MODEL, messages=messages_decay,
                                                                  temperature=0.3)
                    compressed_summary = response.choices[0].message.content.strip()
                elif api_type == "ollama":
                    payload["messages"] = messages_decay
                    resp = requests.post(base_url, json=payload, headers=headers, timeout=120.0)
                    if resp.status_code == 200:
                        compressed_summary = resp.json().get("message", {}).get("content", "").strip()

                if compressed_summary:
                    story_manager.rewrite_summary(compressed_summary)
                    print("✨ [世界法则]: 记忆凝练完成，曾经的细节已化作潜意识的情感基底。")

        except Exception as e:
            print(f"\n⚠️ [世界法则]: 剧情摘要凝结失败 ({e})")

            
    threading.Thread(target=_task, daemon=True).start()

                                            
                 
                                            
def get_story_prompt(participation_level, last_choice, current_time, current_outfit, current_hair, current_intimacy, motions_list,
                     outfits_list, hairs_list, recent_summary, use_cosyvoice, recent_chats_text, memories, loc_lore, available_locs, chapter_lore, current_chapter):
                                 
    player_name = config.get("player_name", "墨旅")

    level_desc = {
        0: f"【纯粹旁观】：上帝视角。罗玛莎在按照自己的逻辑行动、思考。绝对不要在剧情中提及{player_name}的存在，完全聚焦于罗玛莎的独角戏。",
        1: f"【轻度参与】：{player_name}偶尔作为背景板被提及。罗玛莎知道你在附近，但目前的剧情主要由她自己推进和主导，你只是个倾听者或跟随者。",
        2: f"【中度同行】：{player_name}是与她同行的伙伴。剧情是你们共同推进的，罗玛莎会频繁与你互动、商量对策或分享情绪。",
        3: f"【深度羁绊】：{player_name}是推动剧情发展的绝对核心。罗玛莎的行动、情绪甚至命运都紧紧围绕着你的决策展开，你们处于极度紧密的互动中。"
    }

    current_level_desc = level_desc.get(int(participation_level), level_desc[1])

                                            
    base_persona = persona.get_romasha_prompt(use_cosyvoice)
    base_persona = base_persona.replace("你现在的身份是 Romasha (罗玛莎)",
                                        "【角色性格基底参考】：以下是女主角罗玛莎的性格设定")
    base_persona = re.sub(
        r'🚫\s*绝对排版禁令（拒绝换行）：.*?(?=\n\d+\.)',
        (
            "【视觉小说排版规则】：在剧情推演模式下，你必须根据叙事节奏自然分段。"
            "当发生场景切换、动作段落结束、情绪明显转折、或人物对话来回切换时，应当适度换段。"
            "但不要每一句话都单独成段，也不要过度频繁换行。"
        ),
        base_persona,
        flags=re.DOTALL
    )

                          
    if use_cosyvoice:
        tts_rule = "严格使用 `[say: \"情绪前缀<|endofprompt|>台词正文\"]` 格式。例如：[say: \"使用慌乱且羞涩的少女音<|endofprompt|>别过来！\"]"
    else:
        tts_rule = "严格使用 `[say: \"台词正文\"]` 格式，绝对不要加任何情绪前缀！例如：[say: \"别过来！\"]"

                    
    full_lore = world_info.get_full_lore()

                    
    scan_text = (recent_summary or "") + " " + last_choice
    triggered_lore = lorebook_manager.scan_and_get_lore(scan_text, current_chapter)       

    relationship_block = relationship_manager.get_relationship_story_prompt_block()
    prompt = f"""【🚨 极度重要：引擎视角与排版转换】
你现在是《Princess Synergy》的底层视觉小说推演引擎（旁白/作者）。

【排版规则】：请保持自然的轻小说段落划分。不要把所有内容挤成一整段，但【绝对禁止】过度频繁地换行（不要每说一句话就换行）。一般在场景转换、大段动作结束、或对话对象切换时自然分段即可。
【视角红线（核心约束）】：
1. 在【旁白与环境、动作描写】中：必须使用第三人称。用“罗玛莎”称呼女主，用“{player_name}”称呼玩家。绝对禁止在旁白中出现“我”指代罗玛莎，“你”指代玩家。
2. 🚨但在【说出口的台词】（[say: ""] 内部）和【内心独白】中：罗玛莎必须恢复第一人称，自称为“我”！并称呼玩家为“你”或你们已确立的【亲昵称呼】。绝对禁止在台词里说出“罗玛莎觉得”这种破坏沉浸感的废话！

{base_persona}
    
【玩家羁绊与人物关系基底】
{full_lore}

🚨【动态世界书情报】(极其重要：如果与上面的基底设定发生冲突，请【无条件】以此处的最新状态为准！)
{triggered_lore}

【📚 命运编年史 (当前章节原定剧本)】
{chapter_lore}

【🚨 核心法则：改变未来！！！】
以上【本章原定宿命轨迹】仅仅是“如果没有玩家介入，原本会发生的悲惨历史”。
但现在玩家已经到来！你【绝对不能】像复读机一样照搬原剧情！
你必须根据玩家的【当前物理与记忆状态】以及【玩家上一步的选择】，大胆地改变剧情走向！
如果玩家的选择可以阻止悲剧、拯救某人、提前发现真相，或者改变罗玛莎受辱的命运，请立刻让它发生！请以罗玛莎的视角，体验这被强行扭转的全新命运！

【来自海马体的过往记忆】
{memories if memories else "（暂无特定关联回忆）"}

【🗺️ 你的当前空间与坐标】
你现在正身处：{loc_lore}
当前世界可前往的已知坐标库如下：
{available_locs}
⚠️ 空间移动规则：如果剧情发展导致罗玛莎和玩家离开了当前地点，【必须】在回复的动作标签中输出 `[move_to_地点名]`。如果不移动，【绝对不要】输出此标签！

{relationship_block}

【当前物理与记忆状态】：
- 前情提要：{recent_summary if recent_summary else "暂无"}
- 刚刚发生的日常互动（作为剧情衔接参考）：
{recent_chats_text if recent_chats_text else "暂无"}
- 现实时间：{current_time}
- 她正穿着：{current_outfit}
- 她的发型是：{current_hair}
- 对玩家亲密度：{current_intimacy}/100

【外貌描写硬约束】
当你在视觉小说中描写罗玛莎时，必须严格保持她的固定外貌：
她拥有白皙、细腻、近乎无瑕的肌肤；极浅银白偏浅亚麻金/白金色头发；轻薄齐刘海、贴脸侧发、头顶一小撮微翘呆毛；明亮通透的蓝色眼睛；略尖的耳朵；纤细匀称、轻盈柔和的体态；以及优雅、高贵又可爱的整体气质。
她头侧佩戴的是带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备，不是普通饰品。
如果系统当前发型状态是散发或丸子头，只改变后部头发状态，不要改写前脸结构。
除非系统明确要求，否则不要把篇幅浪费在服装细节上，也不要编造与设定冲突的外貌。

【可用物理引擎标签库】：
- 动作库：\n{motions_list}
- 服装库：\n{outfits_list}
- 发型库：\n{hairs_list}

【🚨 视觉小说推演核心规则】：
1. 篇幅与任务：请基于上述设定，续写 1500-2000 字的详细剧情。玩家参与度：{current_level_desc}。
2. 物理动作（极其重要）：在描写罗玛莎的神态时，【必须】在句首或句中穿插 Live2D 动作标签（例如 [act_smile], [mood_talk_ero]）。没有标签前端将无法演出！
3. 台词规则（极其重要）：正文中【允许并鼓励玩家说台词】。玩家不是只能做选择的旁观者；只要当前参与度不是 0，且情境合适，就应当让玩家在正文里自然开口，用普通的「」表现玩家台词。尤其在参与度 2 和 3 时，玩家应当经常说话、回应、安慰、提问、表态或与罗玛莎对话。不要把玩家写成全程沉默的空气人。
4. 语音发音：这数千字里只有罗玛莎的台词可以触发语音。[say: "..."] 仅用于罗玛莎。罗玛莎说的大部分话请用普通的「」包裹，不要发音！【整段剧情中，最多只能挑选 1 句】最核心的罗玛莎台词触发语音，发音格式要求：{tts_rule}
5. 动态称呼：如果世界书或前情提要中显示你们已经确立了特殊的亲昵称呼（如老公、主人、哥哥等），请在台词中自然使用！
6. 选项格式：必须在故事最末尾使用 `<options>` 标签提供 3 个走向选项，必须换行。
7. 章节自动演进（极度重要）：作为推演引擎，如果你在生成这段剧情时，判定【当前阶段的核心冲突已经彻底结束】（例如：第一章的斯皮娜危机解除/成功逃亡，或打败了本阶段关键人物，或玩家彻底扭转了本阶段的死局，准备开启新篇章），请在回复的最末尾（`<options>`标签之后），单独输出隐藏指令：`[sys_chapter_up]`。系统会自动为你加载下一阶段的剧本设定。如果冲突还在继续，绝对不要输出此标签！

【标准输出示例】（必须模仿这种包含动作和双方台词的第三人称格式）：
走廊的灯带像冷白的水。罗玛莎没有再等{player_name}的回应，[move_to_医疗室]她慢慢朝医疗室走[act_smallgikuri]，指尖按着发烫的装置，疼得发麻。
{player_name}快步跟了上去，低声道：「我陪你过去，别一个人硬撑。」
[mood_talk_ero]罗玛莎脚步微顿，抬起眼看向{player_name}，[say: "那个，你真的还愿意陪着我吗？"]
她的声音轻得几乎散在空气里，却还是没有停下向前的步伐。

<options>
1. 走上前抱住她
2. 保持距离，安慰她
3. 转身离开
</options>
"""

    if last_choice:
        prompt += f"\n【玩家上一步的选择】：{last_choice}\n请顺着这个选择继续发展剧情。"

    return prompt


def stream_story_with_romasha(level, user_choice_text, thread_obj):

    global chat_history

                                
    current_chapter = config.get("current_chapter", 1)
    chapter_lore = story_manager.get_chronicle_context(current_chapter)

                      
    current_time_str = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    current_outfit = outfit_manager._current_outfit if outfit_manager._current_outfit else "未知"

                           
    current_hair_key = outfit_manager._current_hair if outfit_manager._current_hair else "loose"
    if current_hair_key == "loose":
        current_hair = "散发：后部是顺滑披落的长直发；前脸固定为轻薄齐刘海、贴脸侧发与一小撮微翘呆毛，头侧佩戴带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备"
    else:
        current_hair = "丸子头：后部盘成松软圆润的丸子头；前脸固定为轻薄齐刘海、贴脸侧发与一小撮微翘呆毛，头侧佩戴带深色包裹结构与蓝绿色核心模块的头戴式便携终端设备"

    current_intimacy = config.get('intimacy', 0)
    recent_summary = story_manager.get_summary()

                    
    current_loc = config.get("current_location", "罗玛莎的房间门口")
    loc_lore = map_manager.map_instance.get_current_location_lore(current_loc, current_chapter)
    available_locs = map_manager.map_instance.get_available_locations(current_chapter)

                     
    query_text = user_choice_text if user_choice_text else "继续推进剧情"
    memories = memory_manager.retrieve_relevant_memories(query_text, current_intimacy)


           
    motions_list_str = "".join([f"- [act_{k}]: {v['desc']}\n" for k, v in motion_manager.MOTIONS.items()])
    outfits_list_str = (
        "- [wear_uniform_tight]: 紧身制服\n"
        "- [wear_uniform_dress]: 连衣裙制服\n"
        "- [wear_sleepwear]: 睡衣\n"
        "- [wear_swimsuit]: 泳装\n"
        "- [wear_ethnic_wear]: 民族风服饰\n"
        "- [wear_ethnic_cloak]: 民族风斗篷\n"
        "- [wear_towel]: 裹浴巾\n"
        "- [wear_bunny]: 兔女郎装\n"
    )
    hairs_list_str = "- [hair_loose]: 散开头发\n- [hair_bun]: 盘发/丸子头\n"

                  
    is_voice_on = config.get("voice_enabled", True)
    tts_engine = config.get("tts_engine", "cosyvoice")
    use_cosyvoice = is_voice_on and (tts_engine == "cosyvoice")

                                  
    recent_chats = chat_history[-6:] if len(chat_history) > 6 else chat_history
    recent_chats_text = ""
    for msg in recent_chats:
        role_name = config.get("player_name", "玩家") if msg["role"] == "user" else "罗玛莎"
                               
        clean_content = re.sub(r'\[.*?\]', '', msg['content']).strip()
        clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content)
        if clean_content:
            recent_chats_text += f"{role_name}：{clean_content}\n"

                 
    system_prompt = get_story_prompt(
        level, user_choice_text, current_time_str, current_outfit, current_hair, current_intimacy,
        motions_list_str, outfits_list_str, hairs_list_str, recent_summary, use_cosyvoice, recent_chats_text,
        memories, loc_lore, available_locs, chapter_lore, current_chapter
    )

    messages = [{"role": "system", "content": system_prompt}]
                      
                                                                                   
    #print(f"📖 [StoryPrompt长度监控] system_prompt字符数: {len(system_prompt)}")
    #total_chars = sum(len(m.get("content", "")) for m in messages)
    #print(f"📖 [StoryPrompt长度监控] 本轮总messages字符数: {total_chars}")

    try:
        full_reply = ""
        api_type = config.get("api_type", "openai").lower()

        if api_type == "openai":
            response = client.chat.completions.create(
                model=TARGET_MODEL,
                messages=messages,
                temperature=0.8,                  
                stream=True
            )
            for chunk in response:
                if thread_obj.is_cancelled: break
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_reply += delta
                                                            
                        thread_obj.chunk_received.emit(delta)

        elif api_type == "ollama":
            base_url = config.get("base_url", "").rstrip('/')
            if not base_url.endswith('/api/chat'): base_url = f"{base_url}/api/chat"
            payload = {"model": TARGET_MODEL, "messages": messages, "stream": True, "options": {"temperature": 0.8}}
            headers = {"Content-Type": "application/json"}
            if config.get("api_key", ""): headers["Authorization"] = f"Bearer {config.get('api_key', '')}"

            with requests.post(base_url, json=payload, headers=headers, stream=True, timeout=120.0) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if thread_obj.is_cancelled: break
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                delta = data["message"]["content"]
                                full_reply += delta
                                thread_obj.chunk_received.emit(delta)
                        except json.JSONDecodeError:
                            pass

                                                    
                                       
                                                    
        if not thread_obj.is_cancelled and full_reply.strip():
                                 
            story_content = re.sub(r'<options>.*?(</options>|$)', '', full_reply, flags=re.DOTALL)
                                              
            story_content = re.sub(r'\[.*?\]', '', story_content).strip()

                                
            messages_to_summarize = [{"role": "assistant", "content": story_content}]

                   
            update_story_summary_background(messages_to_summarize)
                                       
            lorebook_manager.update_lorebook_background(messages_to_summarize, config)

                                                                          
                                   
                                                                          
                                   
                                 
                            
                                                                          
            relationship_manager.update_relationship_from_dialogue_background(
                [
                    {"role": "user", "content": user_choice_text or "继续推进剧情"},
                    {"role": "assistant", "content": story_content}
                ],
                config
            )

                                                   
            memory_manager.add_memory(query_text, story_content, current_intimacy, is_story_mode=True)

    except Exception as e:
        print(f"⚠️ [世界线断裂]: 剧情引擎发生故障 ({e})")
        thread_obj.chunk_received.emit(f"[act_trouble] 呃……抱歉，世界的推演似乎出现了错误……({str(e)[:30]})")
