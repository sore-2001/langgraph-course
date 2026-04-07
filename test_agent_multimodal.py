import asyncio
import os
from agent.agent import create_agent

async def main():
    agent = create_agent(verbose=True)
    
    print("Testing Geological Map Recognition Agent...\n")
    
    query = (
        "请分析这张地质图 (data/gouli_map/sample.jpg) 的成矿地质条件。"
        "1. 使用 vision_analyze 提取其中的矿点和断层。"
        "2. 使用 calculate_spatial_relationships 计算它们的空间关系。"
        "3. 然后根据图上的地层或图例信息，结合知识图谱 (kg_query 或 kg_community_summary) 分析断层对成矿的控制作用。"
        "4. 最后给出一个综合的成矿预测报告。"
    )
    
    print(f"Query: {query}\n")
    
    os.makedirs("logs", exist_ok=True)
    log_path = "logs/test_agent_multimodal_result.log"
    
    try:
        response = await agent.run(user_msg=query)
        print("\n=== Agent Response ===")
        print(response)
        
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Query:\n{query}\n\n")
            f.write(f"=== Agent Response ===\n{response}\n")
        print(f"\nResult saved to {log_path}")
    except Exception as e:
        print(f"\nError: {e}")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())