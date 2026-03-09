# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Geological knowledge graph construction and Agentic RAG system using LangGraph and LlamaIndex. The project extracts structured triples from geological PDFs and builds a Neo4j-powered knowledge graph for retrieval-augmented generation.

## Architecture

The codebase has two main subsystems:

### 1. Knowledge Graph Pipeline (`data_process/`)
- **pdf_loader.py**: Loads geological PDFs using LlamaIndex `SimpleDirectoryReader`, chunks text with `SentenceSplitter` (Chinese sentence-aware splitting on `。`)
- **triple_extractor.py**: LLM-based triple extraction using `OpenAILike` (Gemini via local proxy). Extracts standardized `(subject, relation, object)` triples with robust JSON parsing
- **graph_builder.py**: Builds `PropertyGraphIndex` from triples, writes to Neo4j via `Neo4jPropertyGraphStore`. Creates `Chunk -> Entity` MENTIONS relationships for RAG
- **geo_ontology.py**: Pydantic models for 6 entity types (`Deposit`, `OreBody`, `Rock`, `Mineral`, `Stratum`, `GeoTectonic`) and 39 geological relations
- **main.py**: Orchestrates full pipeline: PDF → triples → Neo4j → query testing

### 2. RAG & Agent Systems
- **llama_index/**: Workflow-based RAG implementations (`RAGWorkflow` with ingest → retrieve → rerank → synthesize steps)
- **ingestion.py**: LangChain ingestion pipeline for web documents with Chroma vector store
- **main.py** (root): LangGraph agent entry point with MCP/web-search tool interfaces

## Key Commands

```bash
# Setup
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run knowledge graph pipeline
python data_process/main.py

# Run LangGraph agent
python main.py

# Run tests
pytest data_process --cov=data_process

# Code formatting
black .
isort .
```

## Configuration

All configuration via `.env` and `data_process/config.py`:
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL_NAME`: LLM config (Gemini via local proxy)
- `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL_NAME`: Zhipu AI embeddings
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j connection
- `PDF_DIR`: Source PDF directory
- `TAVILY_API_KEY`: Web search (optional)

## Development Notes

- Triple extraction uses `GeoTripleExtractor._extract_json_array()` with 4 fallback strategies for robust JSON parsing from LLM responses
- Self-referential triples (subject == object name) are filtered in `utils.validate_triple()`
- Global triple deduplication by `(subject_name, relation_name, object_name)` key
- Text chunks stored as `Chunk` entities with MENTIONS relationships enable hybrid RAG (graph + text retrieval)

## Git Structure

Active development on `project/agentic-rag` branch. Original LangGraph tutorial commits preserved in history; current implementation diverges with geological domain adaptation using LlamaIndex + Neo4j instead of LangChain + Chroma.
