# Repository Guidelines

## Project Structure & Module Organization
- `data_process/`: PDF ingest pipeline (loader, triple extractor, Neo4j graph builder) plus `main.py` orchestration.
- `vision_process/`: computer-vision adapters for geological maps; extend here for map tiling, coordinate transforms, and model checkpoints.
- `graph/` (tracked history) + `ingestion.py`: LangGraph agent wiring, retriever bootstrap, and shared config helpers.
- `llama_index/` and `data/`: experimental notebooks and raw assets (PDFs, PNGs, text dumps). Keep generated triples under repo root (`geology_triples_test.json`) and logs in `logs/`.

## Build, Test, and Development Commands
- `python -m venv .venv` then `.\.venv\Scripts\activate` to isolate dependencies.
- `pip install -r requirements.txt` installs LangChain, LangGraph, Neo4j, pytest, black, and supporting CV libs.
- `python data_process/main.py` chunks PDFs, extracts triples, persists them to Neo4j, and emits sample queries.
- `python main.py` runs the LangGraph agent (LLM chat endpoint + MCP/web-search tool interfaces configured in `.env`).
- `pytest data_process` executes extractor/graph utilities; add new suites beside the modules they cover.

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indents, and informative type hints. Modules use `snake_case.py`; classes in `PascalCase`; node/tool IDs in `lower-hyphen` when surfaced to LangGraph.
- Run `black .` and `isort .` before commits; CI expects default profiles. Keep docstrings bilingual only where user-facing logs demand it.

## Testing Guidelines
- Prefer pytest functions named `test_<feature>`. Mirror `data_process` structure (`tests/test_pdf_loader.py`, etc.) and use fixtures for sample PDFs/maps.
- Validate Neo4j writes with local Bolt test containers or a stubbed `graph_store`. Capture coverage targets (>=80% for utility layers) via `pytest --cov=data_process`.

## Commit & Pull Request Guidelines
- Adopt Conventional Commits (`feat: add vision chunk projector`, `fix(graph): guard empty triples)` as seen in git history.
- Squash noisy experiments; commits should document intent and key parameters (LLM models, prompt IDs).
- PRs must explain scenario, link issues or experiment IDs, describe data sources touched, and attach console screenshots for agent runs (include queries + answers referencing graph background knowledge and network/MCP tool usage).

## Agent & Security Notes
- Store secrets in `.env` (`OPENAI_API_KEY`, `EMBEDDING_*`, `NEO4J_*`). Never hardcode keys or map tiles.
- Ensure every tool (local KG query, visual interpreter, web search, MCP connectors) validates inputs and logs provenance so the agent can cite whether answers come from the geological graph, online retrieval, or vision outputs.
