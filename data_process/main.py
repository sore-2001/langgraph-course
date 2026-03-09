"""
主执行文件：调用 data_process 模块完成从 PDF 到知识图谱的全流程
"""
from pathlib import Path
import sys

# 确保项目根目录在搜索路径中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from data_process.config import Config
from data_process.graph_builder import GeoGraphBuilder
from data_process.utils import logger
from data_process.pdf_loader import load_geology_pdfs
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike

def main():
    """主流程：PDF加载→三元组抽取→图谱构建"""
    try:
        # 配置全局 LLM 供 LlamaIndex 查询引擎使用
        Settings.llm = OpenAILike(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            api_base=Config.OPENAI_BASE_URL,
            is_chat_model=True,
            temperature=Config.OPENAI_TEMPERATURE,
        )

        # 1. 初始化图谱构建器
        graph_builder = GeoGraphBuilder()

        # 2. 从PDF构建图谱 (少量数据测试)
        logger.info("开始全流程构建地质知识图谱 (测试模式：仅取前20个文本块)...")
        # 手动加载并截取节点
        nodes = load_geology_pdfs(Config.PDF_DIR)
        test_nodes = nodes[:10] if nodes else []
        logger.info(f"共加载 {len(nodes)} 个文本块，截取前 {len(test_nodes)} 个进行测试。")

        # 抽取三元组
        all_triples = []
        for i, node in enumerate(test_nodes):
            logger.info(f"处理测试文本块 {i+1}/{len(test_nodes)}：{node.metadata.get('source')}")
            triples = graph_builder.extractor.extract_from_text(node.text)
            all_triples.extend(triples)

        from data_process.utils import triples_to_json
        triples_to_json(all_triples, "./geology_triples_test.json")

        # 构建图谱
        index = graph_builder.build_from_triples(all_triples, source_nodes=test_nodes)

        # 3. 测试查询
        logger.info("测试图谱查询...")
        query_engine = index.as_query_engine(include_text=True)
        response = query_engine.query("塘江沅钨矿主要赋存于什么岩石中？")
        logger.info(f"查询结果：{str(response)}")
        
        logger.info("全流程执行完成！")
        
    except Exception as e:
        logger.error(f"主流程执行失败：{str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()