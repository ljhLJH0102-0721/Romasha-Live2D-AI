                         
                                                              
         
                                                              
       
                            
                          
                                          
                                        
                               
                                                                       
                                                              

import os
import json
import sys
import re
import copy
import threading
import hashlib
import requests
from openai import OpenAI

                                                              
                      
                                                              
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

_rel_lock = threading.Lock()

          
REL_FILE = os.path.join(app_dir, "world_data", "relationship_state.json")

                                                              
       
                                                              
              
                                                         
            
                                                              
STAGE_ORDER = {
    "stranger": 0,         
    "trusted": 1,        
    "close": 2,                  
    "lovers": 3,           
    "bonded": 4,            
    "married": 5                
}
                                                              
           
                                                              
     
                                         
                                   
 
     
                 
                                 
                                                              
VALID_ATTITUDES = {
    "normal",        
    "shy",            
    "hurt",              
    "distant",          
    "cold",        
    "dependent"            
}
                                                              
         
                                                              
          
                                  
                                              
                                                              
VALID_TOUCH_ZONES = {
    "head", "face", "hand_left", "hand_right",
    "belly", "leg", "hip", "bust", "crotch"
}
                                                              
        
                                                              
                     
                                                          
 
                          
       
        
        
        
        
            
                                                              
DEFAULT_REL = {
                                                              
                   
                                                              
                    
                      
                   
                                                              
    "current_relationship_stage": "stranger",
                                                              
                      
                                                              
                       
                       
                     
                                                                  
    "highest_relationship_stage": "stranger",
                                                                  
                  
                    
                                                                  
    "physical_intimacy_stage": 0,

                   
    "trust": 0,      
    "attachment": 0,         

                   
    "shyness": 80,                  
    "boundary_softness": 0,                  

            
    "exclusive_bond": False,               
    "married": False,        
    "first_night_completed": False,                       

                                                              
                  
                                                              
                   
              
               
             
                 
                     
                                                              
    "current_attitude": "normal",
                                                              
                   
                                                              
                       
                      
                      
                                                              
    "temporary_distance_level": 0,
                                                              
              
                                                              
           
                            
                                                              
    "temporary_blocked_touch_zones": [],

               
                          
                                               
    "accepted_touch_zones": [
        "head", "face", "hand_left", "hand_right"
    ],

            
    "special_flags": {
        "confessed_each_other": False,            
        "slept_together": False,          
        "kissed": False,          
        "body_familiarity": False                 
    },
                                                                  
                                   
                                                                  
    "last_processed_signature": ""
}


                                                              
        
                                                              
def _ensure_dir():

    os.makedirs(os.path.dirname(REL_FILE), exist_ok=True)


