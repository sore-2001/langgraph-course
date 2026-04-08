"""
LlamaIndex ReAct Agent for Geological Mapping

This module creates and runs a ReAct agent with:
- Knowledge graph query tool (Neo4j)
- Web search tool (Google Custom Search)
- File system tools (read/write)
- Python code execution
- Shell command execution
- Vision analysis tool (when available)
"""
import os
import asyncio
import signal
import sys
from typing import Optional

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer

# Load environment variables
load_dotenv()

# Import tools
from agent.tools import (
    kg_query,
    kg_community_summary,
    web_search,
    file_read,
    file_write,
    python_exec,
    shell_exec,
    peace_map_analyze,
    peace_rock_knowledge,
    vision_analyze,
    calculate_spatial_relationships,
)   
from agent.config import AgentConfig


def create_agent(
    token_limit: int = None,
    max_iterations: int = None,
    verbose: bool = None,
) -> ReActAgent:
    """
    Create a ReAct Agent with all configured tools.

    Args:
        token_limit: Maximum tokens for memory buffer (default: 8000)
        max_iterations: Maximum tool execution iterations (default: 30)
        verbose: Enable verbose logging (default: True)

    Returns:
        Configured ReActAgent instance
    """
    token_limit = token_limit or AgentConfig.TOKEN_LIMIT
    max_iterations = max_iterations or AgentConfig.MAX_ITERATIONS
    verbose = verbose or AgentConfig.VERBOSE

    # Configure LLM (Gemini via local proxy)
    llm = OpenAILike(
        model=AgentConfig.OPENAI_MODEL_NAME,
        api_key=AgentConfig.OPENAI_API_KEY,
        api_base=AgentConfig.OPENAI_BASE_URL,
        is_chat_model=True,
        context_window=128000,
    )

    # Configure Embedding model (Zhipu AI)
    embed_model = OpenAILikeEmbedding(
        model_name=AgentConfig.EMBEDDING_MODEL_NAME,
        api_key=AgentConfig.EMBEDDING_API_KEY,
        api_base=AgentConfig.EMBEDDING_BASE_URL,
    )

    # Set global settings
    Settings.llm = llm
    Settings.embed_model = embed_model

    # Define available tools
    tools = [
        FunctionTool.from_defaults(fn=kg_query, name="kg_query", description="Query the geological knowledge graph for information about mineral deposits, formations, faults, and metallogenic conditions"),
        FunctionTool.from_defaults(fn=kg_community_summary, name="kg_community_summary", description="Query macro-level GraphRAG community summaries for a geological entity"),
        FunctionTool.from_defaults(fn=web_search, name="web_search", description="Search the web for current information and latest research"),
        FunctionTool.from_defaults(fn=file_read, name="file_read", description="Read content from files"),
        FunctionTool.from_defaults(fn=file_write, name="file_write", description="Write content to files"),
        FunctionTool.from_defaults(fn=python_exec, name="python_exec", description="Execute Python code for calculations and data analysis"),
        FunctionTool.from_defaults(fn=shell_exec, name="shell_exec", description="Execute shell commands"),
        FunctionTool.from_defaults(fn=peace_map_analyze, name="peace_map_analyze", description="Analyze geological map images using PEACE module to extract metadata, layouts, and legends. Use query='layout', 'legend', 'info', or 'full'"),
        FunctionTool.from_defaults(fn=peace_rock_knowledge, name="peace_rock_knowledge", description="Get domain knowledge (type, age) for a specific rock/stratigraphic unit from local knowledge base"),
        FunctionTool.from_defaults(fn=vision_analyze, name="vision_analyze", description="Analyze geological map images to extract spatial features (faults, minerals)"),
        FunctionTool.from_defaults(fn=calculate_spatial_relationships, name="calculate_spatial_relationships", description="Calculate spatial relationships (e.g. distances) between minerals and faults given the JSON output from vision_analyze"),
    ]

    # Configure memory with ChatMemoryBuffer for context management
    memory = ChatMemoryBuffer.from_defaults(token_limit=token_limit)

    # Create ReAct Agent
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        memory=memory,
        verbose=verbose,
        max_iterations=max_iterations,
        context=AgentConfig.CONTEXT_PROMPT,
    )

    return agent


async def run_agent_interactive(agent: ReActAgent) -> None:
    """
    Run the agent in interactive mode.

    Args:
        agent: Configured ReActAgent instance
    """
    running = True

    def signal_handler(sig, frame):
        """Handle Ctrl+C signal"""
        nonlocal running
        print("\n\nReceived Ctrl+C, exiting...")
        running = False

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("Geological Mapping Agent - Interactive Mode")
    print("=" * 60)
    print("Available tools:")
    print("  - kg_query: Query geological knowledge graph")
    print("  - kg_community_summary: Query GraphRAG community summaries")
    print("  - web_search: Search the web")
    print("  - file_read/file_write: File operations")
    print("  - python_exec: Run Python code")
    print("  - shell_exec: Run shell commands")
    print("  - vision_analyze: Analyze spatial features of geological maps")
    print("  - calculate_spatial_relationships: Calculate spatial relationships")
    print("  - peace_map_analyze: PEACE geological map extraction")
    print("  - peace_rock_knowledge: PEACE local domain knowledge")
    print("=" * 60)
    print("Type 'exit' or press Ctrl+C to quit\n")

    turn_count = 0
    total_time = 0.0

    while running:
        try:
            # Get user input
            user_input = await asyncio.to_thread(input, "User: ")
            user_input = user_input.strip()
        except EOFError:
            break

        if not running:
            break

        if user_input.lower() in ["exit", "quit"]:
            print("Agent: Goodbye!")
            break

        if not user_input:
            continue

        import time
        turn_start_time = time.time()

        try:
            # Process query with async chat
            response = await agent.achat(user_input)
            turn_time = time.time() - turn_start_time
            total_time += turn_time
            turn_count += 1

            print(f"\nAgent: {response}")
            print(f"[Time: {turn_time:.2f}s]")

        except Exception as e:
            print(f"\nError: {str(e)}")
            # Reset agent memory on critical errors
            # agent.reset()

    if turn_count > 0:
        print(f"\nAverage time per turn: {total_time/turn_count:.2f}s")


async def run_agent_query(agent: ReActAgent, query: str) -> str:
    """
    Run a single query through the agent.

    Args:
        agent: Configured ReActAgent instance
        query: User query string

    Returns:
        Agent response
    """
    response = await agent.achat(query)
    return response


def main():
    """Main entry point for the agent."""
    # Create agent
    agent = create_agent()

    # Run interactive mode
    asyncio.run(run_agent_interactive(agent))


if __name__ == "__main__":
    main()
