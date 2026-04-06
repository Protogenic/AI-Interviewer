import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from ai_service.models.build_profile import Phrase, AnnotatedPhrase, InterviewerProfile
from ai_service.offline_pipeline.parsing.rule_anotator import RuleAnnotator
from ai_service.offline_pipeline.profiling.linguistic_profiler import LinguisticProfiler
from ai_service.offline_pipeline.profiling.reactivity_analyzer import ReactivityAnalyzer
from ai_service.offline_pipeline.templates.create_templates import TemplateCreator


logger = logging.getLogger(__name__)


def load_phrases_from_jsonl(file_path: Path) -> List[Phrase]:
    phrases: List[Phrase] = []

    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            item: Dict[str, Any] = json.loads(line)

            speaker = item.get("speaker", "").strip().lower()
            role = ""
            if speaker == "guest":
                role = "guest"
            elif speaker == "interviewer":
                role = "interviewer"
            else:
                continue

            phrases.append(
                Phrase(
                    role=role,
                    text=item.get("text", "").strip(),
                    replica_id=int(item.get("replica_id", len(phrases)))
                )
            )

    phrases.sort(key=lambda x: x.replica_id)
    return phrases


def phrase_to_csv_row(interviewer_id: str, interview_id: str, phrase: AnnotatedPhrase) -> dict:
    csv_row = {
        "interviewer_id": interviewer_id,
        "interview_id": interview_id,
        "replica_id": phrase.replica_id,
        "role": phrase.role,
        "text": phrase.text,
        "action": phrase.action.value if phrase.action else None,
        "question_openness": phrase.question_openness.value if phrase.question_openness else None,
        "emotion": phrase.emotion.value if phrase.emotion else None,
        "technique": phrase.technique.value if phrase.technique else None,
        "answer_type": phrase.answer_type.value if phrase.answer_type else None,
    }
    return csv_row


def annotate_phrases(phrases: List[Phrase], annotator: RuleAnnotator) -> List[AnnotatedPhrase]:
    annotated_phrases: List[AnnotatedPhrase] = []

    for phrase in phrases:
        if len(phrase.text.split()) > 50:
            continue

        ap = AnnotatedPhrase(
            role=phrase.role,
            text=phrase.text,
            replica_id=phrase.replica_id,
        )

        if phrase.role == "interviewer":
            action = annotator.annotate_action(phrase.text)
            question_openness = annotator.annotate_question_openness(phrase.text)
            emotion = annotator.annotate_emotion(phrase.text)
            technique = annotator.annotate_techniques(phrase.text)

            ap.action = action
            ap.question_openness = question_openness
            ap.emotion = emotion
            ap.technique = technique

        elif phrase.role == "guest":
            answer_type = annotator.annotate_answer_type(phrase.text)
            ap.answer_type = answer_type

        annotated_phrases.append(ap)
    return annotated_phrases

def run_pipeline_for_interviewer(
        interviewer_id: str,
        dir_clean_text: Path,
        annotated_csv_path: Path,
        profile_path: Path,
) -> None:
    annotator = RuleAnnotator()
    profiler = LinguisticProfiler()
    reactivity = ReactivityAnalyzer()
    template_creator = TemplateCreator(min_frequency=2)

    annotated_csv_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    jsonl_files = sorted(dir_clean_text.glob("*.jsonl"))
    if not jsonl_files:
        logger.warning("No .jsonl files found in %s", dir_clean_text)
        return

    logger.info("Found %d jsonl files for interviewer %s", len(jsonl_files), interviewer_id)

    all_annotated_phrases: List[AnnotatedPhrase] = []

    with open(annotated_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "interviewer_id",
                "interview_id",
                "replica_id",
                "role",
                "text",
                "action",
                "question_openness",
                "emotion",
                "technique",
                "answer_type",
            ],
        )
        writer.writeheader()

        for jsonl_file in jsonl_files:
            interview_id = jsonl_file.stem
            phrases = load_phrases_from_jsonl(jsonl_file)

            if not phrases:
                logger.warning("No valid phrases loaded from %s", jsonl_file)
                continue

            annotated_phrases = annotate_phrases(phrases, annotator)
            all_annotated_phrases.extend(annotated_phrases)

            for ap in annotated_phrases:
                writer.writerow(
                    phrase_to_csv_row(
                        interviewer_id=interviewer_id,
                        interview_id=interview_id,
                        phrase=ap
                    )
                )

    if not all_annotated_phrases:
        logger.warning("No annotated phrases produced for interviewer %s", interviewer_id)
        return

    interviewer_texts = [ap.text for ap in all_annotated_phrases if ap.role == "interviewer"]
    linguistic_profile = profiler.build_profile(interviewer_texts)

    reactivity_matrix = reactivity.build_matrix(all_annotated_phrases)
    templates = template_creator.create(all_annotated_phrases)

    characteristic_phrases: List[str] = []
    for template in templates[:10]:
        characteristic_phrases.extend(template.examples[:2])

    profile = InterviewerProfile(
        interviewer_id=interviewer_id,
        linguistic_profile=linguistic_profile,
        reactivity_matrix=reactivity_matrix,
        templates=templates,
        characteristic_phrases=characteristic_phrases[:20],
    )

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

    logger.info("[DONE] Offline pipeline completed for %s", interviewer_id)
    logger.info("Profile saved to: %s", profile_path)
    logger.info("Annotations saved to: %s", annotated_csv_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s"
    )

    interviewer_id = "dud"
    run_pipeline_for_interviewer(
        interviewer_id=interviewer_id,
        dir_clean_text=Path(f"ai_service/data/cleaned/{interviewer_id}"),
        annotated_csv_path=Path(f"ai_service/data/annotated/dud/auto_annotations.csv"),
        profile_path = Path(f"ai_service/data/profiles/{interviewer_id}_profile.json"),
    )






