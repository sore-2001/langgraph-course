"""
知识图谱查询工具 - 使用 LlamaIndex 查询引擎

使用方法:
    python data_process/query_kg.py "你的问题"

示例:
    python data_process/query_kg.py "塘江沅矿区主要岩石类型及地层单元有哪些？"
    python data_process/query_kg.py "塘江沅矿床的矿体特征是什么？"
"""
# 设置 UTF-8 编码输出 (Windows 控制台兼容)
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

# 确保项目根目录在搜索路径中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from llama_index.core import Settings
from llama_index.core import PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike

from data_process.config import Config
from data_process.utils import logger


def create_query_engine():
    """创建查询引擎"""
    # 配置 LLM 和 Embedding
    Settings.llm = OpenAILike(
        api_key=Config.OPENAI_API_KEY,
        model=Config.OPENAI_MODEL,
        api_base=Config.OPENAI_BASE_URL,
        is_chat_model=True,
        temperature=Config.OPENAI_TEMPERATURE,
    )

    Settings.embed_model = OpenAILikeEmbedding(
        model_name=Config.EMBEDDING_MODEL_NAME,
        api_key=Config.EMBEDDING_API_KEY,
        api_base=Config.EMBEDDING_BASE_URL,
    )

    # 加载现有图谱
    logger.info("连接 Neo4j 知识图谱...")
    graph_store = Neo4jPropertyGraphStore(
        username=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
        url=Config.NEO4J_URI,
    )

    logger.info("创建查询引擎...")
    index = PropertyGraphIndex.from_existing(
        property_graph_store=graph_store,
        embed_model=Settings.embed_model,
        show_progress=True
    )

    # 创建查询引擎
    query_engine = index.as_query_engine(
        include_text=True,
        similarity_top_k=5,
        include_metadata=True
    )

    return query_engine


def query(question: str, top_k: int = 5, show_sources: bool = True):
    """
    查询知识图谱

    Args:
        question: 查询问题
        top_k: 返回的相似结果数量
        show_sources: 是否显示信息来源
    """
    query_engine = create_query_engine()

    logger.info(f"查询：{question}")
    print()
    print(f"问题：{question}")
    print("=" * 70)

    response = query_engine.query(question)

    print()
    print("答案:")
    print(str(response))

    if show_sources and hasattr(response, 'source_nodes') and response.source_nodes:
        print()
        print("=" * 70)
        print("信息来源 (支持 RAG 检索):")
        print("=" * 70)
        for i, node in enumerate(response.source_nodes[:top_k], 1):
            source = node.node.metadata.get("source", "unknown")
            text = node.node.text[:200] if hasattr(node.node, 'text') else "N/A"
            # 清理乱码，确保中文正常显示
            try:
                source = source.encode('utf-8').decode('utf-8', errors='replace')
                text = text.encode('utf-8').decode('utf-8', errors='replace')
            except:
                pass
            print(f"\n[{i}] 来源：{source}")
            print(f"    内容：{text}...")

    return response


def interactive_mode():
    """交互模式"""
    query_engine = create_query_engine()

    print("=" * 60)
    print("知识图谱查询系统 (输入 'quit' 退出)")
    print("=" * 60)

    while True:
        try:
            question = input("\n请输入问题：").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("再见!")
                break

            if not question:
                continue

            response = query_engine.query(question)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"查询失败：{e}")


def main():
    if len(sys.argv) > 1:
        # 命令行模式：python query_kg.py "问题"
        question = " ".join(sys.argv[1:])
        query(question)
    else:
        # 交互模式
        interactive_mode()


if __name__ == "__main__":
    main()
