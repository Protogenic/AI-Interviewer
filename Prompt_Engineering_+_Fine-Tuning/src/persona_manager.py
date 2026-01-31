import json
from typing import Any, Dict, List

from config import PERSONA_PATH


class PersonaManager:
    def __init__(self, path=PERSONA_PATH):
        self.path = path
        self.persona = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._get_default()

        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("persona", self._get_default())

    def _get_default(self) -> Dict[str, Any]:
        default = {
            "name": "Interviewer",
            "role": "General Interviewer",
            "system_instructions": "Ты интервьюер. Задавай глубокие вопросы."
        }
        self.save(default)
        return default

    def save(self, persona: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"persona": persona}
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_name(self) -> str:
        return self.persona.get("name", "Interviewer")

    def get_role(self) -> str:
        return self.persona.get("role", "Interviewer")

    def get_system_prompt(self) -> str:
        system_instructions = self.persona.get("system_instructions", "")

        # Тон
        tone = self.persona.get("tone", {})
        tone_desc = tone.get("primary", "neutral")

        # Черты
        traits = self.persona.get("key_traits", [])
        traits_str = "\n".join([f"- {t}" for t in traits[:4]])

        # Язык
        lang_style = self.persona.get("language_style", {})
        vocab = ", ".join(lang_style.get("vocabulary_markers", [])[:6])
        syntax = "\n".join([f"  • {p}" for p in lang_style.get("syntax_patterns", [])[:3]])

        # Табу
        taboos = lang_style.get("taboos", [])
        taboo_rules = "\nНЕ ИСПОЛЬЗУЙ:\n" + "\n".join([f"  ❌ {t}" for t in taboos])

        # Few-shot
        few_shots = self.persona.get("few_shot_examples", [])
        examples = "\nПРИМЕРЫ:\n"
        for ex in few_shots[:3]:
            examples += f"\n📝 {ex.get('context', '')}\n"
            examples += f"   → {ex.get('response', '')}\n"

        # Параметры
        gen_params = self.persona.get("generation_parameters", {})
        temp_note = f"Temperature: {gen_params.get('temperature', 0.7)}"

        prompt = f"""{system_instructions}

ЧЕРТЫ:
{traits_str}

СТИЛЬ:
{syntax}

СЛОВА: {vocab}

{taboo_rules}

{examples}

Тон: {tone_desc}
{temp_note}

ПРАВИЛА:
• Отвечай только как интервьюер
• Каждый ответ — 1–3 вопроса
• Используй историю разговора
"""
        return prompt

    def print_info(self) -> None:
        print(f"Персонаж: {self.get_name()}")
        print(f"Роль: {self.get_role()}")
