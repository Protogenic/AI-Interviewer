from collections import Counter, defaultdict
from typing import List, Dict

from ai_service.models.build_profile import AnnotatedPhrase, Template
from ai_service.offline_pipeline.templates.split_components import ComponentSeparator
from ai_service.offline_pipeline.categories import Technique, Action, QuestionOpenness, Emotion


class TemplateCreator:
    def __init__(self, min_frequency: int = 2, top_techniques: int = 3) -> None:
        self.min_frequency = min_frequency
        self.separator = ComponentSeparator()
        self.top_techniques = top_techniques

    def _iter_phrase_techniques(self, phrase: AnnotatedPhrase) -> List[Technique]:
        raw = getattr(phrase, "techniques", None)

        if raw is None:
            return []

        return [t for t in raw if t is not None]

    def create(self, phrases: List[AnnotatedPhrase]) -> List[Template]:
        max_replica: Dict[str, int] = {}

        for p in phrases:
            interview_id = p.interview_id
            rid = p.replica_id
            if interview_id not in max_replica:
                max_replica[interview_id] = rid
            else:
                max_replica[interview_id] = max(max_replica[interview_id], rid)

        template_group = defaultdict(list)

        for phrase in phrases:
            if phrase.role != "interviewer":
                continue

            components, template = self.separator.split_into_components(phrase.text)

            interview_id = phrase.interview_id
            max_interview_id = max_replica[interview_id]
            norm_position = (phrase.replica_id / max_interview_id)

            template_group[template].append((phrase, components, norm_position))

        templates: List[Template] = []

        for template, items in template_group.items():
            if len(items) < self.min_frequency:
                continue

            style_counter = Counter(
                (
                    item[0].action.value,
                    item[0].question_openness.value,
                    item[0].emotion.value,
                )
                for item in items
            )

            if style_counter:
                (main_action, main_question_openness, main_emotion), _ = style_counter.most_common(1)[0]
            else:
                main_action = Action.UNCERTAIN.value
                main_question_openness = QuestionOpenness.UNCERTAIN_QUESTION.value
                main_emotion = Emotion.NO_EMOTION.value

            core_items = [
                item for item in items
                if item[0].action.value == main_action
                   and item[0].question_openness.value == main_question_openness
                   and item[0].emotion.value == main_emotion
            ]
            if not core_items:
                core_items = items

            technique_counter = Counter(
                tech.value
                for item in core_items
                for tech in self._iter_phrase_techniques(item[0])
            )

            if technique_counter:
                main_techniques = [t for t, _ in technique_counter.most_common(self.top_techniques)]
            else:
                main_techniques = [Technique.GENERAL.value]

            examples = [item[0].text for item in core_items[:5]]

            norm_positions = [item[2] for item in items]
            avg_position = (sum(norm_positions) / len(norm_positions)) if norm_positions else 0.0

            created_template = Template(
                structure=template,
                frequency=len(items),
                techniques=main_techniques,
                action=main_action,
                question_openness=main_question_openness,
                emotion=main_emotion,
                avg_position=avg_position,
                reactivity=[],
                examples=examples,
            )
            templates.append(created_template)

        templates.sort(key=lambda templ: templ.frequency, reverse=True)
        return templates