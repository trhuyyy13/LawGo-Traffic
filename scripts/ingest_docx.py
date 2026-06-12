"""Extract text from .docx files in raw_dir and save JSON to output_dir.

Usage:
    python scripts/ingest_docx.py [--input data/raw] [--output data/extracted]
"""
import argparse

from lawgo_traffic.ingestion.docx_extractor import extract_all_docx

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract .docx → JSON paragraphs")
    parser.add_argument("--input", default="data/raw", help="Directory with .docx files")
    parser.add_argument("--output", default="data/extracted", help="Output directory for JSON")
    args = parser.parse_args()

    saved = extract_all_docx(args.input, args.output)
    print(f"\n✓ Extracted {len(saved)} files → {args.output}")
