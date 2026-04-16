from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List


LOG = logging.getLogger("make_table")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def index_by_test_file(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        tf = str(r.get("test_file", ""))
        if tf:
            out[tf] = r
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build final CSV table from results/*.jsonl")
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("out_csv", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    results_dir: Path = args.results_dir
    out_csv: Path = args.out_csv

    expected = {
        "gpt_only_temp_0_7": results_dir / "gpt_only_temp_0_7.jsonl",
        "gpt_chroma_io_temp_0_3": results_dir / "gpt_chroma_io_temp_0_3.jsonl",
        "gpt_chroma_io_temp_0_7": results_dir / "gpt_chroma_io_temp_0_7.jsonl",
        "gpt_chroma_qa_temp_0_3": results_dir / "gpt_chroma_qa_temp_0_3.jsonl",
        "gpt_chroma_qa_temp_0_7": results_dir / "gpt_chroma_qa_temp_0_7.jsonl",
        "gpt_faiss_qa_temp_0_3": results_dir / "gpt_faiss_qa_temp_0_3.jsonl",
        "gpt_faiss_qa_temp_0_7": results_dir / "gpt_faiss_qa_temp_0_7.jsonl",
        "qwen_only_cases": results_dir / "qwen_only_cases.jsonl",
        "qwen_chroma_cases_templates_temp_0_7": results_dir / "qwen_chroma_cases_templates_temp_0_7.jsonl",
    }

    missing = [name for name, p in expected.items() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing result files: {missing}")

    gpt_only_temp_0_7 = index_by_test_file(read_jsonl(expected["gpt_only_temp_0_7"]))
    gpt_chroma_io_temp_0_3 = index_by_test_file(read_jsonl(expected["gpt_chroma_io_temp_0_3"]))
    gpt_chroma_io_temp_0_7 = index_by_test_file(read_jsonl(expected["gpt_chroma_io_temp_0_7"]))
    gpt_chroma_qa_temp_0_3 = index_by_test_file(read_jsonl(expected["gpt_chroma_qa_temp_0_3"]))
    gpt_chroma_qa_temp_0_7 = index_by_test_file(read_jsonl(expected["gpt_chroma_qa_temp_0_7"]))
    gpt_faiss_qa_temp_0_3 = index_by_test_file(read_jsonl(expected["gpt_faiss_qa_temp_0_3"]))
    gpt_faiss_qa_temp_0_7 = index_by_test_file(read_jsonl(expected["gpt_faiss_qa_temp_0_7"]))
    qwen_only_cases = index_by_test_file(read_jsonl(expected["qwen_only_cases"]))
    qwen_chroma_cases_templates_temp_0_7 = index_by_test_file(read_jsonl(expected["qwen_chroma_cases_templates_temp_0_7"]))

    all_test_files = sorted(set(gpt_only_temp_0_7.keys()) | set(gpt_chroma_io_temp_0_3.keys()) | set(gpt_faiss_qa_temp_0_3.keys()))
    if not all_test_files:
        LOG.warning("No rows found.")
        return

    cols = [
        "test_file",
        "gpt_only_temp_0_7",
        "gpt_chroma_io_temp_0_3",
        "gpt_chroma_io_temp_0_7",
        "gpt_chroma_qa_temp_0_3",
        "gpt_chroma_qa_temp_0_7",
        "gpt_faiss_qa_temp_0_3",
        "gpt_faiss_qa_temp_0_7",
        "qwen_only_cases",
        "qwen_chroma_cases_templates_temp_0_7"
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for tf in all_test_files:
            w.writerow(
                {
                    "test_file": tf,
                    "gpt_only_temp_0_7": (gpt_only_temp_0_7.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_chroma_io_temp_0_3": (gpt_chroma_io_temp_0_3.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_chroma_io_temp_0_7": (gpt_chroma_io_temp_0_7.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_chroma_qa_temp_0_3": (gpt_chroma_qa_temp_0_3.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_chroma_qa_temp_0_7": (gpt_chroma_qa_temp_0_7.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_faiss_qa_temp_0_3": (gpt_faiss_qa_temp_0_3.get(tf, {}) or {}).get("generated_question", ""),
                    "gpt_faiss_qa_temp_0_7": (gpt_faiss_qa_temp_0_7.get(tf, {}) or {}).get("generated_question", ""),
                    "qwen_only_cases": (qwen_only_cases.get(tf, {}) or {}).get("generated_question", ""),
                    "qwen_chroma_cases_templates_temp_0_7": (qwen_chroma_cases_templates_temp_0_7.get(tf, {}) or {}).get("generated_question", ""),
                }
            )

    LOG.info("Wrote %s (rows=%d)", out_csv, len(all_test_files))


if __name__ == "__main__":
    main()
