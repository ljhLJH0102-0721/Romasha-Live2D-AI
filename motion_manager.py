                   
import random

                            
                                                      
MOTIONS = {
    "amazing": {"index": 0, "desc": "吃惊后退半步，手抬起捂嘴，像是在说“诶？？！”"},
    "angry": {"index": 1, "desc": "义正言辞的拒绝，带有愤怒和坚守底线的感觉"},
    "chui": {"index": 2, "desc": "闭眼左手抬起食指放在嘴前，轻微摇头，示意“安静哦”"},
    "device": {"index": 3, "desc": "右手摸头，像是无意识间做出来的动作（如摸头戴设备）"},
    "donbiki": {"index": 4, "desc": "嫌弃，像是在说“恶心，离我远点”"},
    "doya": {"index": 5, "desc": "闭眼且脸发红，接受夸赞时无意识间做出的娇羞动作"},
    "guruguru": {"index": 6, "desc": "比较羞涩的震惊，像是在说“诶？？？？？？？”"},
    "hatujo": {"index": 7, "desc": "脸发红捂胸叹气，面对尴尬或暧昧话题时无奈又害羞"},
    "iyaiya": {"index": 8, "desc": "无奈摇头幅度较大外加叹息，接受尴尬话题后的下意识动作"},
    "neutral": {"index": 9, "desc": "强制切换到基础的呆立姿势并绝对静止"},
    "poster": {"index": 10, "desc": "双手交叉成叉号举在嘴前，坚决地说“达咩，不行，拒绝”"},
    "question": {"index": 11, "desc": "带有疑问的神态"},
    "relief": {"index": 12, "desc": "捂胸叹气，释怀、放松的状态"},
    "sad": {"index": 13, "desc": "较为悲伤的神情"},
    "skirt_bust": {"index": 14, "desc": "就像是在胸部好像被别人碰到之后突然娇羞的反应动作"},
    "skirt_hip": {"index": 15, "desc": "就像是在臀部好像被别人碰到之后突然娇羞的反应动作"},
    "skirt": {"index": 16, "desc": "被突然靠近或触碰后娇羞的动作"},
    "smallamazing": {"index": 17, "desc": "较为小幅度的震惊"},
    "smallangry": {"index": 18, "desc": "小幅度的生气、拒绝"},
    "smallangryb": {"index": 19, "desc": "更小幅度的生气、拒绝"},
    "smalldoya": {"index": 20, "desc": "有些小得意的可爱动作"},
    "smallgikuri": {"index": 21, "desc": "有些愧疚、心虚的动作"},
    "smallsmile": {"index": 22, "desc": "稍微有一点点高兴的动作"},
    "smile": {"index": 23, "desc": "比较高兴、开朗的微笑"},
    "talk": {"index": 24, "desc": "非静止的待机常态动作（适合普通交流时使用）"},
    "talk_alc": {"index": 25, "desc": "非静止的有些害羞的待机常态动作（适合微醺或害羞交流）"},
    "talk_ero": {"index": 26, "desc": "非静止的委屈、带泪滴的待机常态动作（惹哭或深情时）"},
    "taol_fall": {"index": 27, "desc": "浴衣无意间掉落（身穿浴衣时极度害羞或意外时触发）"},
    "trouble": {"index": 28, "desc": "突然遇到麻烦、不知所措的神态"},
    "troublesmile": {"index": 29, "desc": "有些尴尬的赔笑"},
    "victory": {"index": 30, "desc": "骄傲、有些胜利或占优的神情"},
    "wait": {"index": 31, "desc": "维持前一个动作的姿势直接冻结定格（完全不动）"},
    "wait_haji": {"index": 32, "desc": "维持前一个动作的姿势冻结定格，但嘴部微动（小声嘀咕）"}
}


def get_motion_index(action_name):



    action_name = action_name.lower()

                     
    if action_name in MOTIONS:
        return MOTIONS[action_name]["index"]

                      

                             
    if action_name == "freeze_silent":
        return MOTIONS["wait"]["index"]                                

                                  
    elif action_name == "freeze_mutter":
        return MOTIONS["wait_haji"]["index"]

                             

    print(f"警告: 未找到动作指令 {action_name}，默认返回 talk")
    return MOTIONS["talk"]["index"]