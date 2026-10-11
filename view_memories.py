                  
import chromadb
import time
import os
import sys

                             
try:
    import story_manager
except ImportError:
    story_manager = None

def get_intimacy_desc(intimacy_val):
    if intimacy_val < 30: return "陌生与戒备"
    elif intimacy_val < 60: return "朋友与信任"
    elif intimacy_val < 80: return "暧昧与在意"
    else: return "极度依赖与深爱"

def read_diary():
    print("📖 正在翻阅 Romasha 的世界线档案与脑海深处的碎片...\n")
                                   
    export_filename = "romasha_world_state_export.txt"

    try:
                        
        client = chromadb.PersistentClient(path="./romasha_memory_db")

                   
        collection = client.get_collection(name="romasha_memories")

                   
        data = collection.get()

        total_memories = len(data['ids']) if data and data.get('ids') else 0

                                         
        memories_list = []
        if total_memories > 0:
            for i in range(total_memories):
                memories_list.append({
                    "id": data['ids'][i],
                    "text": data['documents'][i],
                    "metadata": data['metadatas'][i]
                })
                                   
            memories_list.sort(key=lambda x: int(x["metadata"].get("timestamp", 0)))

                       
        with open(export_filename, "w", encoding="utf-8") as f:
                         
            f.write(f"📖 Romasha 的完整记忆档案\n")
            f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

                                               
            f.write("📜 【当前剧情前情提要 & 近期日记】\n")
            f.write("（这是用于维持对话连贯性的滑动窗口总结）\n")
            f.write("-" * 50 + "\n")
            if story_manager:
                summary_text = story_manager.get_summary()
                if summary_text.strip():
                    f.write(summary_text + "\n")
                else:
                    f.write("（暂无近期的剧情总结，可能你们刚刚重置了世界线）\n")
            else:
                f.write("（无法加载 story_manager 模块）\n")

            f.write("\n" + "=" * 50 + "\n\n")

                                                   
            f.write(f"🧠 【海马体深层碎片 (共 {total_memories} 条)】\n")
            f.write("（这些记忆会在遇到相似情境时被随机唤醒，带有时光印记）\n")
            f.write("-" * 50 + "\n")

            if total_memories == 0:
                f.write("📭 目前记忆库是空的，你们还没有创造深刻的回忆。\n")
            else:
                                       
                for mem in memories_list:
                    metadata = mem["metadata"]
                    text = mem["text"]

                           
                    timestamp_ms = int(metadata.get('timestamp', 0))
                    if timestamp_ms > 0:
                        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_ms / 1000))
                    else:
                        time_str = "未知时间"

                                          
                    past_intimacy = metadata.get('intimacy_at_time', 0)
                    past_desc = get_intimacy_desc(past_intimacy)

                                       
                    record = (
                        f"🕰️ 时间: {time_str} | 💖 羁绊值: {past_intimacy} ({past_desc})\n"
                        f"📝 碎片内容:\n{text}\n"
                        f"{'-' * 50}\n"
                    )

                                        
                                           
                    f.write(record)

                        
        full_path = os.path.abspath(export_filename)
        print(f"✅ 档案提取完毕！已成功保存为文本文件，你可以随时打开查看：\n📂 {full_path}")

    except Exception as e:
        print(f"⚠️ 读取记忆失败，可能是数据库不存在或正在被主程序强行占用: {e}")

if __name__ == "__main__":
    read_diary()