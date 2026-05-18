import asyncio
import json
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from llm_evaluation.test_cases import TestCase

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "Ты - эксперт по оценке качества реплик AI-интервьюера. "
    "Тебе будут давать реплику, сгенерированную языковой моделью, "
    "и контекст (кто интервьюер, какая эмоция требовалась, последнее слово гостя). "
    "Оцени реплику строго по четырём критериям от 1 до 5. "
    "Отвечай ТОЛЬКО валидным JSON без пояснений."
)

_JUDGE_USER_TEMPLATE = """\
ИНТЕРВЬЮЕР: {interviewer_desc}
ТРЕБУЕМАЯ ЭМОЦИЯ: {emotion}
ПОСЛЕДНЯЯ РЕПЛИКА ГОСТЯ: {last_answer}

СГЕНЕРИРОВАННАЯ РЕПЛИКА:
{reply}

Оцени реплику по шкале 1–5 по каждому критерию:
1. style    - насколько реплика соответствует стилю интервьюера (лексика, ритм, интонация)
2. language - насколько текст звучит по-русски естественно и грамматически правильно
3. emotion  - насколько реплика соответствует заданной эмоциональной окраске
4. overall  - общее впечатление от реплики как реакции интервьюера

Шкала: 1=очень плохо, 2=плохо, 3=удовлетворительно, 4=хорошо, 5=отлично

Верни строго JSON:
{{"style": <int>, "language": <int>, "emotion": <int>, "overall": <int>, "comment": "<1 sentence>"}}
"""

_INTERVIEWER_DESCS = {
    "dud": "Юрий Дудь - динамичный, прямолинейный, разговорный стиль на «ты»",
    "sobchak": "Ксения Собчак - провокационный, острый, эмоционально заряженный стиль на «ты»",
    "pozner": "Владимир Познер - спокойный, аналитический, интеллигентный стиль на «вы»",
}

_EMOTION_DESCS = {
    "neutral": "нейтральный тон",
    "challenge": "провокационная, испытывающая",
    "empathy": "сочувствие, эмпатия",
    "commentary": "короткая реакция одобрения",
}


@dataclass
class JudgeScores:
    style: float | None = None
    language: float | None = None
    emotion: float | None = None
    overall: float | None = None
    comment: str = ""
    judge_error: str = ""

    @property
    def mean(self) -> float | None:
        scores = [s for s in (self.style, self.language, self.emotion, self.overall) if s is not None]
        return round(sum(scores) / len(scores), 2) if scores else None


def scores_to_dict(s: JudgeScores) -> dict:
    return {
        "style": s.style,
        "language": s.language,
        "emotion": s.emotion,
        "overall": s.overall,
        "mean": s.mean,
        "comment": s.comment,
        "judge_error": s.judge_error,
    }


class LLMJudge:
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def evaluate(
        self,
        test_case: TestCase,
        reply: str,
        last_answer: str = "",
    ) -> JudgeScores:
        interviewer_desc = _INTERVIEWER_DESCS.get(test_case.interviewer, test_case.interviewer)
        emotion_desc = _EMOTION_DESCS.get(test_case.emotion, test_case.emotion)

        user_msg = _JUDGE_USER_TEMPLATE.format(
            interviewer_desc=interviewer_desc,
            emotion=emotion_desc,
            last_answer=last_answer or "(не указано)",
            reply=reply or "(пустой ответ)",
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _JUDGE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            return JudgeScores(
                style=float(data.get("style", 0)),
                language=float(data.get("language", 0)),
                emotion=float(data.get("emotion", 0)),
                overall=float(data.get("overall", 0)),
                comment=str(data.get("comment", "")),
            )
        except Exception as e:
            logger.warning("Judge failed for case %s: %s", test_case.id, e)
            return JudgeScores(judge_error=str(e))

    async def evaluate_batch(
        self,
        items: list[tuple[TestCase, str, str]],
        concurrency: int = 5,
    ) -> list[JudgeScores]:
        sem = asyncio.Semaphore(concurrency)

        async def _one(tc: TestCase, reply: str, last_answer: str) -> JudgeScores:
            async with sem:
                return await self.evaluate(tc, reply, last_answer)

        return await asyncio.gather(*[_one(tc, r, la) for tc, r, la in items])
