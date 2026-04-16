from __future__ import annotations

import argparse, json, logging, os, time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

os.environ["POSTHOG_DISABLED"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
from sentence_transformers import SentenceTransformer

LOG = logging.getLogger("index_chroma_cases")

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

def to_metadata(row: Dict[str, Any], drop: set[str]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for k, v in row.items():
        if k in drop:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            meta[k] = v
        else:
            meta[k] = json.dumps(v, ensure_ascii=False)
    return meta

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases_jsonl", type=Path)
    ap.add_argument("persist_dir", type=Path)
    ap.add_argument("base_name", type=str)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    rows = [r for r in iter_jsonl(args.cases_jsonl) if r.get("case_id") and r.get("state_text") and r.get("next_question")]
    if not rows:
        LOG.warning("No rows in %s", args.cases_jsonl)
        return

    client = chromadb.PersistentClient(path=str(args.persist_dir))
    ids = [str(r["case_id"]) for r in rows]
    state_docs = [str(r["state_text"]) for r in rows]
    q_docs = [str(r["next_question"]) for r in rows]
    state_metas = [to_metadata(r, drop={"state_text"}) for r in rows]
    q_metas = [to_metadata(r, drop={"next_question"}) for r in rows]

    for model_name, suffix in EMBED_MODELS:
        LOG.info("=== Model=%s (%s) ===", model_name, suffix)
        embedder = SentenceTransformer(model_name)

        col_state = client.get_or_create_collection(f"{args.base_name}_state_{suffix}")
        col_q = client.get_or_create_collection(f"{args.base_name}_q_{suffix}")

        for start in range(0, len(rows), BATCH_SIZE):
            end = min(len(rows), start + BATCH_SIZE)
            emb = embedder.encode(state_docs[start:end], show_progress_bar=False, convert_to_numpy=True).astype("float32")
            col_state.upsert(
                ids=ids[start:end],
                documents=state_docs[start:end],
                metadatas=state_metas[start:end],
                embeddings=emb.tolist(),
            )

        for start in range(0, len(rows), BATCH_SIZE):
            end = min(len(rows), start + BATCH_SIZE)
            emb = embedder.encode(q_docs[start:end], show_progress_bar=False, convert_to_numpy=True).astype("float32")
            col_q.upsert(
                ids=ids[start:end],
                documents=q_docs[start:end],
                metadatas=q_metas[start:end],
                embeddings=emb.tolist(),
            )

        LOG.info("Done suffix=%s (cases=%d)", suffix, len(rows))

if __name__ == "__main__":
    main()
