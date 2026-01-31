#!/usr/bin/env python3
"""
Универсальный AI‑интервьюер
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from interviewer import AIInterviewer  # noqa


def main() -> None:
    bot = AIInterviewer()
    bot.persona_manager.print_info()

    print("\nИнтервью начато.")
    print("reset — очистить контекст, exit — выход\n")

    while True:
        try:
            user_input = input("Гость: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "выход"):
            break

        if user_input.lower() == "reset":
            bot.reset_history()
            continue

        answer = bot.generate(user_input)
        print(f"\nИнтервьюер: {answer}\n")


if __name__ == "__main__":
    main()
