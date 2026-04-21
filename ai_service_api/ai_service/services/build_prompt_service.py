from typing import List, Tuple, Optional
import random

from ai_service.models.generation import GenerationRequest, BuildPromptResult, InterviewPart
from ai_service.models.build_profile import InterviewerProfile, Template
from ai_service.models.rag import RagExample
from ai_service.offline_pipeline.profiling.markers import MARKERS


def _sample_marker(
    density: Optional[float],
    category: str,
    scale: float = 60.0,
) -> Tuple[bool, str]:
    rng = random.Random()
    if density is None or density <= 0:
        return False, ""

    probability = min(1.0, density * scale)
    use = rng.random() < probability
    if not use:
        return False, ""

    meta = MARKERS[category]
    instruction = (
        f"Используй в этой реплике ровно один маркер {meta['label']} "
        f"из списка: {', '.join(meta['examples'])}. "
        f"Вставь его естественно в любое место внутри фразы."
    )
    return True, instruction


class BuildPromptService:
    def __init__(self, max_history: int = 5) -> None:
        self.max_history = max_history


    def profile_to_instruction(self, profile: InterviewerProfile) -> List[str]:
        ling_profile = profile.linguistic_profile
        instructions: List[str] = []

        avg_len = getattr(ling_profile, "avg_question_length", None)
        if avg_len is not None:
            if avg_len < 10:
                instructions.append(
                    "Длина: реплика должна быть короткой и лаконичной (до 10 слов)."
                )
            elif avg_len > 20:
                instructions.append(
                    "Длина: реплика развёрнутая, многосоставная (более 20 слов)."
                )
            else:
                instructions.append(
                    f"Длина: реплика средней длины (~{int(avg_len)} слов)."
                )

        multi_sentence_ratio = getattr(ling_profile, "multi_sentence_ratio", None)
        if multi_sentence_ratio is not None and multi_sentence_ratio > 0.5:
            instructions.append(
                "Реплика может содержать несколько предложений подряд."
            )

        density_map = {
            "empathy": getattr(ling_profile, "empathy_density", None),
            "hedging": getattr(ling_profile, "hedging_density", None),
            "pressure": getattr(ling_profile, "pressure_density", None),
            "filler": getattr(ling_profile, "filler_density", None),
            "formal": getattr(ling_profile, "formal_density", None),
            "provocation": getattr(ling_profile, "provocation_density", None),
        }
        for category, density in density_map.items():
            _, line = _sample_marker(density, category)
            if line:
                instructions.append(line)

        characteristic_phrases = getattr(profile, "characteristic_phrases", []) or []
        if characteristic_phrases:
            phrases = " | ".join(characteristic_phrases[:3])
            instructions.append(
               f"Характерные фразы интервьюера (НЕ копируй их), "
                f": {phrases}"
            )

        return instructions


    def build_prompt(
            self,
            input_data: GenerationRequest,
            profile: InterviewerProfile,
            template: Template,
            rag_examples: list[RagExample]
    ) -> BuildPromptResult:
        style_instructions = self.profile_to_instruction(profile)

        structure_block = self._build_structure_block(template)
        style_block = self._build_style_block(style_instructions)
        context_block = self._build_context_block(input_data.full_interview_history, input_data.last_answer)
        constraints_block = self._build_output_constraints(template)
        examples_block = self._build_examples_block(rag_examples)

        prompt = "\n\n".join([
            "Ты генерируешь следующее высказывание интервьюера для диалога с пользователем "
            "в стиле конкретного интервьюера.",
            f"имя пользователя: {input_data.user_name}",
            f"информация о пользователе: {input_data.user_info}",
            structure_block,
            style_block,
            context_block,
            examples_block,
            constraints_block,
        ])

        result = BuildPromptResult(
            prompt= prompt,
            style_instruction=style_instructions,
        )
        print(prompt)
        return result

    @staticmethod
    def _build_structure_block(template: Template) -> str:
        structure = getattr(template, "structure", None)
        action = getattr(template, "action", None)
        question_openness = getattr(template, "question_openness", None)
        emotion = getattr(template, "emotion", None)
        techniques = getattr(template, "techniques", None)
        examples = getattr(template, "examples", None)

        lines_block = ["СТРУКТУРА РЕПЛИКИ:"]

        if structure:
            lines_block.append(
                f"- Реплика состоит РОВНО из {len(structure.split("+"))} частей в порядке: {structure}."
            )
            lines_block.append(
                "- Каждая часть - ровно одно предложение. Не сливай части и не пропускай их."
            )
            lines_block.append("- Значения ролей:")
            if "question" in structure:
                lines_block.append("-- question - Прямая вопросительная конструкция, нацеленная на получение конкретных фактов, имен, "
                               "дат или уточнение обстоятельств события, заканчивается знаком вопроса.")
            if "acknowledgment" in structure:
                lines_block.append("-- acknowledgment - Минимальная реакция, подтверждающая, "
                               "что интервьюер слушает гостя и понимает его. ")
            if "bridge" in structure:
                lines_block.append("-- bridge - связующая фраза для навигации: смена темы, возврат "
                               "к недосказанному или обозначение структуры разговора.")
            if "paraphrase" in structure:
                lines_block.append("-- paraphrase - сжатый пересказ слов собеседника или подведение итога сказанному, "
                               "чтобы подтвердить правильность понимания сути.")
            if "empathy" in structure:
                lines_block.append("-- empathy - демонстрация эмоциональной связи: выражение сочувствия, "
                               "удивления, поддержки или уместного сомнения в словах гостя.")
            if "request" in structure:
                lines_block.append("-- request - призыв к активному действию: просьба раскрыть тему подробнее, "
                               "привести живой пример, описать свои чувства или пояснить позицию.")
            if "text" in structure:
                lines_block.append("-- text - информационное наполнение реплики: изложение фактов, вводных данных "
                               "или личного мнения интервьюера, создающее фон для вопроса.")

        if action is not None:
            lines_block.append(f"- Основное действие фразы: {action}")

        if question_openness is not None:
            lines_block.append(f"- Тип фразы по открытости вопроса: {question_openness}")

        if emotion is not None:
            lines_block.append(f"- Эмоциональная окраска: {emotion}")

        if techniques is not None:
            lines_block.append(f"- Используемые техники: {', '.join(techniques)}")

        #if examples:
        #    lines_block.append("Примеры реплик с такой же структурой: ")
        #    for example in examples:
        #        lines_block.append(f" - {example}")

        structure_block = "\n".join(lines_block)
        return structure_block

    @staticmethod
    def _build_style_block(style_instructions: List[str]) -> str:
        if not style_instructions:
            return "ИНСТРУКЦИИ СТИЛЯ:\n- Нейтральный стиль без выраженных маркеров."
        lines_block = ["ИНСТРУКЦИЯ СТИЛЯ:"]
        for instruction in style_instructions:
            lines_block.append(f"- {instruction}")
        style_block = "\n".join(lines_block)
        return style_block


    def _build_context_block(self, dialogue_history: List[InterviewPart], current_guest_answer: str) -> str:
        lines_block = ["КОНТЕКСТ ДИАЛОГА: "]

        if not dialogue_history and not current_guest_answer:
            lines_block.append("(начало диалога, истории нет)")
            return "\n".join(lines_block)

        for phrase in dialogue_history:
            role = phrase.role
            text = phrase.text
            lines_block.append(f"{role}: {text}")

        if current_guest_answer:
            lines_block.append(f"Последняя реплика гостя (на неё нужно ответить): {current_guest_answer}")

        context_block = "\n".join(lines_block)
        return context_block


    def _build_examples_block(self, rag_examples: List[RagExample]) -> str:
        if not rag_examples:
            return ""

        lines_block = ["ПРИМЕРЫ ВОПРОСОВ ИНТЕРВЬЮЕРА В ПОХОЖЕМ КОНТЕКСТЕ: "]
        for ex in rag_examples:
            text= ex.question_text
            lines_block.append(f"{text}")

        example_block = "\n".join(lines_block)
        return example_block

    @staticmethod
    def _build_output_constraints(template: Template) -> str:
        structure = getattr(template, "structure", None)

        if structure:
            schema_example = ", ".join(
                f'{{"role": "{role}", "content": "..."}}' for role in structure.split("+")
            )
            schema_roles = ", ".join(f'"{role}"' for role in structure.split("+"))
            json_hint = (
                "Ответ ВЕРНИ СТРОГО в формате JSON (без markdown, без префиксов, без пояснений):\n"
                f'{{"parts": [{schema_example}]}}\n'
                f"Массив parts должен содержать ровно {len(structure.split("+"))} элементов "
                f"в порядке: [{schema_roles}]. Каждый content - ровно одно предложение."
            )
        else:
            json_hint = (
                "Ответ верни в формате JSON: "
                '{"parts": [{"role": "question", "content": "..."}]}'
            )

        return "\n".join([
            "ФОРМАТ ВЫВОДА:",
            "- Сгенерируй ровно одну реплику интервьюера.",
            "- Строго следуй инструкции стиля, выполни каждый пункт обязательно.",
            "- Учитывай контекст диалога",
            "- Не добавляй пояснений, ярлыков или метакомментариев.",
            "- Не подписывай реплику именем интервьюера.",
            "- НЕЛЬЗЯ НИ В КОЕМ СЛУЧАЕ использовать '-', тире и дефис в сгенерированной фразе.",
            "- Обращайся с пользователем на 'ты', учитывай пол user_name.",
            json_hint,
        ])


