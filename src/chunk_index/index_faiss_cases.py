from __future__ import annotations

import argparse, json, logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("index_faiss_cases")
BATCH_SIZE = 64
EMBED_MODELS: List[Tuple[str, str]] = [
    ("intfloat/multilingual-e5-base", "e5_base"),
    ("intfloat/multilingual-e5-large", "e5_large"),
]

def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return x / norms

def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def build_space(
    *,
    subdir: Path,
    embedder: SentenceTransformer,
    docs: List[str],
    metas: List[Dict[str, Any]],
    ids: List[str],
    space_name: str,
) -> None:
    subdir.mkdir(parents=True, exist_ok=True)

    all_emb: List[np.ndarray] = []
    for start in range(0, len(docs), BATCH_SIZE):
        end = min(len(docs), start + BATCH_SIZE)
        emb = embedder.encode(docs[start:end], show_progress_bar=False, convert_to_numpy=True).astype("float32")
        all_emb.append(emb)
    mat = np.vstack(all_emb)
    mat = l2_normalize(mat)

    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(mat)
    faiss.write_index(index, str(subdir / "index.faiss"))

    store_rows = [{"faiss_id": i, "text": docs[i]} for i in range(len(docs))]
    meta_rows = [{"faiss_id": i, "case_id": ids[i], **metas[i]} for i in range(len(docs))]

    write_jsonl(subdir / "store.jsonl", store_rows)
    write_jsonl(subdir / "meta.jsonl", meta_rows)
    (subdir / "config.json").write_text(
        json.dumps(
            {
                "space": space_name,
                "metric": "ip_cosine",
                "normalize": True,
                "dim": dim,
                "count": len(docs),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases_jsonl", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    rows = [r for r in iter_jsonl(args.cases_jsonl) if r.get("case_id") and r.get("state_text") and r.get("next_question")]
    if not rows:
        LOG.warning("No rows in %s", args.cases_jsonl)
        return

    ids = [str(r["case_id"]) for r in rows]
    state_docs = [str(r["state_text"]) for r in rows]
    q_docs = [str(r["next_question"]) for r in rows]

    common_meta = []
    for r in rows:
        common_meta.append(
            {
                "interview_id": r.get("interview_id"),
                "source_file": r.get("source_file"),
                "turn_id_start": r.get("turn_id_start"),
                "turn_id_end": r.get("turn_id_end"),
                "state_token_len": r.get("state_token_len"),
                "nextq_token_len": r.get("nextq_token_len"),
                "is_yesno": r.get("is_yesno"),
                "q_wh": r.get("q_wh"),
                "opener_particle": r.get("opener_particle"),
                "has_named_entity": r.get("has_named_entity"),
            }
        )

    for model_name, suffix in EMBED_MODELS:
        embedder = SentenceTransformer(model_name)
        base = args.out_dir / suffix
        LOG.info("=== %s ===", base)

        build_space(
            subdir=base / "state",
            embedder=embedder,
            docs=state_docs,
            metas=[{**m, "next_question": q_docs[i]} for i, m in enumerate(common_meta)],
            ids=ids,
            space_name="state",
        )
        build_space(
            subdir=base / "q",
            embedder=embedder,
            docs=q_docs,
            metas=[{**m, "state_preview": state_docs[i][-500:]} for i, m in enumerate(common_meta)],
            ids=ids,
            space_name="q",
        )
        LOG.info("Done %s", base)

if __name__ == "__main__":
    main()
