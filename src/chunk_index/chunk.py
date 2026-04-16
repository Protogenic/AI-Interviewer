from __future__ import annotations

import argparse
import json
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Literal


LOG = logging.getLogger("chunk")

Mode = Literal["qa_pair", "interviewer_only"]
MAX_TOKENS_VARIANTS = (500, 700, 1000)

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def normalize_spaces(s: str) -> str:
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


@dataclass(frozen=True)
class PieceInterview:
    interview_id: str
    source_file: str
    replica_id: int
    speaker: str
    text: str


def reading_jsonl(path: Path) -> Iterator[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Bad JSON in {path} at line {i}: {e}") from e


def load_pieces(path: Path) -> List[PieceInterview]:
    pieces: List[PieceInterview] = []
    for obj in reading_jsonl(path):
        text = normalize_spaces(str(obj.get("text", "")))
        if not text:
            continue
        pieces.append(
            PieceInterview(
                interview_id=str(obj.get("interview_id", path.stem)),
                source_file=str(obj.get("source_file", path.name)),
                replica_id=int(obj.get("replica_id", len(pieces))),
                speaker=str(obj.get("speaker", "")),
                text=text,
            )
        )
    pieces.sort(key=lambda t: t.turn_id)
    return pieces


def build_chunk_row(dataset: str, mode: Mode, interview_id: str, source_file: str, pieces: List[PieceInterview], text: str) -> Dict:
    text = normalize_spaces(text)
    token_len = len(TOKEN_RE.findall(text))
    char_len = len(text)
    return {
        "chunk_id": str(uuid.uuid4()),
        "dataset": dataset,
        "mode": mode,
        "interview_id": interview_id,
        "source_file": source_file,
        "replica_id_start": pieces[0].replica_id,
        "replica_id_end": pieces[-1].replica_id,
        "text": text,
        "num_pieces": len(pieces),
        "token_len": token_len,
        "char_len": char_len,
    }


def chunk_interviewer_only(pieces: List[PieceInterview], max_tokens: int, overlap_pieces: int = 1) -> List[Dict]:
    interviewer = [piece for piece in pieces if piece.speaker == "interviewer" and piece.text]
    if not interviewer:
        return []

    out: List[Dict] = []
    buf: List[PieceInterview] = []
    buf_tokens = 0

    def chunking() -> None:
        nonlocal buf, buf_tokens
        if not buf:
            return
        text = "\n".join(t.text for t in buf)
        out.append(
            build_chunk_row(
                dataset="",
                mode="interviewer_only",
                interview_id=buf[0].interview_id,
                source_file=buf[0].source_file,
                pieces=buf,
                text=text,
            )
        )
        if overlap_pieces > 0:
            buf = buf[-overlap_pieces:]
            buf_tokens = sum(len(TOKEN_RE.findall(piece.text)) for piece in buf)
        else:
            buf = []
            buf_tokens = 0

    for piece in interviewer:
        piece_tokens = len(TOKEN_RE.findall(piece.text))
        if not buf:
            buf = [piece]
            buf_tokens = piece_tokens
            if buf_tokens >= max_tokens:
                chunking()
            continue

        if buf_tokens + piece_tokens <= max_tokens:
            buf.append(piece)
            buf_tokens += piece_tokens
        else:
            chunking()
            buf = [piece]
            buf_tokens = piece_tokens
            if buf_tokens >= max_tokens:
                chunking()

    chunking()
    return out


def chunk_qa_pair(turns: List[PieceInterview], max_tokens: int, max_answer_pieces: int = 5) -> List[Dict]:
    out: List[Dict] = []
    n = len(turns)
    i = 0

    while i < n:
        while i < n and turns[i].speaker != "interviewer":
            i += 1
        if i >= n:
            break

        q_turns: List[PieceInterview] = []
        q_tokens = 0
        while i < n and turns[i].speaker == "interviewer":
            t = turns[i]
            t_tokens = len(TOKEN_RE.findall(t.text))
            if not q_turns or q_tokens + t_tokens <= max_tokens:
                q_turns.append(t)
                q_tokens += t_tokens
                i += 1
            else:
                break

        a_turns: List[PieceInterview] = []
        a_tokens = 0
        while i < n and turns[i].speaker != "interviewer" and len(a_turns) < max_answer_pieces:
            t = turns[i]
            t_tokens = len(TOKEN_RE.findall(t.text))
            if a_turns and (q_tokens + a_tokens + t_tokens) > max_tokens:
                break
            a_turns.append(t)
            a_tokens += t_tokens
            i += 1

        q_text = "\n".join(t.text for t in q_turns).strip()
        a_text = "\n".join(t.text for t in a_turns).strip()
        if a_turns:
            text = f"Q:\n{q_text}\n\nA:\n{a_text}"
            chunk_turns = q_turns + a_turns
        else:
            text = f"Q:\n{q_text}"
            chunk_turns = q_turns

        out.append(
            build_chunk_row(
                dataset="",
                mode="qa_pair",
                interview_id=chunk_turns[0].interview_id,
                source_file=chunk_turns[0].source_file,
                pieces=chunk_turns,
                text=text,
            )
        )
    return out


def write_jsonl(path: Path, rows: Iterable[Dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    number_chunks = 0
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
            number_chunks += 1
    return number_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk cleaned JSONL into RAG datasets.")
    parser.add_argument("in_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("mode", type=str, choices=["qa_pair", "interviewer_only"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    in_dir: Path = args.in_dir
    out_dir: Path = args.out_dir
    mode: Mode = args.mode

    files = sorted([path_file for path_file in in_dir.rglob("*.jsonl") if path_file.is_file()])
    if not files:
        LOG.warning("No .jsonl found in %s", in_dir)
        return

    LOG.info("Found %d cleaned files in %s", len(files), in_dir)

    for max_tokens in MAX_TOKENS_VARIANTS:
        dataset_name = f"{'qa' if mode == 'qa_pair' else 'interviewer'}_{max_tokens}"
        dataset_dir = out_dir / mode / str(max_tokens)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        out_path = dataset_dir / f"{dataset_name}.jsonl"

        all_rows: List[Dict] = []
        for files_piece in files:
            pieces = load_pieces(files_piece)
            if not pieces:
                continue
            if mode == "qa_pair":
                rows = chunk_qa_pair(pieces, max_tokens=max_tokens, max_answer_pieces=5)
            else:
                rows = chunk_interviewer_only(pieces, max_tokens=max_tokens, overlap_pieces=1)

            for r in rows:
                r["dataset"] = dataset_name
            all_rows.extend(rows)

        n = write_jsonl(out_path, all_rows)
        LOG.info("Wrote dataset=%s:  %s (chunks=%d)", dataset_name, out_path, n)

    LOG.info("Done.")


if __name__ == "__main__":
    main()