class BuildSystemPromptService:
    def profile_to_instruction(self, profile: InterviewerProfile) -> List[str]:
        ling_profile = profile.linguistic_profile
        instructions: List[str] = []

        avg_len = getattr(ling_profile, "avg_question_length", None)
        if avg_len is not None:
            if avg_len < 10:
                instructions.append(
                    "Длина: реплика должна быть короткой и лаконичной (до 10 слов)."
                )
            elif avg_len > 20:
                instructions.append(
                    "Длина: реплика развёрнутая, многосоставная (более 20 слов)."
                )
            else:
                instructions.append(
                    f"Длина: реплика средней длины (~{int(avg_len)} слов)."
                )

        multi_sentence_ratio = getattr(ling_profile, "multi_sentence_ratio", None)
        if multi_sentence_ratio is not None and multi_sentence_ratio > 0.5:
            instructions.append(
                "Реплика может содержать несколько предложений подряд."
            )

        density_map = {
            "empathy": getattr(ling_profile, "empathy_density", None),
            "hedging": getattr(ling_profile, "hedging_density", None),
            "pressure": getattr(ling_profile, "pressure_density", None),
            "filler": getattr(ling_profile, "filler_density", None),
            "formal": getattr(ling_profile, "formal_density", None),
            "provocation": getattr(ling_profile, "provocation_density", None),
        }
        for category, density in density_map.items():
            _, line = _sample_marker(density, category)
            if line:
                instructions.append(line)

        characteristic_phrases = getattr(profile, "characteristic_phrases", []) or []
        if characteristic_phrases:
            phrases = " | ".join(characteristic_phrases[:3])
            instructions.append(
               f"Характерные фразы интервьюера (НЕ копируй их), "
                f": {phrases}"
            )

        return instructions


    def build_prompt(
            self,
            profile: InterviewerProfile,
            template: Template,
    ) -> BuildPromptResult:
        style_instructions = self.profile_to_instruction(profile)

        style_block = self._build_style_block(style_instructions)
        constraints_block = self._build_output_constraints(template)

        prompt = "\n\n".join([
            style_block,
            constraints_block,
        ])

        result = BuildPromptResult(
            prompt= prompt,
            style_instruction=style_instructions,
        )
        return result


    @staticmethod
    def _build_style_block(style_instructions: List[str]) -> str:
        if not style_instructions:
            return "ИНСТРУКЦИИ СТИЛЯ:\n- Нейтральный стиль без выраженных маркеров."
        lines_block = ["ИНСТРУКЦИЯ СТИЛЯ:"]
        for instruction in style_instructions:
            lines_block.append(f"- {instruction}")
        style_block = "\n".join(lines_block)
        return style_block


    @staticmethod
    def _build_output_constraints(template: Template) -> str:
        structure = getattr(template, "structure", None)

        if structure:
            schema_example = ", ".join(
                f'{{"role": "{role}", "content": "..."}}' for role in structure.split("+")
            )
            schema_roles = ", ".join(f'"{role}"' for role in structure.split("+"))
            json_hint = (
                "Ответ ВЕРНИ СТРОГО в формате JSON (без markdown, без префиксов, без пояснений):\n"
                f'{{"parts": [{schema_example}]}}\n'
                f"Массив parts должен содержать ровно {len(structure.split("+"))} элементов "
                f"в порядке: [{schema_roles}]. Каждый content - ровно одно предложение."
            )
        else:
            json_hint = (
                "Ответ верни в формате JSON: "
                '{"parts": [{"role": "question", "content": "..."}]}'
            )

        return "\n".join([
            "ФОРМАТ ВЫВОДА:",
            "- Сгенерируй ровно одну реплику интервьюера.",
            "- Строго следуй инструкции стиля, выполни каждый пункт обязательно.",
            "- Учитывай контекст диалога",
            "- Не добавляй пояснений, ярлыков или метакомментариев.",
            "- Не подписывай реплику именем интервьюера.",
            "- НЕЛЬЗЯ НИ В КОЕМ СЛУЧАЕ использовать '-', тире и дефис в сгенерированной фразе.",
            "- Обращайся с пользователем на 'ты', учитывай пол user_name.",
            json_hint,
        ])


