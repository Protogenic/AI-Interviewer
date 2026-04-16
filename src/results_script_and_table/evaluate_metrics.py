from __future__ import annotations

import argparse
import csv
import json
import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LOG = logging.getLogger("evaluate_metrics")


def read_lines(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Bad JSON on line {i} in {path}: {e}") from e
    return rows


def detect_generated_field(sample_row: Dict[str, Any], preferred: str) -> str:
    if preferred in sample_row:
        return preferred
    for cand in ["generated_question", "generated", "prediction", "output", "answer", "text"]:
        if cand in sample_row:
            return cand
    return preferred


def char_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def masked_mean(xs: List[float], mask: List[bool]) -> float:
    vals = [x for x, m in zip(xs, mask) if m]
    return mean(vals)


def compute_bertscore_f1(
    cands: List[str],
    refs: List[str],
    model_type: str,
    batch_size: int,
    device: Optional[str] = None,
    lang: str = "ru",
) -> List[float]:
    try:
        from bert_score import score as bert_score
    except ImportError as e:
        raise ImportError("Install: pip install bert-score") from e

    P, R, F1 = bert_score(
        cands=cands,
        refs=refs,
        lang=lang,
        model_type=model_type,
        verbose=False,
        batch_size=batch_size,
        device=device,
    )
    return [float(x) for x in F1.tolist()]


def compute_embeddings(
    texts: List[str],
    st_model_name: str,
    batch_size: int,
    device: Optional[str] = None,
):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError("Install: pip install sentence-transformers") from e

    model = SentenceTransformer(st_model_name, device=device)
    emb = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_tensor=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return emb


def cosine_for_normalized_pairwise(a_emb, b_emb) -> List[float]:
    sims = (a_emb * b_emb).sum(dim=1)
    return [float(x) for x in sims.detach().cpu().tolist()]


def cosine_to_centroid(a_emb, centroid_emb) -> List[float]:
    sims = (a_emb * centroid_emb).sum(dim=1)
    return [float(x) for x in sims.detach().cpu().tolist()]


def build_style_centroid_texts(
    style_rows: List[Dict[str, Any]],
    text_field: str,
    speaker_field: str,
    speaker_value: Optional[str],
) -> List[str]:
    texts: List[str] = []
    for r in style_rows:
        if speaker_value is not None:
            if str(r.get(speaker_field, "")) != speaker_value:
                continue
        t = r.get(text_field, "")
        if t is None:
            continue
        t = str(t).strip()
        if t:
            texts.append(t)
    return texts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate results/*.jsonl vs original.txt by line index (BERTScore + embeddings cosine + char ratio). "
                    "Optionally compute style similarity vs style jsonl corpus."
    )
    parser.add_argument("inputdir", type=Path, help="Directory containing original.txt (and optionally reference.jsonl for style)")
    parser.add_argument("results_dir", type=Path, help="Directory with model result files (*.jsonl), each line i corresponds to test i")
    parser.add_argument("out_csv", type=Path, help="Detailed output CSV (one row per (model, test_index))")
    parser.add_argument("--summary-csv", type=Path, default=None, help="Optional summary CSV (avg metrics per model)")

    parser.add_argument("--original", type=str, default="original.txt", help="original.txt filename inside inputdir")

    parser.add_argument("--generated-field", type=str, default="generated_question",
                        help="Field name in results jsonl containing generated text")

    parser.add_argument("--bertscore-model", type=str, default="bert-base-multilingual-cased",
                        help="BERTScore model_type (e.g. bert-base-multilingual-cased, xlm-roberta-large)")
    parser.add_argument("--st-model", type=str, default="paraphrase-multilingual-MiniLM-L12-v2",
                        help="SentenceTransformer model name")

    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", type=str, default=None, help="cpu, cuda, cuda:0 ...")
    parser.add_argument("--lang", type=str, default="ru", help="Language for BERTScore (ru/en/...)")

    parser.add_argument("--style-jsonl", type=Path, default=None,
                        help="Optional jsonl corpus to build 'style centroid' and compute style_cosine")
    parser.add_argument("--style-text-field", type=str, default="text", help="Text field in style jsonl")
    parser.add_argument("--style-speaker-field", type=str, default="speaker", help="Speaker field in style jsonl")
    parser.add_argument("--style-speaker-value", type=str, default=None,
                        help="If set, only rows with speaker==this value are used for style centroid")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    inputdir: Path = args.inputdir
    results_dir: Path = args.results_dir
    out_csv: Path = args.out_csv
    summary_csv: Optional[Path] = args.summary_csv

    original_path = inputdir / args.original
    if not original_path.exists():
        raise FileNotFoundError(original_path)
    if not results_dir.exists():
        raise FileNotFoundError(results_dir)

    refs = read_lines(original_path)
    refs = [r for r in refs if r.strip() != ""]

    if not refs:
        raise ValueError("original.txt is empty (after stripping empty lines)")

    result_files = sorted(results_dir.glob("*.jsonl"))
    if not result_files:
        raise FileNotFoundError(f"No *.jsonl found in {results_dir}")

    style_centroid = None
    if args.style_jsonl is not None:
        if not args.style_jsonl.exists():
            raise FileNotFoundError(args.style_jsonl)

        style_rows = read_jsonl(args.style_jsonl)
        style_texts = build_style_centroid_texts(
            style_rows,
            text_field=args.style_text_field,
            speaker_field=args.style_speaker_field,
            speaker_value=args.style_speaker_value,
        )
        if not style_texts:
            raise ValueError("style_jsonl produced 0 texts for centroid (check speaker filter/fields)")

        LOG.info("Computing style centroid from %d texts...", len(style_texts))
        style_emb = compute_embeddings(
            texts=style_texts,
            st_model_name=args.st_model,
            batch_size=args.batch_size,
            device=args.device,
        )
        import torch
        centroid = style_emb.mean(dim=0, keepdim=True)
        centroid = torch.nn.functional.normalize(centroid, p=2, dim=1)
        style_centroid = centroid

    detailed_fields = [
        "test_index",
        "test_id",
        "model",
        "reference",
        "generated",
        "missing_generated",
        "bertscore_f1",
        "emb_cosine",
        "char_ratio",
    ]
    if style_centroid is not None:
        detailed_fields.append("style_cosine")

    summary_fields = [
        "model",
        "n",
        "missing_generated",
        "avg_bertscore_f1",
        "avg_emb_cosine",
        "avg_char_ratio",
    ]
    if style_centroid is not None:
        summary_fields.append("avg_style_cosine")

    detailed_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for rf in result_files:
        model_name = rf.stem
        rows = read_jsonl(rf)
        if not rows:
            LOG.warning("Empty results file: %s", rf)
            continue

        if len(rows) != len(refs):
            raise ValueError(
                f"Count mismatch for model {model_name} ({rf.name}):\n"
                f"results lines: {len(rows)}\n"
                f"original.txt lines: {len(refs)}\n"
                f"Rule: line i in results must correspond to line i in original.txt."
            )

        gen_field = detect_generated_field(rows[0], args.generated_field)

        test_ids: List[str] = []
        cands: List[str] = []
        present_mask: List[bool] = []

        for i, r in enumerate(rows):
            test_id = r.get("test_file") or r.get("id") or r.get("test_id") or f"test_{i:03d}"
            test_ids.append(str(test_id))

            cand = r.get(gen_field, "")
            cand = "" if cand is None else str(cand)
            cands.append(cand)

            present_mask.append(bool(cand.strip()))

        missing_count = present_mask.count(False)

        LOG.info("Model=%s: computing BERTScore...", model_name)
        bert_f1 = compute_bertscore_f1(
            cands=cands,
            refs=refs,
            model_type=args.bertscore_model,
            batch_size=args.batch_size,
            device=args.device,
            lang=args.lang,
        )

        LOG.info("Model=%s: computing embeddings cosine...", model_name)
        ref_emb = compute_embeddings(refs, args.st_model, args.batch_size, args.device)
        cand_emb = compute_embeddings(cands, args.st_model, args.batch_size, args.device)
        emb_cos = cosine_for_normalized_pairwise(cand_emb, ref_emb)

        char_ratios = [char_similarity(c, r) for c, r in zip(cands, refs)]

        style_cos = None
        if style_centroid is not None:
            style_cos = cosine_to_centroid(cand_emb, style_centroid)

        for i, (tid, ref, cand, miss, b, e, ch) in enumerate(
            zip(test_ids, refs, cands, [0 if m else 1 for m in present_mask], bert_f1, emb_cos, char_ratios)
        ):
            row_out = {
                "test_index": i,
                "test_id": tid,
                "model": model_name,
                "reference": ref,
                "generated": cand,
                "missing_generated": miss,
                "bertscore_f1": f"{b:.6f}",
                "emb_cosine": f"{e:.6f}",
                "char_ratio": f"{ch:.6f}",
            }
            if style_cos is not None:
                row_out["style_cosine"] = f"{style_cos[i]:.6f}"
            detailed_rows.append(row_out)

        sum_row = {
            "model": model_name,
            "n": len(refs),
            "missing_generated": missing_count,
            "avg_bertscore_f1": f"{masked_mean(bert_f1, present_mask):.6f}",
            "avg_emb_cosine": f"{masked_mean(emb_cos, present_mask):.6f}",
            "avg_char_ratio": f"{masked_mean(char_ratios, present_mask):.6f}",
        }
        if style_cos is not None:
            sum_row["avg_style_cosine"] = f"{masked_mean(style_cos, present_mask):.6f}"
        summary_rows.append(sum_row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=detailed_fields)
        w.writeheader()
        w.writerows(detailed_rows)
    LOG.info("Wrote detailed CSV: %s (rows=%d)", out_csv, len(detailed_rows))

    if summary_csv is not None:
        summary_csv.parent.mkdir(parents=True, exist_ok=True)
        with summary_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=summary_fields)
            w.writeheader()
            w.writerows(summary_rows)
        LOG.info("Wrote summary CSV: %s (models=%d)", summary_csv, len(summary_rows))


if __name__ == "__main__":
    main()