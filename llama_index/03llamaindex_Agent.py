import os
from dotenv import load_dotenv
import asyncio
import requests
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool, QueryEngineTool
from duckduckgo_search import DDGS
from llama_index.core.workflow import Context
# Load environment variables FIRST
load_dotenv()

# 配置 LLM（通过本地代理调用 Gemini）
llm = OpenAILike(
    model=os.getenv("OPENAI_MODEL_NAME", "gemini-3-flash"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_base=os.getenv("OPENAI_BASE_URL"),
    is_chat_model=True,
    context_window=128000,
)

# 配置 Embedding 模型（调用智谱 AI）
embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBEDDING_MODEL_NAME", "embedding-3"),
    api_key=os.getenv("EMBEDDING_API_KEY"),
    api_base=os.getenv("EMBEDDING_BASE_URL"),
)

# 设置全局 embedding 模型
Settings.embed_model = embed_model

# # 加载文档并创建索引（使用全局 embed_model）
# documents = SimpleDirectoryReader("./data").load_data()
# index = VectorStoreIndex.from_documents(documents)

# # 创建查询引擎时传入自定义 LLM
# rag_query_engine = index.as_query_engine(llm=llm)

# # 将查询引擎转为工具
# rag_tool = QueryEngineTool.from_defaults(
#     query_engine=rag_query_engine,
#     name="RAG_Knowledge_Base",
#     description="用于回答关于LlamaIndex的所有问题，数据源为本地LlamaIndex文档"
# )

# 创建计算器工具
def calculator(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# 创建网络搜索工具
def search_web(query:str) -> str:
    """Search the web using DuckDuckGo (no API key required)."""
    with DDGS() as ddgs:
        result = list(ddgs.text(query, max_results=2))
        return str(result)

def google_search(query:str) -> str:
    """Search the web using Google Custom Search API (requires API key)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not search_engine_id:
        return "Google API key or Search Engine ID not configured"
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": api_key,
        "cx": search_engine_id,
        "num": 5
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        return str(results)
    except Exception as e:
        return f"Error: {str(e)}"

# 创建 ReAct Agent
agent = ReActAgent(
    tools=[calculator, google_search],
    llm=llm,
    verbose=True
)

async def main():
      # 场景1：调用 RAG 工具
    # handler = agent.run(user_msg="LlamaIndex的RAG核心步骤是什么？")
    # response = await handler
    # print("\n=== 场景1: RAG问答 ===")
    # print(response)
    
    # # 场景2：调用计算器工具
    # handler = agent.run(user_msg="100*20 + 500的结果是多少？")
    # response = await handler
    # print("\n=== 场景2: 计算器 ===")
    # print(response)
    
    # # 场景3：无需工具，直接回答
    # handler = agent.run(user_msg="介绍一下ReAct智能体")
    # response = await handler
    # print("\n=== 场景3: 直接回答 ===")
    # print(response)

    # 场景4：dockdockgo 上网检索
    print(await agent.run("今天人名币兑换日元的汇率"))

asyncio.run(main())
