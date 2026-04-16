from __future__ import annotations

import argparse, json, logging, re, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

LOG = logging.getLogger("chunk_cases")
TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

WHY_WORDS = ("почему", "зачем", "кто", "что", "когда", "где", "сколько", "какой", "какая", "какие", "каков", "как")
YESNO_WORDS = ("ты", "вы", "он", "она", "они", "это", "правда", "разве", "неужели", "бывало", "было")
OPENERS_WORDS = ("о", "ага", "слушай", "подожди", "то есть", "окей", "ну", "и что", "и ты", "смотри")

CYR_CAPITAL = re.compile(r"\b[А-ЯЁ][а-яё]+\b")


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

def iter_jsonl(path: Path) -> Iterator[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def reading_pieces(path: Path) -> List[PieceInterview]:
    pieces: List[PieceInterview] = []
    for obj in iter_jsonl(path):
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
    pieces.sort(key=lambda t: t.replica_id)
    return pieces

def collect_question(pieces: List[PieceInterview], i: int) -> Tuple[List[PieceInterview], int]:
    q: List[PieceInterview] = []
    while i < len(pieces) and pieces[i].speaker == "interviewer":
        q.append(pieces[i]); i += 1
    return q, i

def collect_answer(pieces: List[PieceInterview], i: int) -> Tuple[List[PieceInterview], int]:
    a: List[PieceInterview] = []
    while i < len(pieces) and pieces[i].speaker != "interviewer":
        a.append(pieces[i]); i += 1
    return a, i

def question_open_word(question: str) -> str:
    question_word = question.strip().lower()
    for open_word in OPENERS_WORDS:
        if question_word.startswith(open_word + " ") or question_word == open_word:
            return open_word
    return ""

def question_yesno(question: str) -> bool:
    question_word = question.strip().lower()
    first_word = question_word.split(" ", 1)[0] if question_word else ""
    return first_word in YESNO_WORDS

def question_why(question: str) -> str:
    question_word = question.strip().lower()
    for why_word in WHY_WORDS:
        if question_word.startswith(why_word + " ") or question_word == why_word:
            return why_word
    return ""

def has_named_entity(text: str) -> bool:
    return bool(CYR_CAPITAL.search(text))

def build_cases(pieces: List[PieceInterview], window_pairs: int) -> List[Dict]:
    pairs: List[Tuple[List[PieceInterview], List[PieceInterview]]] = []
    i = 0
    len_pieces = len(pieces)
    while i < len_pieces:
        while i < len_pieces and pieces[i].speaker != "interviewer":
            i += 1
        if i >= len_pieces: break
        question, i = collect_question(pieces, i)
        answer, i = collect_answer(pieces, i)
        if question and answer:
            pairs.append((question, answer))

    out: List[Dict] = []
    for j in range(len(pairs) - 1):
        start = max(0, j - (window_pairs - 1))
        state_qa = pairs[start : j + 1]
        next_q_pieces = pairs[j + 1][0]

        state_text = []
        piece_start = state_qa[0][0][0].replica_id
        piece_end = state_qa[-1][1][-1].replica_id

        for (question_in_piece, answer_in_piece) in state_qa:
            question_text = "\n".join(t.text for t in question_in_piece).strip()
            answer_text = "\n".join(t.text for t in answer_in_piece).strip()
            state_text.append(f"Q:\n{question_text}\nA:\n{answer_text}")
        state_text_norm = normalize_spaces("\n\n".join(state_text))

        next_question = normalize_spaces("\n".join(t.text for t in next_q_pieces))
        if not next_question.endswith("?"):
            next_question = next_question.rstrip(".") + "?"

        out.append(
            {
                "case_id": str(uuid.uuid4()),
                "interview_id": state_qa[0][0][0].interview_id,
                "source_file": state_qa[0][0][0].source_file,
                "replica_id_start": piece_start,
                "replica_id_end": piece_end,
                "state_text": state_text_norm,
                "next_question": next_question,
                "state_token_len": len(TOKEN_RE.findall(state_text_norm)),
                "next_q_token_len": len(TOKEN_RE.findall(next_question)),
                "question_yesno": question_yesno(next_question),
                "question_why": question_why(next_question),
                "question_open_word": question_open_word(next_question),
                "has_named_entity": has_named_entity(next_question),
            }
        )
    return out

def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("window_pairs", type=int, choices=[1, 2])
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    files = sorted([p for p in args.in_dir.rglob("*.jsonl") if p.is_file()])
    if not files:
        LOG.warning("No cleaned jsonl found in %s", args.in_dir)
        return

    all_rows: List[Dict] = []
    for file_piece in files:
        pieces = reading_pieces(file_piece)
        if not pieces:
            continue
        rows = build_cases(pieces, window_pairs=args.window_pairs)
        all_rows.extend(rows)

    out_path = args.out_dir / "cases" / f"cases_w{args.window_pairs}.jsonl"
    write_jsonl(out_path, all_rows)
    LOG.info("Wrote %s (cases=%d)", out_path, len(all_rows))

if __name__ == "__main__":
    main()
