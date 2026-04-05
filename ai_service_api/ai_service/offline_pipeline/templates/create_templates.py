from collections import Counter, defaultdict
from typing import List

from ai_service.models.build_profile import AnnotatedPhrase, Template
from ai_service.offline_pipeline.templates.split_components import ComponentSeparator
from ai_service.offline_pipeline.categories import Technique, Action, QuestionOpenness, Emotion


class TemplateCreator:
    def __init__(self, min_frequency: int = 2) -> None:
        self.min_frequency = min_frequency
        self.separator = ComponentSeparator()

    def create(self, phrases: List[AnnotatedPhrase]) -> List[Template]:
        template_group = defaultdict(list)

        for phrase in phrases:
            if phrase.role != "interviewer":
                continue

            components, template = self.separator.split_into_components(phrase.text)
            template_group[template].append((phrase, components))

        templates: List[Template] = []

        for template, items in template_group.items():
            if len(items) < self.min_frequency:
                continue

            technique_counter = Counter(
                item[0].technique.value for item in items
            )
            if technique_counter:
                main_technique = technique_counter.most_common(1)[0][0]
            else:
                main_technique = Technique.GENERAL.value

            action_counter = Counter(
                item[0].action.value for item in items
            )
            if action_counter:
                main_action = action_counter.most_common(1)[0][0]
            else:
                main_action = Action.UNCERTAIN.value

            question_openness_counter = Counter(
                item[0].question_openness.value for item in items
            )
            if question_openness_counter:
                main_question_openness = question_openness_counter.most_common(1)[0][0]
            else:
                main_question_openness = QuestionOpenness.UNCERTAIN_QUESTION.value

            emotion_counter = Counter(
                item[0].emotion.value for item in items
            )
            if emotion_counter:
                main_emotion = emotion_counter.most_common(1)[0][0]
            else:
                main_emotion = Emotion.NO_EMOTION.value

            examples = [item[0].text for item in items[:5]]
            positions = [item[0].replica_id for item in items]
            if positions:
                avg_position = sum(positions) / len(positions)
            else:
                avg_position = 0.0

            created_template = Template(
                structure=template,
                frequency=len(items),
                technique=main_technique,
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