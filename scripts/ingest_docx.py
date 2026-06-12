"""Extract text from .docx files in raw_dir and save to output_dir."""
import argparse

from lawgo_traffic.ingestion.docx_extractor import extract_all_docx

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw")
    parser.add_argument("--output", default="data/extracted")
    args = parser.parse_args()
    extract_all_docx(args.input, args.output)
