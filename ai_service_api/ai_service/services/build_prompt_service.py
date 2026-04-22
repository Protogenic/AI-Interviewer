from typing import List, Tuple, Optional
import random

from ai_service.models.generation import GenerationRequest, BuildPromptResult, InterviewPart
from ai_service.models.build_profile import InterviewerProfile, Template
from ai_service.models.rag import RagExample
from ai_service.offline_pipeline.profiling.markers import MARKERS


def _sample_marker(
    density: Optional[float],
    category: str,
    emotion: str,
    scale: float = 40.0,
) -> Tuple[bool, str]:
    rng = random.Random()
    if density is None or density <= 0:
        return False, ""

    probability = min(1.0, density * scale)
    use = rng.random() < probability
    if not use:
        return False, ""

    if emotion == "empathy":
        if category == "empathy" or category == "filler" or category == "hedging":
            meta = MARKERS[category]
            instruction = (
                "# ОБЯЗАТЕЛЬНО В ЭТОЙ РЕПЛИКЕ"
                f"Используй ровно один подходящий маркер {meta['label']} "
                f"из списка: [ {', '.join(meta['examples'])}]. "
                "Если маркер уже был недавно в ИСТОРИИ ДИАЛОГА, то выбери другой. "
                f"Вставь его естественно в любое место внутри фразы."
            )
            return True, instruction

    if emotion == "challenge":
        if category == "pressure" or category == "provocation" or category == "formal":
            meta = MARKERS[category]
            instruction = (
                "# ОБЯЗАТЕЛЬНО В ЭТОЙ РЕПЛИКЕ"
                f"Используй ровно один подходящий маркер {meta['label']} "
                f"из списка: [ {', '.join(meta['examples'])} ]."
                "Если маркер уже был недавно в ИСТОРИИ ДИАЛОГА, то выбери другой. "
                f"Вставь его естественно в любое место внутри фразы."
            )
            return True, instruction

    if emotion == "neutral" or  emotion == "commentary" or  emotion == "no_emotion":
        if category != "pressure" and category != "provocation" and category != "empathy":
            meta = MARKERS[category]
            instruction = (
                "# ОБЯЗАТЕЛЬНО В ЭТОЙ РЕПЛИКЕ"
                f"Используй ровно один подходящий маркер {meta['label']}."
                f"из списка: [ {', '.join(meta['examples'])} ]. "
                "Если маркер уже был недавно в ИСТОРИИ ДИАЛОГА, то выбери другой. "
                f"Вставь его исходя из контекста вопроса в любое место внутри фразы."
            )
            return True, instruction
    return False, " "


