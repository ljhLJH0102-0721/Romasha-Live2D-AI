                   
import time

                   
                                                               
import onnxruntime
import chromadb
from chromadb.utils import embedding_functions

import re
import threading          

print(f"✅ [基地底层架构]: 生物神经网络已激活... 突触onnxruntime连接版本: {onnxruntime.__version__}")
print(f"🌟 [命运齿轮] 正在尝试建立与那个世界的连接... (核心运转正常)")

            
_client = None
_collection = None
_default_ef = None
            
_db_lock = threading.Lock()

def _get_collection():




    global _client, _collection, _default_ef
    if _collection is None:
        print("💭 [思绪浮现] 过去的记忆片段正在脑海中重组...")
        _default_ef = embedding_functions.DefaultEmbeddingFunction()
        _client = chromadb.PersistentClient(path="./romasha_memory_db")
        _collection = _client.get_or_create_collection(
            name="romasha_memories",
            embedding_function=_default_ef
        )
    return _collection

def add_memory(user_text, ai_text, current_intimacy, is_story_mode=False):




    if not user_text and not is_story_mode: return
    if not ai_text: return

                                         
                                              
    clean_ai = re.sub(r'\[.*?\]', '', ai_text)
                                          
    clean_ai = re.sub(r'^.*?<\|endofprompt\|>', '', clean_ai).strip()

    if not clean_ai: return                                

    timestamp = str(int(time.time() * 1000))

    if is_story_mode:
                                      
        if not user_text or "顺应局势" in user_text or "继续推进" in user_text or "沉默不语" in user_text:
            memory_content = f"在之前的剧情经历中，发生了这样的事：\n{clean_ai}"
        else:
                         
            memory_content = f"在之前的经历中，我（玩家）的抉择是：{user_text}\n随后发生的情节是：{clean_ai}"
    else:
                                  
        memory_content = f"我曾经对Romasha说：{user_text}\nRomasha当时的回应是：{clean_ai}"

    try:
        with _db_lock:                      
            _get_collection().add(
                documents=[memory_content],
                                        
                metadatas=[{"timestamp": timestamp, "intimacy_at_time": current_intimacy}],
                ids=[f"mem_{timestamp}"]
            )
        print(f"💾 [羁绊加深]: 刚才的对话已悄悄留在她的心底: {user_text[:20]}...")
    except Exception as e:
        print(f"⚠️ [记忆模糊]: 这一段记忆似乎像晨雾一样消散了... ({e})")

def get_intimacy_desc(intimacy_val):

    if intimacy_val < 30: return "陌生与戒备"
    elif intimacy_val < 60: return "朋友与信任"
    elif intimacy_val < 80: return "暧昧与在意"
    else: return "极度依赖与深爱"

def retrieve_relevant_memories(current_query, current_intimacy, n_results=3):



    col = _get_collection()
    if col.count() == 0: return ""
    actual_n = min(n_results, col.count())

    try:
        with _db_lock:                      
            results = col.query(query_texts=[current_query], n_results=actual_n)
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]

            if not documents: return ""
            formatted_memories = []
            for doc, meta in zip(documents, metadatas):
                               
                past_intimacy = meta.get("intimacy_at_time", 0)
                past_desc = get_intimacy_desc(past_intimacy)

                                           
                memory_block = (
                    f"【旧日回音 | 发生时亲密度: {past_intimacy} ({past_desc})】\n"
                    f"{doc}"
                )
                formatted_memories.append(memory_block)

        return "\n\n".join(formatted_memories)

    except Exception as e:
        print(f"⚠️ [回忆受阻]: 她努力回想，但记忆有些模糊...")
        return ""

def clear_all_memories():
    global _client, _collection, _default_ef
    try:
        col = _get_collection()         
        _client.delete_collection(name="romasha_memories")
        _collection = _client.get_or_create_collection(
            name="romasha_memories",
            embedding_function=_default_ef
        )
        print("\n🌀 [时光倒流] 所有相处的点滴如沙般流逝，你们回到了最初那份未知的初见。")
    except Exception as e:
        print(f"⚠️ [命运纠缠]: 过去的痕迹似乎难以抹除... ({e})")