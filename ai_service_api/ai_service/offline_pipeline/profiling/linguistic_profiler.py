import re
from statistics import mean
from typing import List

from ai_service_api.ai_service.offline_pipeline.profiling.markers import LinguisticProfileMarker
from ai_service_api.ai_service.models.build_profile import LinguisticProfile

class LinguisticProfiler:
    def build_profile(self, interviewer_texts: List[str]) -> LinguisticProfile:
        markers = LinguisticProfileMarker()
        if not interviewer_texts:
            return LinguisticProfile() #добавить обработчик ошибки

        avg_phrase_length = self._avg_word_count(interviewer_texts)
        number_of_questions = mean([text.count("?") for text in interviewer_texts])

        questions = [text for text in interviewer_texts if "?" in text]
        if questions:
            avg_question_length = self._avg_word_count(questions)
        else:
            avg_question_length = 0.0

        multi_sentence_ratio = self._multi_sentence_ratio(interviewer_texts)

        empathy_density = self._marker_density(interviewer_texts, markers.EMPATHY_MARKERS)
        hedging_density = self._marker_density(interviewer_texts, markers.HEDGING_MARKERS)
        pressure_density = self._marker_density(interviewer_texts, markers.PRESSURE_MARKERS)
        filler_density = self._marker_density(interviewer_texts, markers.FILLER_MARKERS)
        formal_density = self._marker_density(interviewer_texts, markers.FORMAL_MARKERS)
        provocation_density = self._marker_density(interviewer_texts, markers.PROVOCATION_MARKERS)

        ling_profile = LinguisticProfile(empathy_density=empathy_density,
                                         hedging_density=hedging_density,
                                         pressure_density=pressure_density,
                                         filler_density=filler_density,
                                         formal_density=formal_density,
                                         provocation_density=provocation_density,
                                         avg_question_length=avg_question_length,
                                         avg_phrase_length=avg_phrase_length,
                                         multi_sentence_ratio=multi_sentence_ratio,
                                         number_of_questions= number_of_questions)

        return ling_profile


    def _marker_density(self, texts: List[str], markers: List[str]) -> float:
        total_words = sum(len(re.findall(r"\w+", text.lower(), flags=re.UNICODE)) for text in texts)
        if total_words == 0:
            return 0.0

        total_matches = 0
        for phrase in texts:
            lower_phrase = phrase.lower()
            total_matches += sum(lower_phrase.count(marker.lower()) for marker in markers)

        density = total_matches/total_words
        return density


    def _avg_word_count(self, texts: List[str]) -> float:
        if not texts:
            return 0.0
        count = mean(len(re.findall(r"\w+", text, flags=re.UNICODE)) for text in texts)
        return count


    def _multi_sentence_ratio(self, texts: List[str]) -> float:
        if not texts:
            return 0.0
        count = sum(1 for text in texts if len(re.split(r"[.!?]+", text)) > 2)
        ratio = count / len(texts)
        return ratio