class BuildUserPromptService:
    def __init__(self, max_history: int = 5) -> None:
        self.max_history = max_history


    def build_prompt(
            self,
            input_data: GenerationRequest,
            template: Template,
            rag_examples: list[RagExample]
    ) -> BuildPromptResult:

        structure_block = self._build_structure_block(template)
        context_block = self._build_context_block(input_data.full_interview_history, input_data.last_answer)
        examples_block = self._build_examples_block(rag_examples)

        prompt = "\n\n".join([
            "Ты генерируешь следующее высказывание интервьюера для диалога с пользователем.",
            f"Имя пользователя: {input_data.user_name}",
            f"Информация о пользователе: {input_data.user_info}",
            structure_block,
            context_block,
            examples_block,
        ])

        result = BuildPromptResult(
            prompt= prompt,
            style_instruction=[],
        )
        return result

    @staticmethod
    def _build_structure_block(template: Template) -> str:
        structure = getattr(template, "structure", None)
        action = getattr(template, "action", None)
        question_openness = getattr(template, "question_openness", None)
        emotion = getattr(template, "emotion", None)
        techniques = getattr(template, "techniques", None)

        lines_block = ["СТРУКТУРА РЕПЛИКИ:"]

        if structure:
            lines_block.append(
                f"- Реплика состоит РОВНО из {len(structure.split("+"))} частей в порядке: {structure}."
            )
            lines_block.append(
                "- Каждая часть - ровно одно предложение. Не сливай части и не пропускай их."
            )
            lines_block.append("- Значения ролей:")
            if "question" in structure:
                lines_block.append("-- question - Прямая вопросительная конструкция, нацеленная на получение конкретных фактов, имен, "
                               "дат или уточнение обстоятельств события, заканчивается знаком вопроса.")
            if "acknowledgment" in structure:
                lines_block.append("-- acknowledgment - Минимальная реакция, подтверждающая, "
                               "что интервьюер слушает гостя и понимает его. ")
            if "bridge" in structure:
                lines_block.append("-- bridge - связующая фраза для навигации: смена темы, возврат "
                               "к недосказанному или обозначение структуры разговора.")
            if "paraphrase" in structure:
                lines_block.append("-- paraphrase - сжатый пересказ слов собеседника или подведение итога сказанному, "
                               "чтобы подтвердить правильность понимания сути.")
            if "empathy" in structure:
                lines_block.append("-- empathy - демонстрация эмоциональной связи: выражение сочувствия, "
                               "удивления, поддержки или уместного сомнения в словах гостя.")
            if "request" in structure:
                lines_block.append("-- request - призыв к активному действию: просьба раскрыть тему подробнее, "
                               "привести живой пример, описать свои чувства или пояснить позицию.")
            if "text" in structure:
                lines_block.append("-- text - информационное наполнение реплики: изложение фактов, вводных данных "
                               "или личного мнения интервьюера, создающее фон для вопроса.")

        if action is not None:
            lines_block.append(f"- Основное действие фразы: {action}")

        if question_openness is not None:
            lines_block.append(f"- Тип фразы по открытости вопроса: {question_openness}")

        if emotion is not None:
            lines_block.append(f"- Эмоциональная окраска: {emotion}")

        if techniques is not None:
            lines_block.append(f"- Используемые техники: {', '.join(techniques)}")

        structure_block = "\n".join(lines_block)
        return structure_block


    def _build_context_block(self, dialogue_history: List[InterviewPart], current_guest_answer: str) -> str:
        lines_block = ["КОНТЕКСТ ДИАЛОГА: "]

        if not dialogue_history and not current_guest_answer:
            lines_block.append("(начало диалога, истории нет)")
            return "\n".join(lines_block)

        for phrase in dialogue_history:
            role = phrase.role
            text = phrase.text
            lines_block.append(f"{role}: {text}")

        if current_guest_answer:
            lines_block.append(f"Последняя реплика гостя (на неё нужно ответить): {current_guest_answer}")

        context_block = "\n".join(lines_block)
        return context_block


    def _build_examples_block(self, rag_examples: List[RagExample]) -> str:
        if not rag_examples:
            return ""

        lines_block = ["ПРИМЕРЫ ВОПРОСОВ ИНТЕРВЬЮЕРА В ПОХОЖЕМ КОНТЕКСТЕ: "]
        for ex in rag_examples:
            text= ex.question_text
            lines_block.append(f"{text}")

        example_block = "\n".join(lines_block)
        return example_block
