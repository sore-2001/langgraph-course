"""
运行 GraphRAG 社区检测

基于官方文档：https://developers.llamaindex.ai/python/examples/cookbooks/graphrag_v2/
"""
import sys
from pathlib import Path

# 确保项目根目录在搜索路径中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from data_process.graphrag_store import GraphRAGStore
from llama_index.llms.openai_like import OpenAILike
from data_process.config import Config


def main():
    """运行社区检测"""
    print("=" * 60)
    print("开始构建知识图谱社区层次结构")
    print("=" * 60)

    # 配置 LLM
    llm = OpenAILike(
        api_key=Config.OPENAI_API_KEY,
        model=Config.OPENAI_MODEL,
        api_base=Config.OPENAI_BASE_URL,
        is_chat_model=True,
        temperature=Config.OPENAI_TEMPERATURE,
    )

    # 创建 GraphRAGStore
    store = GraphRAGStore(
        username=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
        url=Config.NEO4J_URI,
        llm=llm,
        max_cluster_size=5,  # 每个社区的最大实体数
    )

    try:
        # 构建社区
        store.build_communities(levels=3)

        # 输出统计
        print()
        print("=" * 60)
        print("社区构建完成统计")
        print("=" * 60)
        print(f"实体信息：{len(store.entity_info)} 个实体")
        print(f"社区摘要：{len(store.community_summary)} 个社区")

        # 显示部分社区摘要
        print()
        print("社区摘要示例 (前 3 个):")
        for i, (community_id, summary) in enumerate(list(store.community_summary.items())[:3]):
            print(f"\n--- Community {community_id} ---")
            print(f"{summary[:200]}..." if len(summary) > 200 else summary)

    except Exception as e:
        print(f"社区构建失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        store.close()


if __name__ == "__main__":
    main()
