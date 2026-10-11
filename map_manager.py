                
import os
import json
import sys



                                                                       
                                  
                                                                       
REGION_UNLOCK_CHAPTER = {
                                                         
    "基地核心区（指挥·研究·医疗·档案）": 1,
    "司令室": 1, "研究室": 1, "技术室": 1, "休憩室": 1, "医疗室": 1, "医疗室（石化用）": 1, "档案室": 1, "传送室": 1,

    "基地公共区（大厅·事务·通行）": 1,
    "大厅1F&2F": 1, "大厅1F&2F（周六）": 1, "自动扶梯": 1, "多目的室": 1, "讲义室": 1, "2楼事务室": 1,
    "中央电梯等待室": 1, "公告板": 1, "主柜台": 1, "厕所": 1, "模板地图": 1, "三楼": 1, "3层（初回）": 1,

    "基地训练区": 1,
    "训练室": 1, "右训练室内": 1, "右训练室内（活动用）": 1, "努普龙测试地图": 1,

    "基地生活区（宿舍与个人空间）": 1,
    "罗玛莎的房间": 1, "罗玛莎的房间门口": 1, "男性宿舍": 1, "会议室": 1,
    "卡珠娅的房间": 1, "巴尼拉的房间": 1, "Soot的房间": 1, "安蒂的房间": 1, "男性队员1的房间": 1,
    "队员1的房间(后半）": 1,

    "基地安保与拘禁区": 1,
    "独房": 1,

    "上城区市街与公共设施（索利蒂亚）": 1,
    "上层都市索利蒂亚": 1, "索利提亚": 1, "市街区全景": 1, "喷泉": 1, "喷泉前": 1, "花卉区": 1, "面包店": 1,
    "集合住宅": 1, "海兰达总部": 1,

    "商场与休闲设施（上城区）": 1,
    "商场1F后半(信息台)": 1, "商场3层商店": 1, "泳池接待处": 1, "泳池设施": 1, "男性更衣室": 1,
    "商场4层": 1, "大浴场前台": 1, "大浴场": 1, "游戏区": 1,

    "电视台与媒体设施": 1,
    "TV局": 1, "电视台摄影棚": 1,

                                                       
    "龙人村落与旧文明遗址": 2,
    "斯皮娜的故乡": 2, "吉吉的家": 2, "地下研究室": 2, "第二研究所": 2,

                                                       
    "下城区/储藏区（地下都市）": 3,
    "储藏区": 3, "地下都市中央区块": 3, "地下都市A区块": 3, "地下都市B区块": 3, "地下都市C区块": 3,
    "A区块": 3, "B区块": 3, "C区块": 3, "医院": 3, "更衣室": 3, "厕所事件用A区": 3,
    "自助洗衣店": 3, "垃圾区": 3, "地下城设定用": 3, "休息点": 3, "胶囊旅馆": 3, "旅馆": 3,
    "单间（自由休息用）": 3, "非法商店": 3, "猪鹿蝶": 3, "储存区的猪鹿蝶": 3,

    "下城竞技与赛事设施": 3,
    "斗技场": 3, "斗技场（自由赛第1场）": 3, "斗技场（罗玛莎决胜战）": 3, "走廊・控室": 3, "败者控室": 3,

    "下城风俗与灰色产业区": 3,
    "地下风俗室内": 3, "游郭内装": 3, "游郭控室": 3, "控室": 3, "梅的房间": 3, "竹的房间": 3, "松之间": 3, "竹之间": 3,
    "梅之间": 3, "中庭": 3,
    "花街内装（营业中）": 3, "赌场酒吧": 3, "脱衣剧场入口": 3, "剧院音乐ST": 3,
    "情人旅馆": 3, "许可": 3, "A房间": 3, "B房间": 3, "美容院": 3, "放松理疗馆": 3, "美容护理（事件用）": 3,

                                                           
    "通往研究室的走廊（后半）": 4,
    "大厅1F&2F（周二后半）": 4, "二楼事务室（后半）": 4, "二楼事务室走廊（后半）": 4,
    "3层（后半）": 4, "3层（夜间）": 4, "3层（后半夜用）": 4, "大厅": 4,

    "罗玛莎的房间（后半）": 4, "罗玛莎的房间（审讯后）": 4,
    "4番队宿舍（后半）": 4, "男性队员宿舍（后半）": 4,
    "独房（后半）": 4, "惩罚房": 4, "罗玛莎监禁独房": 4,

    "市街地全景（后半）": 4, "市街地全景后半（夜用）": 4, "长椅": 4,

    "商场2层网咖": 4, "商场2F后半(网咖)": 4, "饮料吧": 4, "7号包厢": 4,
    "商场3F后半": 4, "商场3F后半（泳池）": 4, "女性更衣室": 4,
    "商场3F后半(女性更衣室平泳ぎ3用)": 4, "商场3F后半(女性更衣室ショタ4用)": 4,
    "商场4F后半": 4, "大浴场后半": 4, "大浴场情色综艺用（后半）": 4, "更衣区后半": 4,
    "淋浴室": 4, "淋浴室（夜间）": 4, "淋浴室（后半）": 4,

    "5层后半（电视台演播室新闻用)": 4, "电视台演播室电击烦躁棒": 4, "购物中心5F后半（电视台演播室）": 4,

                                                       
    "终局与灾厄遗址": 5, "避难所": 5, "最终Boss房间": 5,
    "旧转送室": 5, "独房走廊（坏结局用）": 5, "斯皮娜的故乡（监禁结局）": 5
}



             
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

