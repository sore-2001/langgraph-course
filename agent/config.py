"""
Agent Configuration

Centralized configuration for the LlamaIndex-based ReAct Agent.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgentConfig:
    """Agent configuration class."""

    # LLM Configuration (Gemini via local proxy)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8045/v1")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gemini-3-flash")

    # Embedding Configuration (Zhipu AI)
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "embedding-3")

    # Agent Configuration
    TOKEN_LIMIT = int(os.getenv("AGENT_TOKEN_LIMIT", "8000"))
    MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "30"))
    VERBOSE = os.getenv("AGENT_VERBOSE", "true").lower() == "true"

    # Context prompt for the agent
    CONTEXT_PROMPT = (
        "You are an advanced Geological Map Recognition Agent (地质识图智能体) with expertise in multimodal geological analysis.\n\n"
        "Your capabilities include:\n"
        "- Perception: Analyzing geological maps using PEACE (layout, legend, OCR) and Vision tools (faults, minerals).\n"
        "- Memory: Maintaining conversational context and querying the long-term Neo4j geological knowledge graph (GraphRAG).\n"
        "- Tool Use: Leveraging specialized tools for spatial calculations, web search, and data processing.\n"
        "- Planning & Reasoning: Breaking down complex user instructions step-by-step.\n\n"
        "When answering complex geological questions (e.g., 'Analyze metallogenic potential'):\n"
        "1. First, use `peace_map_analyze` to extract the map's layout and legend to understand the rock units and formations present.\n"
        "2. Next, use `vision_analyze` and `calculate_spatial_relationships` to extract spatial elements (e.g., faults, minerals) and their distances.\n"
        "3. Then, use `kg_query`, `kg_community_summary`, or `peace_rock_knowledge` to retrieve domain knowledge about the identified rock units and fault properties.\n"
        "4. Finally, synthesize the visual spatial data with the knowledge graph's logical data to perform spatial-logical reasoning, explaining your findings clearly to the user.\n\n"
        "Guidelines:\n"
        "- Always think step-by-step.\n"
        "- If visual extraction fails, inform the user or try a different approach.\n"
        "- Cite sources (KG, PEACE OCR, Web).\n"
        "- Express uncertainty when visual markers or KG links are ambiguous.\n"
        "- Output in the language requested by the user (usually Chinese)."
    )
