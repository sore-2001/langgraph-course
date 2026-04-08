import asyncio
import os
from agent.agent import create_agent

async def main():
    agent = create_agent(verbose=True)
    
    print("Testing Geological Map Recognition Agent...\n")
    
    # 一个简单的综合问题，验证 KG 工具和视觉工具能否被调用
    query = (
        "请帮我完成两件事：\n"
        "1. 使用 vision_analyze 工具提取图片 'data/gouli_map/沟里地质矿产.JPG' 中的矿点和断层，"
        "然后使用 calculate_spatial_relationships 计算它们的空间关系。\n"
        "2. 使用 kg_query 工具查询一下知识图谱中'塘江沅矿区'的'断层' 和 '矿床' 的相关知识。\n"
        "最后综合这两部分信息给我一个简短的总结。"
    )
    
    print(f"Query: {query}\n")
    
    os.makedirs("logs", exist_ok=True)
    log_path = "logs/test_simple_result.log"
    
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