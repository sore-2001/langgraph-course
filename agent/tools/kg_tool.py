"""
Knowledge Graph Query Tool for Neo4j

This tool provides a natural language interface to query the geological knowledge graph.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from llama_index.core import PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

# Load environment variables
load_dotenv()


class KGQueryTool:
    """Knowledge Graph Query Tool using LlamaIndex + Neo4j."""

    def __init__(self):
        self.graph_store = None
        self.index = None
        self.retriever = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Lazy initialization of the knowledge graph."""
        if self._initialized:
            return True

        try:
            # Neo4j configuration
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD")

            # Embedding configuration
            embedding_api_key = os.getenv("EMBEDDING_API_KEY")
            embedding_base_url = os.getenv("EMBEDDING_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
            embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "embedding-3")

            # Initialize Neo4j graph store
            self.graph_store = Neo4jPropertyGraphStore(
                url=neo4j_uri,
                username=neo4j_user,
                password=neo4j_password,
            )

            # Initialize embedding model
            self.embed_model = OpenAILikeEmbedding(
                model_name=embedding_model_name,
                api_key=embedding_api_key,
                api_base=embedding_base_url,
            )

            # Create index from existing graph
            self.index = PropertyGraphIndex.from_existing(
                property_graph_store=self.graph_store,
                embed_model=self.embed_model,
            )

            # Create retriever
            self.retriever = self.index.as_retriever()

            self._initialized = True
            return True

        except Exception as e:
            print(f"Failed to initialize KG: {str(e)}")
            return False

    def query(self, query_text: str) -> str:
        """
        Query the geological knowledge graph using natural language.

        Args:
            query_text: Natural language query (e.g., "沟里地区有哪些矿床？")

        Returns:
            Query results as formatted string
        """
        if not self._initialize():
            return "Error: Failed to initialize knowledge graph connection"

        try:
            # Retrieve relevant information from the graph
            nodes = self.retriever.retrieve(query_text)

            if not nodes:
                return "No relevant information found in the knowledge graph."

            # Format results
            results = []
            for node in nodes:
                results.append(node.text)

            return "\n\n".join(results)

        except Exception as e:
            return f"Error querying knowledge graph: {str(e)}"


# Create singleton instance
_kg_tool = None


def get_kg_tool() -> KGQueryTool:
    """Get or create the KG query tool singleton."""
    global _kg_tool
    if _kg_tool is None:
        _kg_tool = KGQueryTool()
    return _kg_tool


def kg_query(query: str) -> str:
    """
    Query the geological knowledge graph.

    This tool searches the Neo4j-backed knowledge graph for information about:
    - Mineral deposits and their characteristics
    - Geological formations and rock types
    - Fault systems and tectonic features
    - Metallogenic conditions and predictions

    Args:
        query: Natural language query about geological knowledge

    Returns:
        Retrieved information from the knowledge graph
    """
    return get_kg_tool().query(query)