MAP_FILE = os.path.join(app_dir, "world_data", "game_map_system.json")
        
                                        
                                 
                          
                                    
DYNAMIC_MAP_FILE = os.path.join(app_dir, "world_data", "dynamic_map.json")


def _ensure_world_data_dir():




    os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)


def load_dynamic_map():















    _ensure_world_data_dir()

    if not os.path.exists(DYNAMIC_MAP_FILE):
        return {}

    try:
        with open(DYNAMIC_MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        print(f"⚠️ [空间感知]: 读取动态地图失败: {e}")
        return {}


def save_dynamic_map(data):




    _ensure_world_data_dir()

    try:
        if not isinstance(data, dict):
            data = {}

        with open(DYNAMIC_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ [空间感知]: 保存动态地图失败: {e}")


def clear_dynamic_map():




    _ensure_world_data_dir()

    try:
        if os.path.exists(DYNAMIC_MAP_FILE):
            os.remove(DYNAMIC_MAP_FILE)
            print("🗺️ [空间感知]: 动态地图记忆已清空，世界坐标回归静态初始状态。")
    except Exception as e:
        print(f"⚠️ [空间感知]: 清空动态地图失败: {e}")


class MapManager:
    def __init__(self):
        self.map_data = {}
        self.flat_locations = {}
        self.static_location_names = set()                                   
        self.load_map()

    def load_map(self):
        if not os.path.exists(MAP_FILE):
            print(f"⚠️ [空间感知]: 找不到地图文件: {MAP_FILE}")
            return

        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.map_data = data.get("MapSystem", {})

                                                        
                                            
                                                        
                                
            for zone_name, zone_info in self.map_data.items():
                for sub_loc_name, sub_loc_info in zone_info.get("sub_locations", {}).items():
                    self.flat_locations[sub_loc_name] = dict(sub_loc_info)
                    self.flat_locations[sub_loc_name]["zone"] = zone_name
                    self.flat_locations[sub_loc_name]["zone_desc"] = zone_info.get("description", "")
                                 
                    self.static_location_names.add(sub_loc_name)

                                                        
                                            
                                                        
                      
                          
                                
                                    
            dynamic_map = load_dynamic_map()
            for loc_name, loc_info in dynamic_map.items():
                         
                                           
                                         
                if loc_name in self.flat_locations:
                    continue

                self.flat_locations[loc_name] = {
                    "zone": loc_info.get("zone", "动态发现区域"),
                    "zone_desc": loc_info.get(
                        "zone_desc",
                        "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。"
                    ),
                    "lore": loc_info.get("lore", "暂无详细记录。"),
                    "related_characters": loc_info.get("related_characters", []),
                    "keywords": loc_info.get("keywords", [loc_name])
                }

            print("🗺️ [空间感知]: 地图系统已成功加载并拍平索引。")
        except Exception as e:
            print(f"⚠️ [空间感知]: 地图文件读取失败: {e}")

    def register_dynamic_location(self, location_name, lore="这是一个新发现的地点。", zone="动态发现区域"):














        if not location_name or not isinstance(location_name, str):
            return

        location_name = location_name.strip()
        if not location_name:
            return

                                              
                                                  
                                       
        if location_name in self.static_location_names:
            return

        dynamic_map = load_dynamic_map()

                            
        if location_name not in dynamic_map:
            dynamic_map[location_name] = {
                "zone": zone,
                "zone_desc": "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。",
                "lore": lore,
                "related_characters": ["Romasha"],
                "keywords": [location_name]
            }
            save_dynamic_map(dynamic_map)

                                   
        self.update_dynamic_location(
            location_name=location_name,
            lore=lore,
            zone=zone,
            related_characters=["Romasha"],
            keywords=[location_name]
        )

    def update_dynamic_location(
        self,
        location_name,
        lore=None,
        zone=None,
        zone_desc=None,
        related_characters=None,
        keywords=None
    ):

















        if not location_name or not isinstance(location_name, str):
            return

        location_name = location_name.strip()
        if not location_name:
            return

                 
                                        
                             
        if location_name in self.static_location_names:
            return

        dynamic_map = load_dynamic_map()

                                 
        if location_name not in dynamic_map:
            dynamic_map[location_name] = {
                "zone": zone or "动态发现区域",
                "zone_desc": zone_desc or "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。",
                "lore": lore or "这是一个新发现的地点。",
                "related_characters": related_characters or ["Romasha"],
                "keywords": keywords or [location_name]
            }
        else:
            old_info = dynamic_map[location_name]

                                                        
                                   
                                                        
            old_lore = old_info.get("lore", "")
            if isinstance(lore, str) and lore.strip():
                new_lore = lore.strip()

                       
                                  
                                
                                                      
                if not old_lore:
                    old_info["lore"] = new_lore
                elif len(new_lore) > len(old_lore):
                    old_info["lore"] = new_lore
                elif new_lore not in old_lore and len(new_lore) >= 12:
                    old_info["lore"] = f"{old_lore} {new_lore}".strip()

                                                        
                                
                                                        
            if isinstance(zone, str) and zone.strip():
                if not old_info.get("zone"):
                    old_info["zone"] = zone.strip()

                                                        
                                               
                                                        
            if isinstance(zone_desc, str) and zone_desc.strip():
                old_zone_desc = old_info.get("zone_desc", "")
                default_zone_desc = "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。"
                if not old_zone_desc or old_zone_desc == default_zone_desc:
                    old_info["zone_desc"] = zone_desc.strip()
                elif len(zone_desc.strip()) > len(old_zone_desc):
                    old_info["zone_desc"] = zone_desc.strip()

                                                        
                                        
                                                        
            old_related = old_info.get("related_characters", [])
            if not isinstance(old_related, list):
                old_related = []

            if isinstance(related_characters, list):
                merged_related = list(dict.fromkeys(
                    [str(x).strip() for x in old_related if str(x).strip()] +
                    [str(x).strip() for x in related_characters if str(x).strip()]
                ))
                old_info["related_characters"] = merged_related

                                                        
                              
                                                        
            old_keywords = old_info.get("keywords", [])
            if not isinstance(old_keywords, list):
                old_keywords = []

            if isinstance(keywords, list):
                merged_keywords = list(dict.fromkeys(
                    [str(x).strip() for x in old_keywords if str(x).strip()] +
                    [str(x).strip() for x in keywords if str(x).strip()]
                ))
                old_info["keywords"] = merged_keywords

            dynamic_map[location_name] = old_info

              
        save_dynamic_map(dynamic_map)

                                                     
        fresh_info = dynamic_map[location_name]
        self.flat_locations[location_name] = {
            "zone": fresh_info.get("zone", zone or "动态发现区域"),
            "zone_desc": fresh_info.get(
                "zone_desc",
                zone_desc or "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。"
            ),
            "lore": fresh_info.get("lore", lore or "这是一个新发现的地点。"),
            "related_characters": fresh_info.get("related_characters", related_characters or ["Romasha"]),
            "keywords": fresh_info.get("keywords", keywords or [location_name])
        }

    def get_current_location_lore(self, location_name, current_chapter=1):

        loc = self.flat_locations.get(location_name)
        if not loc:
                     
                                                      
                                         
                                           
                                 
            return (
                f"【当前位置：{location_name}】"
                f"这是一处尚未录入基地常规地图档案的地点，但你与玩家此刻确实正身处这里。"
                f"请把它视为真实存在的当前场景，并根据上下文自然理解其氛围与用途。"
            )

                                            
        required_chapter = REGION_UNLOCK_CHAPTER.get(location_name)
        if required_chapter is None:
            required_chapter = REGION_UNLOCK_CHAPTER.get(loc['zone'], 1)

                                  
        if current_chapter < required_chapter:
                                      
            if required_chapter >= 4:
                return f"系统提示：【{location_name}】当前被高级物理安全锁封闭，罗玛莎目前的ID权限不足以进入，或者该区域正在进行系统升级。不要过度谈论此区域。"
            else:
                return f"系统提示：【{location_name}】通道受限，前方是未探索或被封锁的区域。罗玛莎对此地的情报极度匮乏。"

        info = f"你当前位于【{loc['zone']}】的【{location_name}】。\n"
        info += f"- 区域大背景：{loc.get('zone_desc', '')}\n"
        info += f"- 当前场景氛围：{loc.get('lore', '无特殊说明')}\n"

        if loc.get('related_characters'):
            info += f"- 这里常出现的人：{', '.join(loc['related_characters'])}\n"

        return info

    def get_available_locations(self, current_chapter=1):









        if not self.map_data and not self.flat_locations:
            return "无可用地点"
        region_map = {}

                                                    
                          
                                                    
        for region, data in self.map_data.items():
                                           
            req_chapter = REGION_UNLOCK_CHAPTER.get(region, 1)
            if current_chapter < req_chapter:
                continue
            region_map.setdefault(region, [])
            region_map[region].extend(list(data.get("sub_locations", {}).keys()))
                                                    
                    
                                                    
             
                                              
                                           
        for loc_name, loc_info in self.flat_locations.items():
            zone = loc_info.get("zone", "动态发现区域")
                                            
            if zone not in self.map_data:
                region_map.setdefault(zone, [])
                if loc_name not in region_map[zone]:
                    region_map[zone].append(loc_name)
        lines = []
        for region, locs in region_map.items():
            if locs:
                              
                lines.append(f"- {region}: {', '.join(locs)}")
        return "\n".join(lines) if lines else "无可用地点"

    def reload_dynamic_locations(self):






                                             
        to_delete = [name for name in self.flat_locations if name not in self.static_location_names]
        for name in to_delete:
            self.flat_locations.pop(name, None)

                                      
        dynamic_map = load_dynamic_map()
        for loc_name, loc_info in dynamic_map.items():
            if loc_name in self.static_location_names:
                continue

            self.flat_locations[loc_name] = {
                "zone": loc_info.get("zone", "动态发现区域"),
                "zone_desc": loc_info.get(
                    "zone_desc",
                    "这是一个尚未被正式地图收录、但已被你们踏足过的新地点。"
                ),
                "lore": loc_info.get("lore", "暂无详细记录。"),
                "related_characters": loc_info.get("related_characters", []),
                "keywords": loc_info.get("keywords", [loc_name])
            }

       
map_instance = MapManager()