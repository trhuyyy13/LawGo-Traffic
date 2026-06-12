"""Index child chunks into LightRAG and build structural/semantic graphs."""
import argparse

from lawgo_traffic.rag.lightrag_adapter import LightRAGAdapter
from lawgo_traffic.utils.jsonl import load_jsonl
from lawgo_traffic.config import settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="data/chunks/children.jsonl")
    args = parser.parse_args()
    # TODO: load chunks, build structural graph, call lightrag_adapter.index_chunks
    print("[stub] build_graph_index not implemented yet.")
