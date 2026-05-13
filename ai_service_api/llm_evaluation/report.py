import csv
import statistics
from pathlib import Path

from llm_evaluation.config import RESULTS_DIR


def _safe_mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(statistics.mean(clean), 3) if clean else None


def _safe_std(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(statistics.stdev(clean), 3) if len(clean) >= 2 else None


def aggregate(results: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for r in results:
        grouped.setdefault(r["provider"], []).append(r)

    summary: dict[str, dict] = {}
    for provider, rows in grouped.items():
        n = len(rows)
        m_list = [r["metrics"] for r in rows]
        j_list = [r.get("judge") for r in rows if r.get("judge")]

        def rate(key: str) -> str:
            vals = [m.get(key, False) for m in m_list]
            pct = 100 * sum(vals) / n if n else 0
            return f"{pct:.0f}%"

        latencies = [m["latency_s"] for m in m_list if m.get("latency_s") is not None]
        lat_mean = _safe_mean(latencies)
        lat_std = _safe_std(latencies)

        maes = [m["word_count_mae"] for m in m_list if m.get("word_count_mae") is not None]
        mae_mean = _safe_mean(maes)

        total_cost = sum(m.get("cost_usd", 0) for m in m_list)

        judge_style = _safe_mean([j["style"] for j in j_list if j and j.get("style") is not None])
        judge_lang = _safe_mean([j["language"] for j in j_list if j and j.get("language") is not None])
        judge_emotion = _safe_mean([j["emotion"] for j in j_list if j and j.get("emotion") is not None])
        judge_overall = _safe_mean([j["overall"] for j in j_list if j and j.get("overall") is not None])

        style_cosines = [r["style_cosine"] for r in rows if r.get("style_cosine") is not None]
        style_cosine_mean = _safe_mean(style_cosines)

        summary[provider] = {
            "n": n,
            "json_valid_%": rate("json_valid"),
            "structure_ok_%": rate("roles_correct"),
            "punct_ok_%": rate("no_forbidden_punct"),
            "word_mae": mae_mean,
            "latency_mean_s": lat_mean,
            "latency_std_s": lat_std,
            "judge_style": judge_style,
            "judge_language": judge_lang,
            "judge_emotion": judge_emotion,
            "judge_overall": judge_overall,
            "style_cosine": style_cosine_mean,
            "total_cost_usd": round(total_cost, 4),
        }
    return summary


def _cell(value) -> str:
    if value is None:
        return "—"
    return str(value)


def to_markdown(summary: dict[str, dict]) -> str:
    headers = [
        "Провайдер / модель",
        "JSON OK",
        "Структура OK",
        "Пунктуация OK",
        "Word MAE",
        "Latency (s)",
        "Style cos",
        "Judge: стиль",
        "Judge: язык",
        "Judge: эмоция",
        "Judge: overall",
        "Стоимость (USD)",
    ]

    rows = []
    for provider, s in summary.items():
        lat = (
            f"{s['latency_mean_s']}±{s['latency_std_s']}"
            if s["latency_std_s"] is not None
            else _cell(s["latency_mean_s"])
        )
        rows.append([
            provider,
            s["json_valid_%"],
            s["structure_ok_%"],
            s["punct_ok_%"],
            _cell(s["word_mae"]),
            lat,
            _cell(s["style_cosine"]),
            _cell(s["judge_style"]),
            _cell(s["judge_language"]),
            _cell(s["judge_emotion"]),
            _cell(s["judge_overall"]),
            str(s["total_cost_usd"]),
        ])

    col_widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(headers))
    ]

    def fmt_row(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"

    lines = [fmt_row(headers), sep] + [fmt_row(r) for r in rows]
    return "\n".join(lines)


def to_summary_csv(summary: dict[str, dict]) -> str:
    import io
    buf = io.StringIO()
    fieldnames = [
        "provider", "n", "json_valid_%", "structure_ok_%", "punct_ok_%",
        "word_mae", "latency_mean_s", "latency_std_s",
        "style_cosine",
        "judge_style", "judge_language", "judge_emotion", "judge_overall",
        "total_cost_usd",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for provider, s in summary.items():
        writer.writerow({"provider": provider, **s})
    return buf.getvalue()


def to_per_case_csv(results: list[dict]) -> str:
    import io
    buf = io.StringIO()
    fieldnames = [
        "provider", "case_id", "interviewer", "emotion", "structure",
        "target_words", "json_valid", "has_parts_key", "parts_count_correct",
        "roles_correct", "word_count_mae", "no_forbidden_punct",
        "latency_s", "input_tokens", "output_tokens", "cost_usd",
        "style_cosine",
        "judge_style", "judge_language", "judge_emotion", "judge_overall",
        "judge_mean", "judge_comment",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in results:
        m = r.get("metrics", {})
        j = r.get("judge") or {}
        writer.writerow({
            "provider": r.get("provider"),
            "case_id": r.get("case_id"),
            "interviewer": r.get("interviewer"),
            "emotion": r.get("emotion"),
            "structure": r.get("structure"),
            "target_words": r.get("target_words"),
            **{k: m.get(k) for k in [
                "json_valid", "has_parts_key", "parts_count_correct",
                "roles_correct", "word_count_mae", "no_forbidden_punct",
                "latency_s", "input_tokens", "output_tokens", "cost_usd",
            ]},
            "style_cosine": r.get("style_cosine"),
            "judge_style": j.get("style"),
            "judge_language": j.get("language"),
            "judge_emotion": j.get("emotion"),
            "judge_overall": j.get("overall"),
            "judge_mean": j.get("mean"),
            "judge_comment": j.get("comment"),
        })
    return buf.getvalue()


def save_reports(results: list[dict]) -> None:
    out_dir = Path(RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = aggregate(results)

    md = to_markdown(summary)
    (out_dir / "summary_table.md").write_text(md, encoding="utf-8")

    csv_summary = to_summary_csv(summary)
    (out_dir / "summary_table.csv").write_text(csv_summary, encoding="utf-8")

    csv_per_case = to_per_case_csv(results)
    (out_dir / "per_case.csv").write_text(csv_per_case, encoding="utf-8")

    print("\n" + "=" * 70)
    print(md)
    print("=" * 70)
    print(f"\nReports saved to {out_dir.resolve()}/")
