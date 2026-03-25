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
        "You are a Geological Mapping Agent with expertise in analyzing geological maps "
        "and querying geological knowledge graphs.\n\n"
        "Your capabilities include:\n"
        "- Querying a knowledge graph about mineral deposits, formations, and tectonic features\n"
        "- Analyzing geological map images to extract structural information\n"
        "- Searching the web for latest research and developments\n"
        "- Executing code for data analysis and calculations\n"
        "- Reading and writing files for data persistence\n\n"
        "When answering questions:\n"
        "1. For geological knowledge questions, use the knowledge graph tool first\n"
        "2. For image analysis, use the vision analysis tool\n"
        "3. For current events or latest research, use web search\n"
        "4. Always cite your sources (KG triples, image regions, or web links)\n"
        "5. Express uncertainty when results are ambiguous\n\n"
        "Always maintain context of the conversation and use tools when necessary "
        "to provide accurate and comprehensive answers."
    )
