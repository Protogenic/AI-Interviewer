from typing import List

from ai_service.models.generation import GenerationRequest, BuildPromptResult, InterviewPart
from ai_service.models.build_profile import InterviewerProfile, Template


class BuildPromptService:
    def __init__(self, max_history: int = 5) -> None:
        self.max_history = max_history


    def profile_to_instruction(self, profile: InterviewerProfile) -> List[str]:
        ling_profile = profile.linguistic_profile
        instructions = []

        avg_len = getattr(ling_profile, "avg_question_length", None)
        empathy_density = getattr(ling_profile, "empathy_density", None)
        hedging_density = getattr(ling_profile, "hedging_density", None)
        pressure_density = getattr(ling_profile, "pressure_density", None)
        filler_density = getattr(ling_profile, "filler_density", None)
        formal_density = getattr(ling_profile, "formal_density", None)
        provocation_density = getattr(ling_profile, "provocation_density", None)
        avg_phrase_length = getattr(ling_profile, "avg_phrase_length", None)
        multi_sentence_ratio = getattr(ling_profile, "multi_sentence_ratio", None)
        number_of_questions = getattr(ling_profile, "number_of_questions", None)

        if avg_len < 10:
            instructions.append("Задавай краткий и лаконичный вопрос.")
        elif avg_len > 20:
            instructions.append("Задавай сложный и многокомпонентный вопрос.")

        if empathy_density == 0.0:
            instructions.append("Эмпатичные маркеры: отсутствуют. Не используй эмпатичные маркеры.")
        elif empathy_density > 0.003:
            instructions.append(
                "Эмпатичные маркеры: низкая плотность. Используй эмпатичные маркеры редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif empathy_density > 0.01:
            instructions.append(
                "Эмпатичные маркеры: высокая плотность. Используй эмпатичные маркеры когда уместно.")

        instructions.append("Типичные эмпатичные маркеры: понимаю, понятно, сложно, спасибо, жесть, ой, ничего себе, ну да."
                            "Используйте их только тогда, когда они естественны в контексте.")


        if hedging_density == 0.0:
            instructions.append("Маркеры хеджирования: отсутствуют. Не используй маркеры хеджирования.")
        elif hedging_density > 0.003:
            instructions.append(
                "Маркеры хеджирования: низкая плотность. Используй маркеры хеджирования редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif hedging_density > 0.01:
            instructions.append(
                "Маркеры хеджирования: высокая плотность. Используй маркеры хеджирования когда уместно.")

        instructions.append("Типичные маркеры хеджирования: как бы, мне кажется,по-моему, наверное, вроде, может быть, допустим."
                            "Используйте их только тогда, когда они естественны в контексте.")

        if pressure_density == 0.0:
            instructions.append("Маркеры давления: отсутствуют. Не используй маркеры давления.")
        elif pressure_density > 0.003:
            instructions.append(
                "Маркеры давления: низкая плотность. Используй маркеры давления редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif pressure_density > 0.01:
            instructions.append(
                "Маркеры давления: высокая плотность. Используй маркеры давления когда уместно.")

        instructions.append(
            "Типичные маркеры давления: вы же, подождите, почему же, вы уверены, как вы это объясните, серьёзно, разве."
            "Используйте их только тогда, когда они естественны в контексте.")

        if filler_density == 0.0:
            instructions.append("Маркеры наполнения: отсутствуют. Не используй маркеры наполнения.")
        elif filler_density > 0.003:
            instructions.append(
                "Маркеры наполнения: низкая плотность. Используй маркеры наполнения редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif filler_density > 0.01:
            instructions.append(
                "Маркеры наполнения: высокая плотность. Используй маркеры наполнения когда уместно.")

        instructions.append(
            "Типичные маркеры наполнения: ну, э, угу, так, ага, вот, то есть, слушай, смотрите, о, ну да."
            "Используйте их только тогда, когда они естественны в контексте.")

        if formal_density == 0.0:
            instructions.append("Формальные маркеры: отсутствуют. Не используй формальные маркеры.")
        elif formal_density > 0.003:
            instructions.append(
                "Формальные маркеры: низкая плотность. Используй формальные маркеры редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif formal_density > 0.01:
            instructions.append(
                "Формальные маркеры: высокая плотность. Используй формальные маркеры когда уместно.")

        instructions.append(
            "Типичные формальные маркеры: расскажите, объясните, уточните, как вы относитесь, что значит, "
            "с каких пор, когда последний раз, для начала, поговорим про, давайте об этом, как это было."
            "Используйте их только тогда, когда они естественны в контексте.")

        if provocation_density == 0.0:
            instructions.append("Провокационные маркеры: отсутствуют. Не используй провокационные маркеры.")
        elif provocation_density > 0.003:
            instructions.append(
                "Провокационные маркеры: низкая плотность. Используй провокационные маркеры редко, не более 1 в предложении, если в истории диалога они отсутсвуют.")
        elif provocation_density > 0.01:
            instructions.append(
                "Провокационные маркеры: высокая плотность. Используй провокационные маркеры когда уместно.")

        instructions.append(
            "Типичные провокационные маркеры: расскажите, объясните, уточните, как вы относитесь, что значит, "
            "с каких пор, когда последний раз, для начала, поговорим про, давайте об этом, как это было."
            "Используйте их только тогда, когда они естественны в контексте.")

        characteristic_phrases = getattr(profile, "characteristic_phrases", [])
        if characteristic_phrases:
            instructions.append("Опционально используйте примеры фраз интервьюера. "
                                f"Примеры фраз интервьюера:{' '.join(characteristic_phrases[:3])}")

        return instructions


    def build_prompt(self, input_data: GenerationRequest, profile: InterviewerProfile, template: Template) -> BuildPromptResult:
        style_instructions = self.profile_to_instruction(profile)

        structure_block = self._build_structure_block(template)
        style_block = self._build_style_block(style_instructions)
        context_block = self._build_context_block(input_data.full_interview_history, input_data.last_answer)
        constraints_block = self._build_output_constraints()

        prompt = "\n\n".join([
            "Ты генерируешь следующее высказывание интервьюера для диалога с пользователем в стиле конкретного интервьюера.",
            structure_block,
            style_block,
            context_block,
            constraints_block,
        ])

        result = BuildPromptResult(
            prompt= prompt,
            style_instruction=style_instructions,
            example_used=0
        )
        return result

    @staticmethod
    def _build_structure_block(template: Template) -> str:
        structure = getattr(template, "structure")
        action = getattr(template, "action")
        technique = getattr(template, "technique")
        examples = getattr(template, "examples")

        lines_block = [
            "СТРУКТУРА:",
            f"- Следуй этой структуре: {structure}"
            f"Каждый элемент - предложение."
        ]

        if technique is not None:
            lines_block.append(f"- Используй технику вопроса: {technique}")

        if action is not None:
            lines_block.append(f"- Используй действие для диалога: {action}")

        if examples:
            lines_block.append("Примеры вопросов этого интервьюера: ")
            for example in examples:
                lines_block.append(f" - {example}")

        structure_block = "\n".join(lines_block)
        return structure_block

    @staticmethod
    def _build_style_block(style_instructions: List[str]) -> str:
        lines_block = ["ИНСТРУКЦИЯ СТИЛЯ:"]
        for instruction in style_instructions:
            lines_block.append(f"- {instruction}")
        style_block = "\n".join(lines_block)
        return style_block


    def _build_context_block(self, dialogue_history: List[InterviewPart], current_guest_answer: str) -> str:
        lines_block = ["КОНТЕКСТ ДИАЛОГА С ПОЛЬЗОВАТЕЛЕМ: "]

        for phrase in dialogue_history:
            role = phrase.role
            text = phrase.text
            lines_block.append(f"{role}: {text}")

        if current_guest_answer:
            lines_block.append(f"Последняя фраза гостя, после которой нужно дать ответ: {current_guest_answer}")

        context_block = "\n".join(lines_block)
        return context_block

    @staticmethod
    def _build_output_constraints() -> str:
        return "\n".join([
            "ОГРАНИЧЕНИЯ ДЛЯ ГЕНЕРАЦИИ:",
            "- Генерируй ровно одно высказывание интервьюера.",
            "- Делай высказывание естественным и реалистичным.",
            "- Не объясняй свои рассуждения.",
            "- Не добавляй ярлыки или маркеры.",
            "- Сохрани заданную структуру и стиль.",
        ])
