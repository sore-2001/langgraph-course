from ntpath import dirname
import dotenv
from openai import timeout
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.workflow import step,Workflow, Context, StartEvent, StopEvent
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from dotenv import load_dotenv
import os
import asyncio
from llama_index.core.workflow import Event
from llama_index.core.schema import NodeWithScore

# llamaindex通过索引， 检索，重排序，总结完成RAG
# 检索完成的事件：传递检索到的节点
class RetrieveEvent(Event):
    nodes: list[NodeWithScore]

# 重排序完成的事件：传递重排序后的节点
class RerankEvent(Event):
    nodes: list[NodeWithScore]

# Load environment variables
load_dotenv()

# Initialize global models with environment variables
llm = OpenAILike(
    model=os.getenv("OPENAI_MODEL_NAME", "gemini-3-flash"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_base=os.getenv("OPENAI_BASE_URL"),
)

# Use OpenAILikeEmbedding for third-party embedding models
embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBEDDING_MODEL_NAME", "embedding-3"),
    api_key=os.getenv("EMBEDDING_API_KEY"),
    api_base=os.getenv("EMBEDDING_BASE_URL"),
    embed_batch_size=10
)

# 定义RAG工作流，继承自基础Workflow
class RAGWorkflow(Workflow):
     # 步骤1：文档摄入（Ingest）→ 生成索引
    @step
    async def ingest(self, ctx:Context, ev:StartEvent) -> StopEvent | None:
        """
        触发条件：StartEvent携带dirname（数据目录）
        功能：加载目录下的文档，生成VectorStoreIndex并返回
        """
        dirname = ev.get("dirname")
        if not dirname:
            return None
        documents = SimpleDirectoryReader(dirname).load_data()
        # 基于文档生成向量索引：指定嵌入模型
        index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
        # 存储索引到上下文
        return StopEvent(result=index)
    
     # 步骤2：检索（Retrieve）→ 从索引召回相关节点
    @step
    async def retrieve(self, ctx:Context, ev:StartEvent) -> RetrieveEvent | None:
        """
        触发条件：StartEvent携带query（查询）和index（索引）
        功能：基于查询从索引中检索相关节点，传递给重排序步骤
        """
        query = ev.get("query")
        index = ev.get("index")
        if not query:
            return None
        print(f"Query the database with: {query}")
        await ctx.store.set("query", query)
        if index is None:
            print("Index is empty, load some documents before querying!")
            return None
        retriever = index.as_retriever(similarity_top_k=2)
        nodes = await retriever.aretrieve(query)
        print(f"Retrieved {len(nodes)} nodes.")
        return RetrieveEvent(nodes=nodes)

     # 步骤3：重排序（Rerank）→ 提升节点相关性
    @step
    async def rerank(self, ctx:Context, ev:RetrieveEvent) -> RerankEvent:
        """
        触发条件：接收到RetrieveEvent
        功能：用LLM对检索节点重排序，保留TopN相关节点
        """
        # Initialize reranker with global llm variable
        ranker = LLMRerank(
            choice_batch_size=5, top_n=3, llm=llm
        )
        
        # Get query from context
        query = await ctx.store.get("query", default=None)
        print(f"Received query: {query}", flush=True)
        
        # Rerank nodes
        new_nodes = ranker.postprocess_nodes(ev.nodes, query_str=query)
        print(f"Reranked nodes from {len(ev.nodes)} to {len(new_nodes)}")
        
        return RerankEvent(nodes=new_nodes)
    
    # 步骤4：合成（Synthesize）→ 生成最终回答
    @step
    async def synthesize(self, ctx:Context, ev:RerankEvent) -> StopEvent:
        """
        触发条件：接收到RerankEvent
        功能：基于重排序后的节点和查询，调用LLM生成流式回答
        """
        # Initialize response synthesizer
        summarizer = CompactAndRefine(llm=llm, streaming=True, verbose=True)
        
        # Get query from context
        query = await ctx.store.get("query", default=None)
        
        # Synthesize response asynchronously
        response = await summarizer.asynthesize(query, nodes=ev.nodes)
        
        # Return response
        return StopEvent(result=response)


async def main():
    w = RAGWorkflow()
    index = await w.run(dirname='data')
    result = await w.run(query="How was Llama2 trained?", index=index, timeout=120)
    async for chunk in result.async_response_gen():
        print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
