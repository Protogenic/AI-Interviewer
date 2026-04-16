from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple


os.environ["POSTHOG_DISABLED"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
from chromadb.errors import InvalidCollectionException
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("index_chroma")

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


def to_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for k, v in row.items():
        if k in ("text", "chunk_id"):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            meta[k] = v
        else:
            meta[k] = json.dumps(v, ensure_ascii=False)
    return meta


def format_eta(seconds: float) -> str:
    seconds = max(0.0, seconds)
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m:d}m {s:02d}s"
    return f"{s:d}s"


def main() -> None:
    parser = argparse.ArgumentParser(description="Index chunks JSONL to Chroma (2 embed models, fixed + progress).")
    parser.add_argument("file_jsonl", type=Path)
    parser.add_argument("persist_dir", type=Path)
    parser.add_argument("collection_name", type=str)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    chunks_path: Path = args.file_jsonl
    persist_dir: Path = args.persist_dir
    base_collection_name: str = args.collection_name

    if not chunks_path.exists():
        raise FileNotFoundError(chunks_path)

    rows = [r for r in iter_jsonl(chunks_path) if r.get("chunk_id") and r.get("text")]
    if not rows:
        LOG.warning("No rows to index in %s", chunks_path)
        return

    ids = [str(r["chunk_id"]) for r in rows]
    docs = [str(r["text"]) for r in rows]
    metas = [to_metadata(r) for r in rows]

    client = chromadb.PersistentClient(path=str(persist_dir))

    total = len(docs)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    LOG.info("Loaded %d chunks from %s", total, chunks_path)
    LOG.info("Persist dir: %s, batch_size=%d, batches=%d", persist_dir, BATCH_SIZE, total_batches)

    for model_name, suffix in EMBED_MODELS:
        collection_name = f"{base_collection_name}_{suffix}"

        LOG.info("Collection: %s", collection_name)
        LOG.info("Embed model: %s", model_name)
        LOG.info("Indexing %d chunks", total)

        try:
            col = client.get_or_create_collection(name=collection_name)
        except InvalidCollectionException as e:
            raise RuntimeError(f"Could not create/get collection {collection_name}: {e}") from e

        embedder = SentenceTransformer(model_name)

        t0 = time.time()
        processed = 0
        last_log_time = t0

        for b in range(total_batches):
            start = b * BATCH_SIZE
            end = min(total, start + BATCH_SIZE)

            batch_docs = docs[start:end]
            batch_ids = ids[start:end]
            batch_metas = metas[start:end]

            emb = embedder.encode(
                batch_docs,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).astype("float32")

            col.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
                embeddings=emb.tolist(),
            )

            processed = end

            now = time.time()
            elapsed = now - t0
            speed = processed / elapsed if elapsed > 0 else 0.0
            remaining = total - processed
            eta = remaining / speed if speed > 0 else float("inf")

            if (now - last_log_time) >= 0.3 or processed == total:
                LOG.info(
                    "[%s] batch %d/%d, %d/%d chunks, %.1f chunks/s, ETA %s",
                    suffix,
                    b + 1,
                    total_batches,
                    processed,
                    total,
                    speed,
                    format_eta(eta),
                )
                last_log_time = now

        total_time = time.time() - t0
        LOG.info("Done collection=%s, time=%s, avg_speed=%.1f chunks/s",
                 collection_name, format_eta(total_time), (total / total_time) if total_time > 0 else 0.0)

    LOG.info("All done.")


if __name__ == "__main__":
    main()
