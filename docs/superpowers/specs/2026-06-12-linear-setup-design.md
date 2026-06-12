# Linear Setup — LawGo Traffic

> Date: 2026-06-12
> Project: LawGo Traffic (team HUY)
> Scope: Solo project management setup

---

## 1. Approach

Option A — Flat & Simple: 1 project, 7 milestones, labels for module + type. No cycles.

---

## 2. Milestones

| # | Name | Phase |
|---|------|-------|
| M1 | Ingestion & Chunking | docx → parser → chunks |
| M2 | Graph Building | structural + semantic graph |
| M3 | RAG Pipeline | LightRAG + Qdrant + BM25 |
| M4 | Tools | fine_calculator, rights_checker, authority_checker, procedure_lookup |
| M5 | Main Agent | LangGraph ReAct loop |
| M6 | API + UI | FastAPI + Streamlit |
| M7 | Eval | golden questions, metrics |

---

## 3. Labels

**Module (blue):** `ingestion` · `graph` · `rag` · `tools` · `agent` · `api-ui` · `eval`

**Type (orange):** `feature` · `spec` · `result` · `bug` · `infra`

Each issue gets exactly 1 module label + 1 type label.

---

## 4. Statuses

```
Todo → In Progress → Done
                  ↘ Cancelled
```

---

## 5. Issue Convention

**Title:** `[Part N] Module — short description`

**Description template:**
```
## Mục tiêu
...

## Checklist
- [ ] ...

## Result / Output
(fill after done — paste results, metrics, file outputs)
```

**Type usage:**
- `feature` — implement new functionality
- `spec` — design doc / spec
- `result` — log of actual run output (JSON, eval scores, etc.)
- `bug` — something broken
- `infra` — Docker, config, dependencies
