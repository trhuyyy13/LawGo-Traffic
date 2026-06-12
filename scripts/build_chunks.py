"""Parse extracted JSON and build parent/child JSONL chunks."""
import argparse

from lawgo_traffic.ingestion.chunk_builder import build_all_chunks
from lawgo_traffic.utils.jsonl import save_jsonl

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/extracted")
    parser.add_argument("--output", default="data/chunks")
    args = parser.parse_args()
    # TODO: load parsed units and call build_all_chunks
    print("[stub] build_chunks not implemented yet.")
