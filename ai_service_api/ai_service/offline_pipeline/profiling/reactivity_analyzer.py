from collections import Counter, defaultdict
from typing import List, Dict

from ai_service.models.build_profile import AnnotatedPhrase

class ReactivityAnalyzer:
    def build_matrix(self, phrases: List[AnnotatedPhrase]) -> Dict[str, Dict[str, int]]:
        matrix = defaultdict(Counter)

        for i in range(len(phrases) - 1):
            current_phrase = phrases[i]
            next_phrase = phrases[i+1]

            if current_phrase.role == "guest" and next_phrase.role == "interviewer":
                if current_phrase.answer_type and next_phrase.action:
                    matrix[current_phrase.answer_type.value][next_phrase.action.value] += 1

        return {answer_type: dict(counter) for answer_type, counter in matrix.items()}

    def print_matrix(self, matrix: Dict[str, Dict[str, int]]) -> None:
        print("------Reactivity Matrix------")
        for answer_type, reaction in matrix.items():
            print(f"\n{answer_type}:")
            for act, count in sorted(reaction.items(), key=lambda x:x[1], reverse=True):
                print(f"    {act}: {count}")