class BuildSystemPromptService:
    def build_prompt(
            self,
            profile: InterviewerProfile,
            template: Template,
    ) -> BuildPromptResult:
        style_instructions = self.profile_to_instruction(profile, template)

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


    def profile_to_instruction(self, profile: InterviewerProfile, template: Template) -> List[str]:
        ling_profile = profile.linguistic_profile
        instructions: List[str] = []

        instructions.append(
            "Ты - Юрий Дудь, российский журналист-интервьюер. "
            "Твоя задача - выдать одну реплику этого интервьюера "
            "в соответствии с последним ответом гостя и историей диалога."
        )

        multi_sentence_ratio = getattr(ling_profile, "multi_sentence_ratio", None)
        if multi_sentence_ratio is not None and multi_sentence_ratio > 0.5:
            instructions.append(
                "Реплика это одно или несколько предложений, "
                "которые могут быть вопросом, утверждением, восклицанием или междометием."
            )
        else:
            instructions.append(
                "Реплика это ровно одно предложение, "
                "которое может быть вопросом, утверждением, восклицанием или междометием."
            )

        instructions.append(
            "# ПЕРСОНА"
        )

        avg_len = getattr(ling_profile, "avg_question_length", None)
        if avg_len is not None:
            if avg_len < 10:
                instructions.append(
                    "Длина: реплика должна быть короткой и лаконичной (до 10 слов)."
                )
            elif avg_len > 30:
                instructions.append(
                    "Длина: реплика развёрнутая, многосоставная (более 30 слов)."
                )
            else:
                instructions.append(
                    f"Длина: реплика средней длины (~{int(avg_len)} +- 5 слов)."
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
            _, line = _sample_marker(density, category, template.emotion)
            if line:
                instructions.append(line)

        instructions.append(
            "# ОБРАЩЕНИЕ"
            "Всегда 'ты'. Никогда 'вы'. В примерах ниже может встречаться 'вы' - это артефакт расшифровок, игнорируй."
        )

        instructions.append(
            "# ПУНКТУАЦИЯ"
            "Используй: точка, запятая, '?', '!', '...'."
            "Тире '—' и дефис '-' не используй. Вместо тире начинай новое предложение или ставь запятую."
        )

        instructions.append(
            "# ОБРАЗЦЫ СТИЛЯ ИНТЕРВЬЮЕРА "
            "Это живые цитаты из реальных интервью. Считывай ритм, лексику, степень прямоты:"
        )

        characteristic_phrases = getattr(profile, "characteristic_phrases", []) or []
        if characteristic_phrases:
            phrases = "\n-".join(characteristic_phrases[:5])
            instructions.append(
                f"{phrases}"
            )

        instructions.append(
            "Не копируй эти фразы дословно. Опирайся на ощущение стиля."
        )

        return instructions


    @staticmethod
    def _build_style_block(style_instructions: List[str]) -> str:
        if not style_instructions:
            return "ИНСТРУКЦИИ СТИЛЯ:\n- Нейтральный стиль без выраженных маркеров."
        style_block = "\n".join(style_instructions)
        return style_block


    @staticmethod
    def _build_output_constraints(template: Template) -> str:
        structure = getattr(template, "structure", None)

        if structure:
            schema_example = ", ".join(
                f'{{"role": "{role}", "content": "..."}}' for role in structure.split('+')
            )
            schema_roles = ", ".join(f'"{role}"' for role in structure.split('+'))
            json_hint = (
                "Только валидный JSON без markdown, комментариев, без префиксов, без пояснений:\n"
                "{'parts': [{'role': '<role>', 'content': '<one sentence>'}]}\n"
                "- Ровно столько элементов и в том порядке, как задано в поле STRUCTURE пользовательского сообщения.\n"
                "- Каждый content - ровно одно предложение.\n"
                "- Не подписывай реплику именем.\n"
                "# ПРИМЕР КОРРЕКТНОГО ВЫВОДА\n"
                "STRUCTURE: question + acknowledgment\n"
                "{'parts': ["
                "{'role': 'question', 'content': 'А ты после этого вообще спал?'},"
                "{'role': 'acknowledgment', 'content': 'Угу.'}"
                "]}"
                #f'{{"parts": [{schema_example}]}}\n'
                #f"Массив parts должен содержать ровно {len(structure.split('+'))} элементов "
                #f"в порядке: [{schema_roles}]. Каждый content - ровно одно предложение."
            )
        else:
            json_hint = (
                "Ответ верни в формате JSON: "
                '{"parts": [{"role": "question", "content": "..."}]}'
            )

        '''return "\n".join([
            "ФОРМАТ ВЫВОДА:",
            "- Сгенерируй ровно одну реплику интервьюера.",
            "- Реплика должна быть естественной.",
            "- Строго следуй инструкции стиля, выполни каждый пункт обязательно.",
            "- Учитывай контекст диалога",
            "- Не добавляй пояснений, ярлыков или метакомментариев.",
            "- Не подписывай реплику именем интервьюера.",
            "- НЕЛЬЗЯ НИ В КОЕМ СЛУЧАЕ использовать '-', тире и дефис в сгенерированной фразе.",
            "- Всегда общайся с пользователем на 'ты', учитывай пол user_name.",
            json_hint,
        ])'''
        return "\n".join(["ФОРМАТ ВЫВОДА:", json_hint])


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
            "# ГОСТЬ",
            f"Имя пользователя: {input_data.user_name}",
            f"Информация о пользователе: {input_data.user_info}",
            context_block,
            structure_block,
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
        examples = getattr(template, "examples", None)

        lines_block = ["# STRUCTURE ДЛЯ ГЕНЕРИРУЕМОЙ РЕПЛИКИ ИНТЕРВЬЮЕРА:"]

        if structure:
            lines_block.append(
                f"Роли по порядку: {structure}."
            )
            lines_block.append(
                f"Реплика состоит РОВНО из {len(structure.split('+'))} предложений."
            )
            lines_block.append("Значения ролей:")
            if "question" in structure:
                lines_block.append("- question - Прямая вопросительная конструкция, нацеленная на получение конкретных фактов, имен, "
                               "дат или уточнение обстоятельств события, заканчивается знаком вопроса.")
            if "acknowledgment" in structure:
                lines_block.append("- acknowledgment - Минимальная реакция, подтверждающая, "
                               "что интервьюер слушает гостя и понимает его. Утвердительное или восклицательное предложение.")
            if "bridge" in structure:
                lines_block.append("- bridge - связующая фраза для навигации: смена темы, возврат "
                               "к недосказанному или обозначение структуры разговора. Утвердительное предложение.")
            if "paraphrase" in structure:
                lines_block.append("- paraphrase - сжатый пересказ слов собеседника или подведение итога сказанному, "
                               "чтобы подтвердить правильность понимания сути. Утвердительное предложение.")
            if "empathy" in structure:
                lines_block.append("- empathy - демонстрация эмоциональной связи: выражение сочувствия, "
                               "удивления, поддержки или уместного сомнения в словах гостя. Утвердительное или восклицательное предложение.")
            if "request" in structure:
                lines_block.append("- request - призыв к активному действию: просьба раскрыть тему подробнее, "
                               "привести живой пример, описать свои чувства или пояснить позицию. Утвердительное предложение.")
            if "text" in structure:
                lines_block.append("- text - информационное наполнение реплики: изложение фактов, вводных данных "
                               "или личного мнения интервьюера, создающее фон для вопроса. Утвердительное предложение.")

        if action is not None:
            if action == "back_channel":
                lines_block.append(f"- Основное действие фразы: дать короткий сигнал обратной связи.")
            if action == "acknowledgment":
                lines_block.append(f"- Основное действие фразы: выразить короткое согласие или понимание.")
            if action == "clarification":
                lines_block.append(f"- Основное действие фразы: уточнить детали или спросить что-то по той же теме.")
            if action == "transition":
                lines_block.append(f"- Основное действие фразы (ПРИОРИТЕТ): перейти к совершенно новой теме, которой нет в истории диалога.")
            if action == "summary":
                lines_block.append(f"- Основное действие фразы: подытожить или перефразировать для подтверждения.")
            if action == "question":
                lines_block.append(f"- Основное действие фразы: задать новый вопрос по другому аспекту темы.")
            if action == "uncertain":
                lines_block.append(f"- Основное действие фразы: обычный текст.")

        if question_openness is not None:
            if action == "question":
                if question_openness == "open_question":
                    lines_block.append(f"- Вопрос должен быть открытым.")
                if question_openness == "closed_question":
                    lines_block.append(f"- Вопрос должен быть закрытым.")
                if question_openness == "blitz":
                    lines_block.append(f"- Блиц вопрос: он должен быть коротким и соответсвовать структуре 'что-то' или 'что-то'?.")
            else:
                if question_openness == "not_a_question" or question_openness == "uncertain_question":
                    lines_block.append(f"- Реплика должна быть не вопросом.")

        if emotion is not None:
            if emotion == "neutral" or emotion == "no_emotion":
                lines_block.append(f"- Эмоциональная окраска: нейтральный тон")
            if emotion == "challenge":
                lines_block.append(f"- Эмоциональная окраска: провокационная, испытывающая")
            if emotion == "empathy":
                lines_block.append(f"- Эмоциональная окраска: сочуствие, эмпатия.")
            if emotion == "commentary":
                lines_block.append(f"- Эмоциональная окраска: короткая реакция одобрения на ответ гостя('это круто', 'супер', 'хорошо' и т.д.).")

        if techniques is not None:
            tech = ', '.join(techniques)
            lines_block.append(f"- Используй все или некоторые техники:")
            if "behavioral" in tech:
                lines_block.append(
                    "- behavioral - вопрос о конкретных поступках и действиях в прошлом.")
            if "why_question" in tech:
                lines_block.append(
                    "- why_question - вопрос 'почему' и похожие.")
            if "how_question" in tech:
                lines_block.append(
                    "- how_question - вопрос 'как' и похожие.")
            if "values_exploration" in tech:
                lines_block.append(
                    "- values_exploration - вопрос про отношение и значение чего-то для гостя.")
            if "fact_checking" in tech:
                lines_block.append(
                    "- fact_checking - проверка достоверности чего-либо.")
            if "definition_request" in tech:
                lines_block.append(
                    "- definition_request - просьба что-нибудь объяснить.")
            if "reaction_request" in tech:
                lines_block.append(
                    "- reaction_request - про реакцию на что-то.")
            if "quantity_request" in tech:
                lines_block.append(
                    "- quantity_request - запрос конкретной стоимости чего-либо.")
            if "time_request" in tech:
                lines_block.append(
                    "- time_request - уточнение дат определенных событий.")
            if "background_request" in tech:
                lines_block.append(
                    "- background_request - изучение контекста, предыстории событий.")
            if "relationship" in tech:
                lines_block.append(
                    "- relationship - про отношения с людьми.")
            if "opinion_request" in tech:
                lines_block.append(
                    "- opinion_request - о личном взгляде гостя на какую-либо тему.")
            if "example_request" in tech:
                lines_block.append(
                    "- example_request - просьба привести реальный случай или пример.")
            if "hypothetical" in tech:
                lines_block.append(
                    "- hypothetical - моделирование вымышленной ситуациии и вопрос про выбор гостя в таких обстоятельствах.")
            if "confirmation" in tech:
                lines_block.append(
                    "- confirmation - уточняющий вопрос для проверки правильности понимания фразы гостя.")
            if "follow_up" in tech:
                lines_block.append(
                    "- follow_up - дополнительный вопрос, вытекающий из последнего ответа собеседника.")

        if examples is not None:
            lines_block.append(f"# ТАК ЗВУЧИТ ЭТОТ ШАБЛОН У ИНТЕРВЬЮЕРА: {', '.join(examples)}")

        structure_block = "\n".join(lines_block)
        return structure_block


    def _build_context_block(self, dialogue_history: List[InterviewPart], current_guest_answer: str) -> str:
        lines_block = ["# ИСТОРИЯ ДИАЛОГА "]

        if not dialogue_history and not current_guest_answer:
            lines_block.append("(начало диалога, истории нет)")
            return "\n".join(lines_block)

        for phrase in dialogue_history:
            role = phrase.role
            text = phrase.text
            lines_block.append(f"{role}: {text}")

        if current_guest_answer:
            lines_block.append(f"# ПОСЛЕДНЯЯ РЕПЛИКА ГОСТЯ: {current_guest_answer}")

        context_block = "\n".join(lines_block)
        return context_block


    def _build_examples_block(self, rag_examples: List[RagExample]) -> str:
        if not rag_examples:
            return ""

        lines_block = ["# ПОХОЖИЕ СИТУАЦИИ В ДИАЛОГЕ. "]
        for ex in rag_examples:
            text_q = ex.question_text
            text_a = ex.answer_text
            lines_block.append(f"Интервьюер: {text_q} \n Гость: {text_a}")

        lines_block.append("Из примеров возьми только ритм, длину и тональность. Тема реплики — только из диалога выше.")

        example_block = "\n".join(lines_block)
        return example_block
