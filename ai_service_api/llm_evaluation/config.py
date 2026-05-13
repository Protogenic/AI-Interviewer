import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    label: str
    api_key: str | None
    base_url: str | None
    model: str
    price_input: float
    price_output: float
    use_json_mode: bool = True
    request_delay: float = 0.0


def _env(name: str) -> str | None:
    return os.getenv(name) or None



ALL_PROVIDERS: list[ProviderConfig] = [

    # OpenAI
    ProviderConfig(
        label="openai/gpt-4o",
        api_key=_env("OPENAI_API_KEY"),
        base_url=None,
        model="gpt-4o",
        price_input=2.50,
        price_output=10.00,
    ),
    ProviderConfig(
        label="openai/gpt-4o-mini",
        api_key=_env("OPENAI_API_KEY"),
        base_url=None,
        model="gpt-4o-mini",
        price_input=0.15,
        price_output=0.60,
    ),


    # OpenRouter paid
    ProviderConfig(
        label="or/deepseek-chat",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-chat",
        price_input=0.27,
        price_output=1.10,
    ),
    ProviderConfig(
        label="or/llama-3.3-70b",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.3-70b-instruct",
        price_input=0.12,
        price_output=0.30,
        use_json_mode=False,
    ),
    ProviderConfig(
        label="or/llama-3.1-8b",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.1-8b-instruct",
        price_input=0.05,
        price_output=0.08,
        use_json_mode=False,
    ),
    ProviderConfig(
        label="or/gemini-2.5-flash",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="google/gemini-2.5-flash",
        price_input=0.15,
        price_output=0.60,
    ),
    ProviderConfig(
        label="or/gemini-2.0-flash",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="google/gemini-2.0-flash-001",
        price_input=0.10,
        price_output=0.40,
    ),
    ProviderConfig(
        label="or/mistral-small-3.1",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="mistralai/mistral-small-3.1-24b-instruct",
        price_input=0.10,
        price_output=0.30,
    ),
    ProviderConfig(
        label="or/mistral-large",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="mistralai/mistral-large-2411",
        price_input=2.00,
        price_output=6.00,
    ),
    ProviderConfig(
        label="or/claude-3.5-haiku",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="anthropic/claude-3.5-haiku",
        price_input=0.80,
        price_output=4.00,
    ),
    ProviderConfig(
        label="or/qwen2.5-72b",
        api_key=_env("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="qwen/qwen-2.5-72b-instruct",
        price_input=0.35,
        price_output=0.40,
    ),
]

JUDGE_MODEL = "gpt-4o"
JUDGE_API_KEY = _env("OPENAI_API_KEY")

EVAL_TEMPERATURE = 0.0
EVAL_MAX_TOKENS = 500

RESULTS_DIR = "llm_evaluation/results"
