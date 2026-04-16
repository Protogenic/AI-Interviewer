from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("index_faiss")

BATCH_SIZE = 64
EMBED_MODELS: List[Tuple[str, str]] = [
    ("intfloat/multilingual-e5-base", "e5_base"),
    ("intfloat/multilingual-e5-large", "e5_large"),
]


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Bad JSON in {path} at line {i}: {e}") from e


def l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return x / norms


def batched(lst: List[int], batch_size: int) -> Iterator[List[int]]:
    for i in range(0, len(lst), batch_size):
        yield lst[i : i + batch_size]


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index chunks JSONL to FAISS (2 embed models, fixed).")
    parser.add_argument("file_jsonl", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    chunks_path: Path = args.file_jsonl
    out_dir: Path = args.out_dir

    if not chunks_path.exists():
        raise FileNotFoundError(chunks_path)

    rows = [r for r in iter_jsonl(chunks_path) if r.get("chunk_id") and r.get("text")]
    if not rows:
        LOG.warning("No rows to index in %s", chunks_path)
        return

    ids = [str(r["chunk_id"]) for r in rows]
    texts = [str(r["text"]) for r in rows]

    metas: List[Dict[str, Any]] = []
    for r in rows:
        meta = {k: v for k, v in r.items() if k not in ("text",)}
        metas.append(meta)

    for model_name, suffix in EMBED_MODELS:
        subdir = out_dir / suffix
        subdir.mkdir(parents=True, exist_ok=True)
        LOG.info("Building FAISS index in %s using %s", subdir, model_name)

        embedder = SentenceTransformer(model_name)

        all_emb: List[np.ndarray] = []
        idxs = list(range(len(texts)))
        for batch_idxs in batched(idxs, BATCH_SIZE):
            batch_texts = [texts[i] for i in batch_idxs]
            emb = embedder.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True).astype("float32")
            all_emb.append(emb)

        emb_mat = np.vstack(all_emb)
        emb_mat = l2_normalize(emb_mat)

        dim = emb_mat.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(emb_mat)

        faiss.write_index(index, str(subdir / "index.faiss"))

        store_rows: List[Dict[str, Any]] = []
        meta_rows: List[Dict[str, Any]] = []
        for i, (chunk_id, txt, meta) in enumerate(zip(ids, texts, metas)):
            store_rows.append({"faiss_id": i, "text": txt})
            meta_rows.append({"faiss_id": i, "chunk_id": chunk_id, **{k: meta.get(k) for k in meta if k != "text"}})

        write_jsonl(subdir / "store.jsonl", store_rows)
        write_jsonl(subdir / "meta.jsonl", meta_rows)

        config = {
            "embed_model": model_name,
            "suffix": suffix,
            "batch_size": BATCH_SIZE,
            "metric": "ip_cosine",
            "normalize": True,
            "dim": dim,
            "source_chunks": str(chunks_path),
            "count": len(texts),
        }
        (subdir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

        LOG.info("Done %s (vectors=%d dim=%d)", subdir, len(texts), dim)

    LOG.info("All done.")


if __name__ == "__main__":
    main()
