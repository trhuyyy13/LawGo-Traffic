"""Parse extracted JSON and build parent/child JSONL chunks.

Usage:
    python scripts/build_chunks.py [--input data/extracted] [--output data/chunks]

Pipeline:
    data/extracted/*.json  →  data/chunks/parents.jsonl
                           →  data/chunks/children.jsonl
"""
import argparse
import json
from pathlib import Path

from lawgo_traffic.ingestion.chunk_builder import build_all_chunks, build_validation_report
from lawgo_traffic.ingestion.legal_parser import parse_legal_document
from lawgo_traffic.utils.jsonl import save_jsonl


def main(input_dir: str, output_dir: str) -> None:
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    all_parents: list[dict] = []
    all_children: list[dict] = []
    all_reports: list[dict] = []

    json_files = sorted(in_path.glob("*.json"))
    if not json_files:
        print(f"[ERROR] No JSON files found in {input_dir}. Run `make ingest` first.")
        return

    for json_file in json_files:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        source_file = data["source_file"]
        doc_id = data["doc_id"]
        document_title = data["document_title"]
        paragraphs: list[str] = data["paragraphs"]

        print(f"\n--- Parsing {source_file} ---")
        articles = parse_legal_document(paragraphs, doc_id, document_title, source_file)
        parents, children = build_all_chunks(articles)

        report = build_validation_report(source_file, doc_id, articles, parents, children)
        all_reports.append(report)
        all_parents.extend(parents)
        all_children.extend(children)

    # Save JSONL
    parents_path = out_path / "parents.jsonl"
    children_path = out_path / "children.jsonl"
    save_jsonl(all_parents, str(parents_path))
    save_jsonl(all_children, str(children_path))

    # Save validation reports
    reports_path = out_path / "validation_report.json"
    reports_path.write_text(
        json.dumps(all_reports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'='*60}")
    print(f"✓ {len(all_parents)} parent chunks  → {parents_path}")
    print(f"✓ {len(all_children)} child chunks   → {children_path}")
    print(f"✓ Validation report → {reports_path}")
    print(f"{'='*60}")

    # Surface any critical warnings
    critical_codes = {"W01", "W02", "W05"}
    for report in all_reports:
        critical = [w for w in report["warnings"] if any(w.startswith(c) for c in critical_codes)]
        if critical:
            print(f"\n[CRITICAL] {report['source_file']}:")
            for w in critical:
                print(f"  {w}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build parent/child JSONL chunks from extracted JSON")
    parser.add_argument("--input", default="data/extracted", help="Directory with extracted JSON files")
    parser.add_argument("--output", default="data/chunks", help="Output directory for JSONL")
    args = parser.parse_args()
    main(args.input, args.output)
