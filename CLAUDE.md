# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Geological knowledge graph construction and Agentic RAG system using LlamaIndex. The project extracts structured triples from geological PDFs and builds a Neo4j-powered knowledge graph for retrieval-augmented generation, with a multi-modal agent for geological map analysis.

## Architecture

The codebase has three main subsystems:

### 1. Knowledge Graph Pipeline (`data_process/`)

PDF text extraction → Triple extraction → Neo4j graph storage

- `data_process/pdf_loader.py`: PDF loading and text chunking
- `data_process/triple_extractor.py`: Geological triple extraction using LLM
- `data_process/graph_builder.py`: Build PropertyGraphIndex and write to Neo4j
- `data_process/geo_ontology.py`: Geological ontology definitions

### 2. LlamaIndex Examples (`llama_index/`)

Reference implementations for LlamaIndex features:
- `01RAGWorkflow.py`: Basic RAG workflow
- `02llamaindex_Neo4j.py`: Neo4j integration
- `03llamaindex_Agent.py`: Basic ReAct agent
- `04Agent_Context_Maintenance.py`: Agent with ChatMemoryBuffer

### 3. Geological Mapping Agent (`agent/`)

**NEW**: Multi-modal agent for geological map analysis

```
agent/
├── __init__.py
├── agent.py              # Main ReActAgent creation and execution
├── config.py             # Agent configuration
├── tools/
│   ├── __init__.py
│   ├── kg_tool.py        # Neo4j knowledge graph query
│   ├── web_search_tool.py # Google Custom Search
│   ├── file_tools.py     # File read/write
│   ├── python_tool.py    # Python code execution
│   ├── shell_tool.py     # Shell command execution
│   ├── vision_tool.py    # Geological map analysis (placeholder)
│   └── ...
```

## Key Commands

```bash
# Setup
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run knowledge graph pipeline
python data_process/main.py

# Run geological mapping agent (interactive mode)
python main.py
# or
python -m agent.agent

# Run tests
pytest data_process --cov=data_process

# Code formatting
black .
isort .
```

## Configuration

All configuration via `.env` and `data_process/config.py`:

**LLM Configuration** (Gemini via local proxy):
- `OPENAI_API_KEY`: API key
- `OPENAI_BASE_URL`: http://127.0.0.1:8045/v1
- `OPENAI_MODEL_NAME`: gemini-3-flash

**Embedding Configuration** (Zhipu AI):
- `EMBEDDING_API_KEY`: API key
- `EMBEDDING_BASE_URL`: https://open.bigmodel.cn/api/paas/v4
- `EMBEDDING_MODEL_NAME`: embedding-3

**Neo4j Configuration**:
- `NEO4J_URI`: bolt://localhost:7687
- `NEO4J_USER`: neo4j
- `NEO4J_PASSWORD`: password

**Web Search Configuration**:
- `GOOGLE_API_KEY`: Google Custom Search API key
- `GOOGLE_SEARCH_ENGINE_ID`: Search engine ID

**Data Directories**:
- `PDF_DIR`: Source PDF directory for knowledge graph extraction

## Agent Tools

The ReAct Agent has access to the following tools:

| Tool | Function | Description |
|------|----------|-------------|
| `kg_query` | Query Neo4j KG | Search geological knowledge graph |
| `web_search` | Google Search | Search web for current information |
| `file_read` | Read files | Read local file content |
| `file_write` | Write files | Write content to local files |
| `python_exec` | Run Python | Execute Python code safely |
| `shell_exec` | Run commands | Execute shell commands |
| `vision_analyze` | Image analysis | Analyze geological maps (requires vision_process) |

## Data

- `data/gouli_map/`: 14 geological map images (JPG format)
- `data/gouli_pdf/`: PDF geological reports
- `data/gouli_txt/`: Extracted text from PDFs
- `data/text_one/`: Additional text documents

## Dependencies

**Core**:
- `llama-index-core`: LlamaIndex framework
- `llama-index-graph-stores-neo4j`: Neo4j integration
- `llama-index-llms/openai-like`: LLM adapter
- `llama-index-embeddings/openai-like`: Embedding adapter

**Vision** (optional):
- `opencv-python`: Image processing
- `paddlepaddle`: Deep learning framework
- `paddleocr`: OCR for Chinese text

**Utilities**:
- `python-dotenv`: Environment variable management
- `requests`: HTTP client
- `beautifulsoup4`: HTML parsing
- `duckduckgo-search`: Web search (no API key)

## Git Structure

Active development on `project/agentic-rag` branch. Original LangGraph tutorial commits preserved in history; current implementation uses LlamaIndex + Neo4j instead of LangChain + Chroma.

## TODO

- [ ] Integrate vision_process module for geological map analysis
- [ ] Add spatial reasoning capabilities to KG
- [ ] Implement report generation tool
- [ ] Add batch processing mode for multiple maps
