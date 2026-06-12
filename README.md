# LawGo Traffic

AI Legal Advisory Agent for Vietnam Traffic Law — powered by LightRAG + GraphRAG + ReAct Agent.

## Architecture

```
User (text / voice)
  ↓
Main Agent (LangGraph ReAct)
  ├── legal_rag_search   ← LightRAG + Qdrant + Neo4j
  ├── fine_calculator
  ├── rights_checker
  ├── authority_checker
  └── procedure_lookup
  ↓
Final answer with citations (Điều / Khoản / Điểm)
```

## Tech Stack

| Layer | Tech |
|-------|------|
| API | FastAPI |
| UI | Streamlit |
| Agent | LangGraph (ReAct) |
| GraphRAG | LightRAG |
| Vector DB | Qdrant Cloud |
| Graph DB | Neo4j AuraDB Free |
| Relational / Storage | Supabase PostgreSQL + Storage |
| Cache | Redis |
| Container | Docker Compose |

## Quick Start

```bash
cp .env.example .env
# Fill in your cloud credentials in .env

make build
make up
```

- API: http://localhost:8080
- UI:  http://localhost:8501
- API docs: http://localhost:8080/docs

## Data Pipeline

```bash
make ingest   # Word → extracted JSON
make chunks   # extracted JSON → parents.jsonl + children.jsonl
make index    # children.jsonl → LightRAG + Qdrant + Neo4j
make eval     # Run golden question evaluation
```

## Development

```bash
make test     # pytest inside api container
make lint     # ruff check
make shell-api  # bash into api container
```

## Folder Structure

```
src/lawgo_traffic/
  api/          FastAPI app + routes + schemas
  agent/        Main agent, intent router, prompts
  ingestion/    docx extractor, legal parser, chunk builder
  graph/        schema, structural & semantic graph builders, Neo4j store
  rag/          LightRAG adapter, vector/BM25 retriever, citation mapper, legal_rag_search tool
  tools/        fine_calculator, rights_checker, authority_checker, procedure_lookup
  voice/        STT adapter (PhoWhisper), TTS adapter (Edge-TTS)
  eval/         metrics, evaluator
  utils/        jsonl helpers, text normalizer

ui/             Streamlit pages
scripts/        CLI pipeline scripts
data/
  raw/          Original .docx files
  extracted/    Text-extracted JSON
  parsed/       Parsed legal units JSON
  chunks/       parents.jsonl + children.jsonl
  graph/        LightRAG index + chunk_mapping.json
  eval/         Golden question sets
```

## Current Limitations

- All modules are stubs — no logic implemented yet.
- Voice requires `VOICE_ENABLED=true` and manual PhoWhisper install.
- Cloud services (Supabase, Qdrant, Neo4j AuraDB) require separate account setup.
