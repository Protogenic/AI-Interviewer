import json
import pytest

from ai_service.services.profile_repository import GetProfileInfo
from ai_service.models.build_profile import InterviewerProfile, LinguisticProfile, Template
from ai_service.exeptions.generation_error import CharacterNotFound, ProfileDataCorruptedError


class TestLoadProfile:
    def test_loads_valid_profile(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.load_profile("dud")
        assert isinstance(profile, InterviewerProfile)
        assert profile.interviewer_id == "dud"

    def test_raises_character_not_found_for_missing_file(self, tmp_path):
        repo = GetProfileInfo(profile_dir=str(tmp_path))
        with pytest.raises(CharacterNotFound) as exc_info:
            repo.load_profile("unknown")
        assert "unknown" in str(exc_info.value)

    def test_raises_profile_data_corrupted_for_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad_profile.json"
        bad_file.write_text("{ invalid json !!!", encoding="utf-8")
        repo = GetProfileInfo(profile_dir=str(tmp_path))
        with pytest.raises(ProfileDataCorruptedError):
            repo.load_profile("bad")

    def test_linguistic_profile_fields(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.load_profile("dud")
        ling = profile.linguistic_profile
        assert isinstance(ling, LinguisticProfile)
        assert ling.avg_question_length == 15.0
        assert ling.empathy_density == 0.1

    def test_templates_parsed(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.load_profile("dud")
        assert len(profile.templates) == 1
        assert isinstance(profile.templates[0], Template)

    def test_reactivity_matrix_present(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.load_profile("dud")
        assert "explanation" in profile.reactivity_matrix

    def test_characteristic_phrases_present(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.load_profile("dud")
        assert "Подождите" in profile.characteristic_phrases


class TestGetProfile:
    def test_get_profile_loads_if_not_cached(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        profile = repo.get_profile("dud")
        assert isinstance(profile, InterviewerProfile)

    def test_get_profile_uses_cache(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        p1 = repo.get_profile("dud")
        p2 = repo.get_profile("dud")
        assert p1 is p2


class TestGetReactivityMatrix:
    def test_returns_dict(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        matrix = repo.get_reactivity_matrix("dud")
        assert isinstance(matrix, dict)
        for key, row in matrix.items():
            assert isinstance(row, dict)

class TestGetTemplates:
    def test_returns_list_of_templates(self, profile_json_file):
        repo = GetProfileInfo(profile_dir=str(profile_json_file))
        templates = repo.get_templates("dud")
        assert isinstance(templates, list)
        assert all(isinstance(t, Template) for t in templates)


class TestProfileWithMissingFields:
    def test_missing_linguistic_fields_use_defaults(self, tmp_path):
        data = {
            "interviewer_id": "sobchak",
            "linguistic_profile": {},
            "reactivity_matrix": {},
            "templates": [],
            "characteristic_phrases": [],
        }
        (tmp_path / "sobchak_profile.json").write_text(json.dumps(data), encoding="utf-8")
        repo = GetProfileInfo(profile_dir=str(tmp_path))
        profile = repo.load_profile("sobchak")
        assert profile.linguistic_profile.empathy_density == 0.0
        assert profile.linguistic_profile.avg_question_length == 0.0
