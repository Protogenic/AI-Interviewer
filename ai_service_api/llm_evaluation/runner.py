import asyncio
import json
import logging
import time
from pathlib import Path

from openai import AsyncOpenAI, BadRequestError

from llm_evaluation.config import (
    ProviderConfig,
    EVAL_TEMPERATURE,
    EVAL_MAX_TOKENS,
    RESULTS_DIR,
)
from llm_evaluation.metrics import compute, metrics_to_dict
from llm_evaluation.test_cases import TestCase, TEST_CASES

logger = logging.getLogger(__name__)


async def _call_provider(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    use_json_mode: bool,
) -> tuple[str, int, int]:
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": EVAL_TEMPERATURE,
        "max_tokens": EVAL_MAX_TOKENS,
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = await client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if use_json_mode and "response_format" in str(e).lower():
            kwargs.pop("response_format", None)
            resp = await client.chat.completions.create(**kwargs)
        else:
            raise

    content = resp.choices[0].message.content or ""
    usage = resp.usage
    in_tok = usage.prompt_tokens if usage else 0
    out_tok = usage.completion_tokens if usage else 0
    return content, in_tok, out_tok


async def run_provider(
    provider: ProviderConfig,
    test_cases: list[TestCase] | None = None,
) -> list[dict]:
    if not provider.api_key:
        logger.warning("Skipping %s — API key not set.", provider.label)
        return []

    cases = test_cases or TEST_CASES

    client_kwargs: dict = {"api_key": provider.api_key}
    if provider.base_url:
        client_kwargs["base_url"] = provider.base_url

    client = AsyncOpenAI(**client_kwargs)

    results = []
    for tc in cases:
        if provider.request_delay > 0:
            logger.debug("[%s] Waiting %.0fs (rate-limit delay) …", provider.label, provider.request_delay)
            await asyncio.sleep(provider.request_delay)
        logger.info("[%s] Running case %s …", provider.label, tc.id)
        t0 = time.perf_counter()
        try:
            raw, in_tok, out_tok = await _call_provider(
                client,
                provider.model,
                tc.system_prompt,
                tc.user_prompt,
                provider.use_json_mode,
            )
        except Exception as e:
            logger.error("[%s] Case %s FAILED: %s", provider.label, tc.id, e)
            raw, in_tok, out_tok = "", 0, 0
        latency = time.perf_counter() - t0

        obj = compute(
            raw_response=raw,
            test_case=tc,
            latency_s=latency,
            input_tokens=in_tok,
            output_tokens=out_tok,
            price_input=provider.price_input,
            price_output=provider.price_output,
        )

        results.append({
            "provider": provider.label,
            "case_id": tc.id,
            "interviewer": tc.interviewer,
            "emotion": tc.emotion,
            "structure": tc.structure,
            "target_words": tc.target_words,
            "metrics": metrics_to_dict(obj),
            "last_answer": _extract_last_answer(tc.user_prompt),
        })

    return results


def _extract_last_answer(user_prompt: str) -> str:
    for line in user_prompt.splitlines():
        if line.startswith("# ПОСЛЕДНЯЯ РЕПЛИКА ГОСТЯ:"):
            return line.split(":", 1)[-1].strip()
    return ""


async def run_all_providers(
    providers: list[ProviderConfig],
    test_cases: list[TestCase] | None = None,
    concurrency: int = 1,
) -> list[dict]:
    all_results: list[dict] = []

    if concurrency == 1:
        for p in providers:
            results = await run_provider(p, test_cases)
            all_results.extend(results)
    else:
        sem = asyncio.Semaphore(concurrency)

        async def _bounded(p: ProviderConfig) -> list[dict]:
            async with sem:
                return await run_provider(p, test_cases)

        batches = await asyncio.gather(*[_bounded(p) for p in providers])
        for batch in batches:
            all_results.extend(batch)

    return all_results


def save_raw_results(results: list[dict], filename: str = "raw_results.json") -> Path:
    out_dir = Path(RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Raw results saved → %s", path)
    return path


def load_raw_results(filename: str = "raw_results.json") -> list[dict]:
    path = Path(RESULTS_DIR) / filename
    return json.loads(path.read_text(encoding="utf-8"))
