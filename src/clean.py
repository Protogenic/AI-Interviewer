"""
Clean raw transcripts and convert them into a normalized JSONL format.

This script transforms raw transcript `.txt` files into a structured dataset for
chunking. Its goal is to standardize interview transcripts, while removing
non-dialogue noise such as stage directions and advertisement blocks.

1) Drops empty lines and standalone bracketed/parenthetical stage directions, intro, music, jingle,
advertisement-like content.
2) Parses speaker markers in transcripts.
3) Turn aggregation:
   - Consecutive lines belonging to the same speaker are merged into a single turn.
   - A new speaker marker flushes the previous buffer into a JSONL record.
   The business rationale: retrieval and modeling operate on coherent speaker blocks, not raw lines.

Input
-----
A directory of `.txt` transcript files.

Output
------
For each input transcript it writes a `.jsonl` file.
- interview_id: stable ID derived from file name
- source_file: original path
- turn_id: incrementing integer index within interview
- speaker: normalized role (e.g., "interviewer" or "guest")
- speaker_raw: raw speaker label extracted from transcript
- text: cleaned text

Command-line interface
----------------------
Positional arguments:

input_dir : str
    Root directory containing raw `.txt` transcripts (searched recursively).
out_dir : str
    Output directory for cleaned `.jsonl` files.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


LOG = logging.getLogger("clean")

SPEAKER_INLINE_RE = re.compile(r"^\s*([^:]{1,80})\s*:\s*(.+?)\s*$")
SPEAKER_ONLY_RE = re.compile(r"^\s*([^:]{1,80})\s*:\s*$")
BRACKET_SPEAKER_RE = re.compile(r"^\s*\[([^\]]{1,80})\]\s*$")

SQUARE_BRACKET_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$")
PAREN_LINE_RE = re.compile(r"^\s*\([^)]*\)\s*$")

VOICE_LABEL_RE = re.compile(r"^\s*(голос|закадровый|диктор)\b", re.IGNORECASE)

AD_LINE_RE = re.compile(
    r"(промокод|скидк|спонсор|реклама|подписывай|ссылка в описан|"
    r"партн[её]р|купон|магазин|заказывай|доставка|регистрац)",
    re.IGNORECASE,
)

JINGLE_LINE_RE = re.compile(r"(джингл|музыка|заставка|интро|аутро)", re.IGNORECASE)


def normalize_spaces(s: str) -> str:
    """
    Removes unnecessary spaces and invisible characters so that nothing interferes with further processing.
    """
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    return s.strip()


def clearing_lines(line: str) -> bool:
    """
    Removes ads, square brackets, and music. The set of markers is based on the transcripts of the interview.
    """
    if not line.strip():
        return True
    if SQUARE_BRACKET_LINE_RE.match(line) or PAREN_LINE_RE.match(line):
        return True
    if JINGLE_LINE_RE.search(line):
        return True
    if AD_LINE_RE.search(line):
        return True
    return False


def unicode_check(path: Path) -> str:
    """
    Handles the error with Unicode
    """
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def role_from_label(label: str) -> Optional[str]:
    """
    Extracting roles logically based on a transcript.
    """
    low = label.lower()
    if "интервьюер" in low or "ведущ" in low:
        return "interviewer"
    if "гость" in low:
        return "guest"
    if VOICE_LABEL_RE.search(low):
        return "drop"
    return None


@dataclass(frozen=True)
class LinePhrase:
    interview_id: str
    source_file: str
    replica_id: int
    speaker: str
    speaker_raw: str
    text: str


class InterviewCleaner:
    """
    Clearing the interview of garbage and making it look like an interviewer and guest
    """

    def __init__(self) -> None:
        self._label_to_role: Dict[str, Optional[str]] = {}
        self._seen_order: List[str] = []

    def map_label(self, label: str) -> Optional[str]:
        if not label:
            return None
        if label in self._label_to_role:
            return self._label_to_role[label]

        extracted_role = role_from_label(label)
        if extracted_role == "drop":
            self._label_to_role[label] = None
            return None
        if extracted_role in ("interviewer", "guest"):
            self._label_to_role[label] = extracted_role
            if label not in self._seen_order:
                self._seen_order.append(label)
            return extracted_role
        if label not in self._seen_order:
            self._seen_order.append(label)

        role: Optional[str]
        if len(self._seen_order) == 1:
            role = "interviewer"
        elif len(self._seen_order) == 2:
            role = "guest"
        else:
            role = None

        self._label_to_role[label] = role
        return role


def speaker_block_generator(interview_id: str, source_file: str, text: str) -> Iterator[LinePhrase]:
    separation_roles = InterviewCleaner()

    current_label = None
    current_role = None
    buf_current_speaker = []
    replica_id = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if clearing_lines(line):
            continue

        match_line = BRACKET_SPEAKER_RE.match(line)
        if match_line:
            if buf_current_speaker and current_label and current_role:
                merged_buf_cur_speaker = normalize_spaces(" ".join(buf_current_speaker))
                buf_current_speaker = []
                if merged_buf_cur_speaker:
                    yield LinePhrase(
                        interview_id=interview_id,
                        source_file=source_file,
                        replica_id=replica_id,
                        speaker=current_role,
                        speaker_raw=current_label,
                        text=merged_buf_cur_speaker,
                    )
                    replica_id += 1
            else:
                buf_current_speaker = []

            current_label = normalize_spaces(match_line.group(1))
            current_role = separation_roles.map_label(current_label)
            continue

        match_line = SPEAKER_INLINE_RE.match(line)
        if match_line:
            if buf_current_speaker and current_label and current_role:
                merged_buf_cur_speaker = normalize_spaces(" ".join(buf_current_speaker))
                buf_current_speaker = []
                if merged_buf_cur_speaker:
                    yield LinePhrase(
                        interview_id=interview_id,
                        source_file=source_file,
                        replica_id=replica_id,
                        speaker=current_role,
                        speaker_raw=current_label,
                        text=merged_buf_cur_speaker,
                    )
                    replica_id += 1
            else:
                buf_current_speaker = []

            current_label = normalize_spaces(match_line.group(1))
            current_role = separation_roles.map_label(current_label)

            payload = normalize_spaces(match_line.group(2))
            if payload and current_role:
                buf_current_speaker.append(payload)
            continue

        match_line = SPEAKER_ONLY_RE.match(line)
        if match_line:
            if buf_current_speaker and current_label and current_role:
                merged_buf_cur_speaker = normalize_spaces(" ".join(buf_current_speaker))
                buf_current_speaker = []
                if merged_buf_cur_speaker:
                    yield LinePhrase(
                        interview_id=interview_id,
                        source_file=source_file,
                        replica_id=replica_id,
                        speaker=current_role,
                        speaker_raw=current_label,
                        text=merged_buf_cur_speaker,
                    )
                    replica_id += 1
            else:
                buf_current_speaker = []

            current_label = normalize_spaces(match_line.group(1))
            current_role = separation_roles.map_label(current_label)
            continue

        if current_role:
            buf_current_speaker.append(line)

    if buf_current_speaker and current_label and current_role:
        merged_buf_cur_speaker = normalize_spaces(" ".join(buf_current_speaker))
        buf_current_speaker = []
        if merged_buf_cur_speaker:
            yield LinePhrase(
                interview_id=interview_id,
                source_file=source_file,
                replica_id=replica_id,
                speaker=current_role,
                speaker_raw=current_label,
                text=merged_buf_cur_speaker,
            )
            replica_id += 1
    else:
        buf_current_speaker = []


def write_jsonl(path: Path, speaker_blocks: Iterable[LinePhrase]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    number_speaker_blocks = 0
    with path.open("w", encoding="utf-8") as f:
        for phrase in speaker_blocks:
            f.write(
                json.dumps(
                    {
                        "interview_id": phrase.interview_id,
                        "source_file": phrase.source_file,
                        "replica_id": phrase.replica_id,
                        "speaker": phrase.speaker,
                        "speaker_raw": phrase.speaker_raw,
                        "text": phrase.text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            number_speaker_blocks += 1
    return number_speaker_blocks


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean transcripts to JSONL.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    in_dir = args.input_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted([path_to_file for path_to_file in in_dir.rglob("*.txt") if path_to_file.is_file()])
    if not txt_files:
        LOG.warning("No .txt files found in %s", in_dir)
        return

    LOG.info("Found %d txt files in %s", len(txt_files), in_dir)

    total_speaker_blocks = 0
    for fp in txt_files:
        interview_id = fp.stem
        raw = unicode_check(fp)
        speaker_blocks = list(speaker_block_generator(interview_id, fp.name, raw))
        if not speaker_blocks:
            LOG.warning("Speaker blocks are missing after cleaning: %s", fp)
            continue

        out_path = out_dir / f"{interview_id}.jsonl"
        number_speaker_blocks = write_jsonl(out_path, speaker_blocks)
        total_speaker_blocks += number_speaker_blocks

    LOG.info("Done. Total speaker blocks written: %d", total_speaker_blocks)


if __name__ == "__main__":
    main()