def _save_relationship_state_unlocked(data):





    _ensure_dir()
    with open(REL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _clamp(value, min_value=0, max_value=100):



    try:
        value = int(value)
    except Exception:
        value = min_value
    return max(min_value, min(max_value, value))


def _stage_value(stage_name):




    return STAGE_ORDER.get(stage_name, STAGE_ORDER["stranger"])


def _build_history_signature(recent_history):








    parts = []
    for msg in recent_history:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip()
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(f"{role}:{content.strip()}")
    raw = "||".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()


def _get_stage_floor_by_facts(state):












    floor_stage = "stranger"
                                    
                                       
                         
    if state.get("married", False):
        return "bonded"
                                
    if state.get("first_night_completed", False) or state.get("exclusive_bond", False):
        floor_stage = "close"
    flags = state.get("special_flags", {})
                                    
    if (
            flags.get("confessed_each_other", False)
            or flags.get("kissed", False)
            or flags.get("slept_together", False)
    ):
        if _stage_value("trusted") > _stage_value(floor_stage):
            floor_stage = "trusted"
    return floor_stage


def _clamp_stage_with_floor(target_stage, state):






    if target_stage not in STAGE_ORDER:
        return state.get("current_relationship_stage", "stranger")
    floor_stage = _get_stage_floor_by_facts(state)
    if _stage_value(target_stage) < _stage_value(floor_stage):
        return floor_stage
    return target_stage


                                                              
      
                                                              
def load_relationship_state():










    _ensure_dir()

    if not os.path.exists(REL_FILE):
        return copy.deepcopy(DEFAULT_REL)

    try:
        with open(REL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return copy.deepcopy(DEFAULT_REL)

                                                                  
                                 
                                                                  
        state = copy.deepcopy(DEFAULT_REL)

                                                                  
                     
                                                                  
        for key, value in data.items():
            state[key] = value

                                                                  
                                           
                                                                  
        default_flags = copy.deepcopy(DEFAULT_REL["special_flags"])
        loaded_flags = data.get("special_flags", {})
        if not isinstance(loaded_flags, dict):
            loaded_flags = {}
        default_flags.update(loaded_flags)
        state["special_flags"] = default_flags

                                                                  
                        
                                                                  
        if not isinstance(state.get("accepted_touch_zones"), list):
            state["accepted_touch_zones"] = copy.deepcopy(DEFAULT_REL["accepted_touch_zones"])

        if not isinstance(state.get("temporary_blocked_touch_zones"), list):
            state["temporary_blocked_touch_zones"] = []

                                                                  
                       
                                                                  
        if state.get("current_relationship_stage") not in STAGE_ORDER:
            state["current_relationship_stage"] = "stranger"

        if state.get("highest_relationship_stage") not in STAGE_ORDER:
            state["highest_relationship_stage"] = "stranger"

        if state.get("current_attitude") not in VALID_ATTITUDES:
            state["current_attitude"] = "normal"

                                                                  
                                     
                                                                  
        state["trust"] = _clamp(state.get("trust", 0))
        state["attachment"] = _clamp(state.get("attachment", 0))
        state["shyness"] = _clamp(state.get("shyness", 80))
        state["boundary_softness"] = _clamp(state.get("boundary_softness", 0))
        state["temporary_distance_level"] = _clamp(state.get("temporary_distance_level", 0))
        state["physical_intimacy_stage"] = max(0, min(5, int(state.get("physical_intimacy_stage", 0))))

        return state

    except Exception:
        return copy.deepcopy(DEFAULT_REL)


def save_relationship_state(data):



    _ensure_dir()
    try:
        with _rel_lock:
            _save_relationship_state_unlocked(data)
    except Exception as e:
        print(f"⚠️ [关系状态机]: 保存关系状态失败: {e}")


def clear_relationship_state():




    save_relationship_state(copy.deepcopy(DEFAULT_REL))


                                                              
          
                                                              
         
                                    
                                
                                                              
def set_relationship_milestone(
        current_relationship_stage=None,
        physical_intimacy_stage=None,
        trust_delta=0,
        attachment_delta=0,
        shyness_delta=0,
        boundary_softness_delta=0,
        married=None,
        exclusive_bond=None,
        first_night_completed=None,
        add_touch_zones=None,
        flag_updates=None,
        allow_stage_rollback=False,
        processed_signature=None,
                                                                  
                          
                                                                  
        current_attitude=None,
        temporary_distance_delta=0,
        temporary_blocked_touch_zones=None
):































    with _rel_lock:
        state = load_relationship_state()

                                                                      
                             
                                                                      
                                               
                           
                                                                      
        if current_relationship_stage in STAGE_ORDER:
            old_current_stage = state.get("current_relationship_stage", "stranger")

            if allow_stage_rollback:
                                       
                state["current_relationship_stage"] = _clamp_stage_with_floor(
                    current_relationship_stage,
                    state
                )
            else:
                                    
                if _stage_value(current_relationship_stage) > _stage_value(old_current_stage):
                    state["current_relationship_stage"] = current_relationship_stage

                                      
            highest_stage = state.get("highest_relationship_stage", "stranger")
            if _stage_value(state["current_relationship_stage"]) > _stage_value(highest_stage):
                state["highest_relationship_stage"] = state["current_relationship_stage"]

                                                                      
                                  
                                                                      
        if physical_intimacy_stage is not None:
            try:
                physical_intimacy_stage = int(physical_intimacy_stage)
            except Exception:
                physical_intimacy_stage = 0
            physical_intimacy_stage = max(0, min(5, physical_intimacy_stage))
            state["physical_intimacy_stage"] = max(
                state.get("physical_intimacy_stage", 0),
                physical_intimacy_stage
            )

                                                                      
                    
                                                                      
                                       
                                                                      
        state["trust"] = _clamp(state.get("trust", 0) + trust_delta)
        state["attachment"] = _clamp(state.get("attachment", 0) + attachment_delta)
        state["shyness"] = _clamp(state.get("shyness", 80) + shyness_delta)
        state["boundary_softness"] = _clamp(
            state.get("boundary_softness", 0) + boundary_softness_delta
        )

                                                                  
                  
                                                                  
        if current_attitude in VALID_ATTITUDES:
            state["current_attitude"] = current_attitude
        state["temporary_distance_level"] = _clamp(
            state.get("temporary_distance_level", 0) + temporary_distance_delta
        )
        if temporary_blocked_touch_zones is not None:
            safe_blocked = [z for z in temporary_blocked_touch_zones if z in VALID_TOUCH_ZONES]
            state["temporary_blocked_touch_zones"] = list(dict.fromkeys(safe_blocked))

                                                                      
                        
                                                                      
                                        
                                                                
                                                                      
        if married is True:
            state["married"] = True
            state["highest_relationship_stage"] = "married"
                                        
            if _stage_value(state.get("current_relationship_stage", "stranger")) < _stage_value("bonded"):
                state["current_relationship_stage"] = "bonded"

        if exclusive_bond is True:
            state["exclusive_bond"] = True

        if first_night_completed is True:
            state["first_night_completed"] = True
            state["physical_intimacy_stage"] = max(state.get("physical_intimacy_stage", 0), 5)

                                                                      
                              
                                                                      
                             
                              
                           
                                                                      
        if add_touch_zones:
            current = state.get("accepted_touch_zones", [])
            safe_new = [z for z in add_touch_zones if z in VALID_TOUCH_ZONES]
            merged = list(dict.fromkeys(current + safe_new))
            state["accepted_touch_zones"] = merged

                                                                      
                   
                                                                      
        if isinstance(flag_updates, dict):
            state_flags = state.get("special_flags", {})
            for k, v in flag_updates.items():
                                          
                if isinstance(v, bool):
                    if v is True:
                        state_flags[k] = True
                    elif k not in state_flags:
                        state_flags[k] = False
                else:
                    state_flags[k] = v
            state["special_flags"] = state_flags

                                                                      
                             
                                                                      
        if processed_signature:
            state["last_processed_signature"] = processed_signature

        _save_relationship_state_unlocked(state)
        return state


                                                              
               
                                                              
                           
                          
                                                              
def get_relationship_prompt_block():













    s = load_relationship_state()

    stage_desc_map = {
        "stranger": "陌生与戒备",
        "trusted": "开始信任",
        "close": "亲近依赖",
        "lovers": "已确认恋人关系",
        "bonded": "深度专属伴侣关系",
        "married": "已婚伴侣"
    }

    attitude_desc_map = {
        "normal": "关系整体稳定，默认自然相处",
        "shy": "更容易害羞，但并非真正疏远",
        "hurt": "当前内心受伤、敏感、需要安抚",
        "distant": "当前刻意拉开距离，不想太亲近",
        "cold": "当前明显冷淡克制",
        "dependent": "当前更依赖对方、容易寻求安慰"
    }

    physical_desc_map = {
        0: "尚无明确亲密接触经历",
        1: "已有牵手等轻度身体接触",
        2: "已能自然拥抱与贴近",
        3: "已有接吻经历",
        4: "已有同床共眠经历",
        5: "已经发生过夫妻级亲密行为"
    }

    touch_zone_map = {
        "head": "头部",
        "face": "脸颊",
        "hand_left": "左手",
        "hand_right": "右手",
        "belly": "腰腹",
        "leg": "腿部",
        "hip": "腰臀",
        "bust": "胸前",
        "crotch": "私密部位"
    }

                                                                            
    current_stage = s.get("current_relationship_stage", "stranger")
    highest_stage = s.get("highest_relationship_stage", "stranger")
    current_attitude = s.get("current_attitude", "normal")
    physical_desc = physical_desc_map.get(s.get("physical_intimacy_stage", 0), "未知的身体亲密阶段")
    accepted_zones_raw = s.get("accepted_touch_zones", [])
    accepted_zones_cn = [touch_zone_map.get(x, x) for x in accepted_zones_raw]
    accepted_text = "、".join(accepted_zones_cn) if accepted_zones_cn else "无"
    blocked_zones_raw = s.get("temporary_blocked_touch_zones", [])
    blocked_zones_cn = [touch_zone_map.get(x, x) for x in blocked_zones_raw]
    blocked_text = "、".join(blocked_zones_cn) if blocked_zones_cn else "无"
    flags = s.get("special_flags", {})
    confessed_each_other = flags.get("confessed_each_other", False)
    kissed = flags.get("kissed", False)
    slept_together = flags.get("slept_together", False)
    body_familiarity = flags.get("body_familiarity", False)

    prompt = (
        "【当前关系硬事实】\n"
                                         
        f"- 你与玩家当前的关系气氛阶段：{stage_desc_map.get(current_stage, '未知')}\n"
        f"- 你们历史上曾达到过的最高关系阶段：{stage_desc_map.get(highest_stage, '未知')}\n"
        f"- 你们当前的身体亲密阶段：{physical_desc}\n"
        f"- 当前信任程度：{s.get('trust', 0)}/100\n"
        f"- 当前依赖与爱意程度：{s.get('attachment', 0)}/100\n"
        f"- 当前害羞敏感程度：{s.get('shyness', 80)}/100\n"
        f"- 面对亲密对象时的边界放松程度：{s.get('boundary_softness', 0)}/100\n"
        f"- 你此刻面对玩家的即时态度：{attitude_desc_map.get(current_attitude, '未知')}\n"
        f"- 你当前临时想拉开距离的程度：{s.get('temporary_distance_level', 0)}/100\n"
        f"- 你当前暂时不希望被触碰的区域：{blocked_text}\n"
        f"- 在温柔、熟悉、关系成立的前提下，不再自动按陌生冒犯理解的接触区域：{accepted_text}\n"
        f"- 是否已经形成专属羁绊：{'是' if s.get('exclusive_bond', False) else '否'}\n"
        f"- 是否已经结为伴侣或婚姻关系：{'是' if s.get('married', False) else '否'}\n"
        f"- 是否已经完成夫妻级亲密里程碑：{'是' if s.get('first_night_completed', False) else '否'}\n"
        f"- 是否已经彼此明确告白：{'是' if confessed_each_other else '否'}\n"
        f"- 是否已经有过接吻：{'是' if kissed else '否'}\n"
        f"- 是否已经有过同床共眠：{'是' if slept_together else '否'}\n"
        f"- 是否已经对彼此身体接触较为熟悉：{'是' if body_familiarity else '否'}\n\n"
        "【关系解释规则（必须服从）】\n"
        "1. 当前关系气氛可以受伤、冷淡、别扭、想拉开距离，但这不等于过去已经成立的关系事实被抹除。\n"
        "2. 如果你们历史上已经确认过恋人关系、专属伴侣关系、婚姻关系，或已经发生过明确的深度亲密经历，那么后续互动中，你不得长期退回到“像刚认识时一样”的陌生防卫逻辑。\n"
        "3. 如果你此刻只是受伤、冷淡、羞耻、疲惫、赌气或需要空间，这表示你现在的表达会更收紧、更克制、更需要安抚，并不表示你否认已经发生过的一切。\n"
        "4. 在关系已经成立的前提下，面对玩家温柔、克制、带珍惜感的贴近、安抚、牵手、拥抱，或其他已经有先例的亲密行为时，你可以表现为害羞、脸红、结巴、轻轻推拒、嘴硬、要求慢一点、要求更温柔，但不应长期机械地像面对陌生人侵犯一样处理。\n"
        "5. 对于你当前暂时不希望被碰的部位，应优先表现为回避、收紧、防备、要求停止、要求尊重，而不是把整个关系都重置成陌生状态。\n"
        "6. 只有当玩家的行为明显带有粗暴、羞辱、强迫、命令、炫耀、物化、无视你感受等意味时，你才应明显升级为强防御与炸毛。\n"
        "7. “已熟悉的接触区域”表示在正常、温柔、熟悉、双方关系成立时，这些接触不再自动按陌生冒犯理解；这不代表你在任何时候都必须接受。\n"
        "8. “当前暂时不希望被碰的部位”的优先级高于“已熟悉的接触区域”。也就是说，就算过去熟悉过，这一刻你也仍然可以不想让他碰那里。\n"
        "9. 关系硬事实的优先级高于单独的亲密度数值。亲密度可以波动，但不能直接覆盖已经成立的重要关系事实。\n"
    )

    return prompt


def get_relationship_story_prompt_block():








    s = load_relationship_state()

    stage_desc_map = {
        "stranger": "陌生与戒备",
        "trusted": "开始信任",
        "close": "亲近依赖",
        "lovers": "已确认恋人关系",
        "bonded": "深度绑定的专属伴侣关系",
        "married": "已婚伴侣关系"
    }

    physical_desc_map = {
        0: "尚无明确亲密接触经历",
        1: "已经有过牵手等轻度身体接触",
        2: "已经可以自然拥抱、贴近",
        3: "已经有过接吻",
        4: "已经有过同床共眠",
        5: "已经发生过明确的深度亲密行为"
    }

    flags = s.get("special_flags", {})

    prompt = (
        "【关系连续性硬事实（剧情模式高优先级）】\n"
        f"- 罗玛莎与玩家当前的关系气氛：{stage_desc_map.get(s.get('current_relationship_stage', 'stranger'), '未知')}\n"
        f"- 他们历史上曾达到过的最高关系阶段：{stage_desc_map.get(s.get('highest_relationship_stage', 'stranger'), '未知')}\n"
        f"- 他们当前的身体亲密程度：{physical_desc_map.get(s.get('physical_intimacy_stage', 0), '未知')}\n"
        f"- 罗玛莎此刻面对玩家的即时态度：{s.get('current_attitude', 'normal')}\n"
        f"- 罗玛莎当前想拉开距离的程度：{s.get('temporary_distance_level', 0)}/100\n"
        f"- 罗玛莎当前短期不希望被碰的区域：{', '.join(s.get('temporary_blocked_touch_zones', [])) or '无'}\n\n"
        f"- 是否已形成专属羁绊：{'是' if s.get('exclusive_bond', False) else '否'}\n"
        f"- 是否已是伴侣或婚姻关系：{'是' if s.get('married', False) else '否'}\n"
        f"- 是否已完成关键亲密里程碑：{'是' if s.get('first_night_completed', False) else '否'}\n"
        f"- 是否已彼此明确告白：{'是' if flags.get('confessed_each_other', False) else '否'}\n"
        f"- 是否已有接吻：{'是' if flags.get('kissed', False) else '否'}\n"
        f"- 是否已有同床共眠：{'是' if flags.get('slept_together', False) else '否'}\n\n"

        "【剧情关系规则】\n"
        "1. 当前关系气氛可以降温、可以别扭、可以受伤、可以冷淡，但这不代表他们之间从未建立过那些已经成立的事实。\n"
        "2. 如果他们已经确认恋爱、专属关系、婚姻关系，或已经发生过明确的深度亲密经历，那么剧情中的互动方式必须体现这种连续性。\n"
        "3. 因此，即使罗玛莎此刻仍会害羞、嘴硬、退缩、轻轻推拒、需要安抚，她也不应被写得像完全陌生人那样长期强烈防备。\n"
        "4. 真正会触发明显防御升级的，应当是粗暴、羞辱、强迫、无视感受，而不是一切亲近本身。\n"
        "5. 如果当前关系气氛较冷，应写成表达收紧、别扭、克制、需要安抚，而不是直接否认过去已经发生的关系事实。\n"
        "6. current_attitude、temporary_distance_level、temporary_blocked_touch_zones 只表示她此刻的情绪与短期边界，"
        "不表示历史关系被抹除。剧情中应把它写成别扭、压抑、轻拒、回避、需要安抚，而不是写成完全陌生式的惊恐或失忆。\n"
    )
    return prompt


                                                              
            
                                                              
     
              
                                        
                                 
                                                              
def update_relationship_from_dialogue_background(recent_history, config):
    def _task():
        try:
            if not recent_history:
                return
            signature = _build_history_signature(recent_history)
            current_state = load_relationship_state()
                                         
            if signature and signature == current_state.get("last_processed_signature", ""):
                return

            dialogue_text = ""
            for msg in recent_history:
                if not isinstance(msg, dict):
                    continue
                role = "我" if msg.get("role") == "user" else "Romasha"
                clean_content = re.sub(r'\[.*?\]', '', msg.get('content', ''))
                clean_content = re.sub(r'^.*?<\|endofprompt\|>', '', clean_content).strip()
                if clean_content:
                    dialogue_text += f"{role}: {clean_content}\n"

            if not dialogue_text.strip():
                return

            prompt = f"""
你现在是“关系状态提取器”。
请根据下面这段最近发生的对话，判断双方关系是否出现了明确的里程碑变化。
你只能输出 JSON，绝对不要输出任何解释、前言、注释、代码块或额外文本。
允许输出的 JSON 结构如下：
{{
  "current_relationship_stage": "stranger/trusted/close/lovers/bonded/married",
  "physical_intimacy_stage": 0,
  "trust_delta": 0,
  "attachment_delta": 0,
  "shyness_delta": 0,
  "boundary_softness_delta": 0,
  "married": null,
  "exclusive_bond": null,
  "first_night_completed": null,
  "add_touch_zones": [],
  "flag_updates": {{}},
  "allow_stage_rollback": false,
  "current_attitude": "normal/shy/hurt/distant/cold/dependent",
  "temporary_distance_delta": 0,
  "temporary_blocked_touch_zones": []
}}

字段含义说明：
- current_relationship_stage：当前关系气氛阶段，可回退。只能从 stranger、trusted、close、lovers、bonded、married 中选择
  - stranger：陌生
  - trusted：开始信任
  - close：亲近依赖
  - lovers：已明确确认恋人关系
  - bonded：深度专属伴侣关系
  - married：已婚
- physical_intimacy_stage：身体亲密历史最高阶段
  - 0：无
  - 1：牵手
  - 2：拥抱
  - 3：接吻
  - 4：同床共眠
  - 5：夫妻级亲密行为
- trust_delta：信任变化值，可正可负
- attachment_delta：依赖/爱意变化值，可正可负
- shyness_delta：害羞敏感程度变化值，可正可负
- boundary_softness_delta：面对亲密对象时边界放松程度变化值，可正可负
- married：是否已婚（true / false），若无法确认则填 null
- exclusive_bond：是否形成专属排他羁绊（true / false），若无法确认则填 null
- first_night_completed：是否已经完成夫妻级亲密里程碑（true / false），若无法确认则填 null
- add_touch_zones：新增的、在正常亲密关系下不再自动按陌生冒犯理解的接触区域，例如 ["belly", "hip"]
- flag_updates：补充标记，例如
  {{
    "confessed_each_other": true,
    "kissed": true,
    "slept_together": true,
    "body_familiarity": true
  }}
- allow_stage_rollback：如果这一轮明显关系降温，可设为 true
- current_attitude：这一轮之后，她当前的即时态度
- temporary_distance_delta：临时拉开距离程度变化值，可正可负
- temporary_blocked_touch_zones：她当前短期不想被碰的区域

判定规则：
1. 必须以“文本中明确发生”为准，不要脑补，不要因为暧昧语气、调情口吻、害羞反应，就自动升级太多。
2. 明确互相告白、正式确认恋爱关系，才能进入 lovers。
3. 明确形成深度专属、彼此认定、关系高度绑定时，才能进入 bonded。
4. 明确结婚、婚礼、夫妻身份成立时，才能进入 married。
5. 明确发生接吻，才能把 kissed 设为 true，或把身体亲密阶段提升到至少 3。
6. 明确同床共眠，才能把 slept_together 设为 true，或把身体亲密阶段提升到至少 4。
7. 明确发生夫妻级亲密行为，才能把 first_night_completed 设为 true，或把身体亲密阶段提升到 5。
8. 如果最近这几句只是延续已有关系，而没有新的明确里程碑，那么 trust_delta、attachment_delta、shyness_delta、boundary_softness_delta 默认都应尽量给 0，不要因为只是继续甜蜜就反复累计。
9. 如果没有新的、明确的关系推进或降温事件，请直接输出空 JSON：{{}}。
10. 如果最近对话中出现了明确的受伤、冷战、疏离、刻意拉开距离、拒绝进一步亲密、关系明显降温，
    你可以让 current_relationship_stage 适度回退，并将 allow_stage_rollback 设为 true。
    但这只表示“当前互动气氛变冷”，不表示历史事实被抹除。已发生的告白、接吻、同床、婚姻、深度亲密经历，不能因为一次争吵就被当作从未发生。
11. 如果只是害羞、嘴硬、短暂别扭，不要轻易回退 current_relationship_stage。
12. 如果她只是现在不想被碰某些部位，请优先用 current_attitude、temporary_distance_delta、
    temporary_blocked_touch_zones 表达，而不是粗暴否认过去所有关系事实。
13. current_attitude 与 current_relationship_stage 可以同时成立。例如：
   - lovers + hurt：仍是恋人，但当前受伤、敏感
   - married + distant：仍是伴侣或夫妻，但这一刻明显想拉开距离

最近对话如下：
{dialogue_text}
"""

            api_type = config.get("api_type", "openai").lower()
            target_model = config.get("target_model", "")
            result_text = ""

            if api_type == "openai":
                client = OpenAI(
                    api_key=config.get("api_key", ""),
                    base_url=config.get("base_url", ""),
                    timeout=60.0
                )
                resp = client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                result_text = resp.choices[0].message.content.strip()

            else:
                base_url = config.get("base_url", "").rstrip('/')
                if not base_url.endswith('/api/chat'):
                    base_url = f"{base_url}/api/chat"

                payload = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
                headers = {"Content-Type": "application/json"}
                if config.get("api_key", ""):
                    headers["Authorization"] = f"Bearer {config.get('api_key', '')}"

                r = requests.post(base_url, json=payload, headers=headers, timeout=60.0)
                if r.status_code == 200:
                    result_text = r.json().get("message", {}).get("content", "").strip()

            m = re.search(r'\{[\s\S]*\}', result_text)
            if not m:
                return

            json_text = m.group(0).strip()

            try:
                data = json.loads(json_text)
            except Exception:
                print(f"⚠️ [关系状态机]: 关系提取器返回了无法解析的 JSON: {result_text[:300]}")
                return

            if not data:
                                            
                state = load_relationship_state()
                state["last_processed_signature"] = signature
                save_relationship_state(state)
                return

            set_relationship_milestone(
                current_relationship_stage=data.get("current_relationship_stage"),
                physical_intimacy_stage=data.get("physical_intimacy_stage"),
                trust_delta=data.get("trust_delta", 0),
                attachment_delta=data.get("attachment_delta", 0),
                shyness_delta=data.get("shyness_delta", 0),
                boundary_softness_delta=data.get("boundary_softness_delta", 0),
                married=data.get("married"),
                exclusive_bond=data.get("exclusive_bond"),
                first_night_completed=data.get("first_night_completed"),
                add_touch_zones=data.get("add_touch_zones"),
                flag_updates=data.get("flag_updates"),
                allow_stage_rollback=data.get("allow_stage_rollback", False),
                processed_signature=signature,
                current_attitude=data.get("current_attitude"),
                temporary_distance_delta=data.get("temporary_distance_delta", 0),
                temporary_blocked_touch_zones=data.get("temporary_blocked_touch_zones")
            )
            print("💞 [关系状态机]: 已根据最近经历更新关系里程碑。")

        except Exception as e:
            print(f"⚠️ [关系状态机]: 更新失败: {e}")

    threading.Thread(target=_task, daemon=True).start()