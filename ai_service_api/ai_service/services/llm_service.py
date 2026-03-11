

class DummyLLMClient:
    async def generate_question(self, prompt: str) -> str:
        # Позже будет прописано взаимодействие с LLM
        return "Как давно ты занимаешься программированием?"