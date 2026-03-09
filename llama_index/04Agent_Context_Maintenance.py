import os
import subprocess
import time
import json
import asyncio
import signal
import sys
from io import StringIO
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
import requests

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

# 设置全局配置
Settings.llm = llm
Settings.embed_model = embed_model


# 工具函数定义
def shell_exec(command: str) -> str:
    """Execute shell commands on the system and return output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}\nReturn code: {result.returncode}"
        return output
    except Exception as e:
        return f"Error: {str(e)}"


def file_read(file_path: str) -> str:
    """Read content from local files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"


def file_write(file_path: str, content: str) -> str:
    """Write content to local files"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"


def python_exec(code: str) -> str:
    """Execute Python code and capture its standard output"""
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    try:
        # Create a local scope for execution
        local_vars = {}
        exec(code, {"__builtins__": __builtins__}, local_vars)
        sys.stdout = old_stdout
        captured_output = redirected_output.getvalue()
        return f"Output: {captured_output}\nVariables: {list(local_vars.keys())}"
    except Exception as e:
        sys.stdout = old_stdout
        return f"Error: {str(e)}"


def google_search(query: str) -> str:
    """Search the web using Google Custom Search API"""
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not search_engine_id:
        return "Error: Google API key or Search Engine ID not configured"
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 2
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        if "items" not in results:
            return "No results found"
        
        formatted = []
        for item in results["items"]:
            formatted.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return json.dumps(formatted, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"


# 创建工具
tools = [
    FunctionTool.from_defaults(fn=shell_exec),
    FunctionTool.from_defaults(fn=file_read),
    FunctionTool.from_defaults(fn=file_write),
    FunctionTool.from_defaults(fn=python_exec),
    FunctionTool.from_defaults(fn=google_search),
]

# 配置内存（上下文维护的关键）
# 使用 ChatMemoryBuffer 自动管理上下文窗口，保留最近的对话
memory = ChatMemoryBuffer.from_defaults(token_limit=4000)

# 创建 ReAct Agent
agent = ReActAgent.from_tools(
    tools=tools,
    llm=llm,
    memory=memory,
    verbose=True,
    max_iterations=30,
    context_prompt=(
        "You are a helpful AI assistant with access to system tools.\n"
        "You can execute shell commands, read/write files, run Python code, and search the web.\n"
        "Always maintain context of the conversation and use tools when necessary to provide accurate answers."
    )
)


# 全局变量用于控制退出
running = True


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    global running
    print("\n\nReceived Ctrl+C, exiting...")
    running = False


async def main():
    """使用 ReAct Agent 的交互式对话"""
    global running
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("Welcome to Optimized LlamaIndex ReAct Agent!")
    print("Optimizations: ChatMemoryBuffer, agent.chat(), improved python_exec")
    print("Available tools: shell_exec, file_read, file_write, python_exec, google_search")
    print("Type 'exit' or press Ctrl+C to quit.")
    print("=" * 60)
    
    turn_count = 0
    total_time = 0
    
    while running:
        try:
            # Use asyncio.to_thread for input to avoid blocking the event loop
            user_input = await asyncio.to_thread(input, "\nUser: ")
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
        
        turn_start_time = time.time()
        
        try:
            # 使用 agent.chat 而不是 agent.run 以便更好地利用内存
            response = await agent.achat(user_input)
            turn_time = time.time() - turn_start_time
            total_time += turn_time
            turn_count += 1
            
            print(f"\nAgent: {response}")
            print(f"[耗时: {turn_time:.2f}秒]")
        except Exception as e:
            print(f"\nError: {str(e)}")
            # 发生严重错误时才重置
            # agent.reset()
    
    if turn_count > 0:
        print(f"\n平均每轮耗时: {total_time/turn_count:.2f}秒")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
