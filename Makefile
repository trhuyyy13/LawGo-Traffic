.PHONY: up down build logs shell-api ingest chunks index eval lint test

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash

# Data pipeline (runs inside api container)
ingest:
	docker compose exec api python scripts/ingest_docx.py --input data/raw --output data/extracted

chunks:
	docker compose exec api python scripts/build_chunks.py --input data/extracted --output data/chunks

index:
	docker compose exec api python scripts/build_graph_index.py --chunks data/chunks/children.jsonl

eval:
	docker compose exec api python scripts/run_eval.py --questions data/eval/golden_questions.sample.json

lint:
	docker compose exec api ruff check src/ tests/

test:
	docker compose exec api pytest tests/ -v
