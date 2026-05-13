import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_CORPUS_BASE = Path("ai_service/data/cleaned_oi")

_INTERVIEWER_DIRS = {
    "dud": _CORPUS_BASE / "dud" / "only_interviewer",
    "sobchak": _CORPUS_BASE / "sobchak" / "only_interviewer",
    "pozner": _CORPUS_BASE / "pozner" / "only_interviewer",
}

_DEFAULT_ST_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

_FORBIDDEN_RE = re.compile(r"['\"{}]")


def extract_content_text(raw_response: str) -> str:
    text = (raw_response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text).rstrip("`").strip()
    text_for_parse = text.replace("'", '"')
    try:
        data = json.loads(text_for_parse)
        parts = data.get("parts") if isinstance(data, dict) else None
        if isinstance(parts, list):
            contents = [
                p.get("content", "") for p in parts
                if isinstance(p, dict) and p.get("content")
            ]
            return " ".join(contents).strip()
    except (json.JSONDecodeError, AttributeError):
        pass
    return text.strip()


class StyleScorer:
    def __init__(
        self,
        st_model: str = _DEFAULT_ST_MODEL,
        device: str = "cpu",
    ) -> None:
        self._st_model_name = st_model
        self._device = device
        self._model = None
        self._centroids: dict = {}

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "Install sentence-transformers: pip install sentence-transformers"
            ) from e
        logger.info("Loading SentenceTransformer: %s …", self._st_model_name)
        self._model = SentenceTransformer(self._st_model_name, device=self._device)

    def _load_centroid(self, interviewer: str):
        if interviewer in self._centroids:
            return self._centroids[interviewer]

        corpus_dir = _INTERVIEWER_DIRS.get(interviewer)
        if corpus_dir is None or not corpus_dir.exists():
            logger.warning(
                "Style corpus not found for '%s' at %s — style_cosine will be None.",
                interviewer, corpus_dir,
            )
            self._centroids[interviewer] = None
            return None

        texts = []
        for jsonl_file in sorted(corpus_dir.glob("*.jsonl")):
            with jsonl_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        t = (d.get("text") or "").strip()
                        if t:
                            texts.append(t)
                    except json.JSONDecodeError:
                        continue

        if not texts:
            logger.warning("No texts found in corpus for '%s'.", interviewer)
            self._centroids[interviewer] = None
            return None

        import torch

        self._load_model()
        logger.info(
            "Building style centroid for '%s' from %d phrases …",
            interviewer, len(texts),
        )
        emb = self._model.encode(
            texts,
            batch_size=64,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        centroid = emb.mean(dim=0, keepdim=True)
        centroid = torch.nn.functional.normalize(centroid, p=2, dim=1)
        self._centroids[interviewer] = centroid
        return centroid

    def score(self, text: str, interviewer: str) -> float | None:
        if not text.strip():
            return None

        centroid = self._load_centroid(interviewer)
        if centroid is None:
            return None

        self._load_model()
        emb = self._model.encode(
            [text],
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        sim = (emb * centroid).sum(dim=1)
        return round(float(sim.item()), 4)

    def score_batch(
        self,
        texts: list[str],
        interviewers: list[str],
    ) -> list[float | None]:
        results: list[float | None] = [None] * len(texts)

        groups: dict[str, list[int]] = {}
        for i, (text, iw) in enumerate(zip(texts, interviewers)):
            if text.strip():
                groups.setdefault(iw, []).append(i)

        for iw, indices in groups.items():
            centroid = self._load_centroid(iw)
            if centroid is None:
                continue

            self._load_model()
            batch_texts = [texts[i] for i in indices]
            emb = self._model.encode(
                batch_texts,
                batch_size=64,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            sims = (emb * centroid).sum(dim=1).detach().cpu().tolist()
            for idx, sim in zip(indices, sims):
                results[idx] = round(float(sim), 4)

        return results


def add_style_scores(results: list[dict], scorer: StyleScorer | None = None) -> list[dict]:
    if scorer is None:
        scorer = StyleScorer()

    texts = []
    interviewers = []
    for r in results:
        raw = r.get("metrics", {}).get("raw_response", "")
        texts.append(extract_content_text(raw))
        interviewers.append(r.get("interviewer", ""))

    scores = scorer.score_batch(texts, interviewers)
    for r, s in zip(results, scores):
        r["style_cosine"] = s

    return results
