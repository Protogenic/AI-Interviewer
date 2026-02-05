from dataclasses import dataclass
from typing import Optional, List, Dict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import DEVICE, GENERATION_CONFIG, ENABLE_THINKING, BASE_MODEL_NAME
from persona_manager import PersonaManager


@dataclass
class InterviewerConfig:
    model_name: str = MODEL_NAME
    device: str = DEVICE
    temperature: float = GENERATION_CONFIG["temperature"]
    top_p: float = GENERATION_CONFIG["top_p"]
    top_k: int = GENERATION_CONFIG["top_k"]
    max_new_tokens: int = GENERATION_CONFIG["max_new_tokens"]
    do_sample: bool = GENERATION_CONFIG["do_sample"]
    enable_thinking: bool = ENABLE_THINKING


class AIInterviewer:
    def __init__(self, config: Optional[InterviewerConfig] = None):
        self.config = config or InterviewerConfig()
        self.persona_manager = PersonaManager()
        self.history: List[Dict[str, str]] = []
        self.tokenizer = None
        self.model = None
        self._load_model()
        self.persona_manager.print_info()

    def _load_model(self) -> None:
        print(f"Загрузка базовой модели {BASE_MODEL_NAME}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            BASE_MODEL_NAME,
            trust_remote_code=True,
        )

        # Загружаем БАЗОВУЮ модель (скачается автоматически)
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            torch_dtype=torch.float16 if self.config.device == "cuda" else torch.float32,
            device_map="auto" if self.config.device == "cuda" else None,
            low_cpu_mem_usage=True,
        )

        # ← НОВОЕ: Накладываем ТВОЙ LoRA адаптер
        from peft import PeftModel
        print(f"Загрузка LoRA из {LORA_PATH}...")
        self.model = PeftModel.from_pretrained(
            base_model,
            str(LORA_PATH)  # путь к твоей папке с adapter_config.json + adapter_model.safetensors
        )

        if self.config.device == "cpu":
            self.model = self.model.to("cpu")

        print(f"✅ LoRA-модель загружена на {self.config.device}")

    def generate(self, user_input: str) -> str:
        messages = [{"role": "system", "content": self.persona_manager.get_system_prompt()}]
        recent_history = self.history[-4:] if len(self.history) > 4 else self.history
        messages.extend(recent_history)
        messages.append({"role": "user", "content": user_input})

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.config.enable_thinking,
        )

        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                do_sample=self.config.do_sample,
            )[0]

        answer_ids = output_ids[len(inputs.input_ids[0]):]
        response = self.tokenizer.decode(answer_ids, skip_special_tokens=True).strip()

        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response})

        if len(self.history) > 10:
            self.history = self.history[-10:]

        return response

    def reset_history(self) -> None:
        self.history = []
        print("История очищена")
