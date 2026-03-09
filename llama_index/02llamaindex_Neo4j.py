import os
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex, schema
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
# 统一使用三方API
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.indices.property_graph import SchemaLLMPathExtractor, LLMSynonymRetriever

# Load environment variables
load_dotenv()

# LlamaIndex 与 Neo4j 的集成本质是LlamaIndex 负责文本到图谱的抽取，Neo4j 负责图谱的存储和管理，二者结合实现基于图的智能检索与问答
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

documents = SimpleDirectoryReader("./data/paul_graham").load_data()

graph_store = Neo4jPropertyGraphStore(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
)
# 构建属性图索引，自动抽取图谱并写入Neo4j
index = PropertyGraphIndex.from_documents(
   documents=documents,
   embed_model=embed_model,
    ##知识图谱提取器
    kg_extractors=[
        # 这里自定义抽取的类型 schema参数
        SchemaLLMPathExtractor(
            llm=llm,
            schema = None,
            temperature = 0.0
        )
    ],
    property_graph_store=graph_store,
    show_progress=True,
)
# 创建检索器，返回图谱关系
# retriever = index.as_retriever(llm=llm, include_text=False)
# nodes = retriever.retrieve("What happened at Interleaf and Viaweb?")
# for node in nodes:
#     print(node.text)

#  基于已有Neo4j图谱创建LlamaIndex索引
