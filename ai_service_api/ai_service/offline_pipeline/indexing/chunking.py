from typing import Any, Iterable, Optional

from ai_service.models.rag import RagChunk


class Chunking:
    def build_qa_chunks(self, replicas: list[dict[str, Any]]) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        i = 0
        seen = set()

        while i < len(replicas):
            r: dict[str, Any] = replicas[i]
            if r.get("speaker") == "interviewer":
                q = (r.get("text") or "").strip()
                if not q:
                    i += 1
                    continue

                answer_text: Optional[str] = None
                j = i + 1
                while j < len(replicas):
                    r2 = replicas[j]
                    t2 = (r2.get("text") or "").strip()
                    if t2 and r2.get("speaker") != "interviewer":
                        answer_text = t2
                        break
                    j += 1

                passage = f"Вопрос интервьюера: {q}"
                if answer_text:
                    passage += f"\nОтвет гостя: {answer_text}"

                key = (r.get("interview_id"), r.get("source_file"), int(r["replica_id"]))
                if key in seen:
                    print("DUPLICATE KEY:", key, "record:", r)
                    i += 1
                    continue
                seen.add(key)

                chunks.append(
                    RagChunk(
                        interview_id=str(r.get("interview_id", "")),
                        source_file=str(r.get("source_file", "")),
                        question_replica_id=int(r.get("replica_id", -1)),
                        question_text=q,
                        answer_text=answer_text,
                        passage_text=passage,
                    )
                )
            i += 1
        return chunks

    def batched(self, items: list[Any], batch_size: int) -> Iterable[list[Any]]:
        for start in range(0, len(items), batch_size):
            yield items[start: start + batch_size]