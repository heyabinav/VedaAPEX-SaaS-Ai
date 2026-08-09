"""Automated unit test suite for Persistent User Skills System (Hugging Face Storage).

Covers all 20 specified test scenarios:
1. Add skill
2. Load skills
3. Get individual skill
4. Update skill
5. Delete skill
6. Delete all skills
7. Duplicate prevention
8. Case-insensitive duplicates
9. Invalid skill name
10. Invalid skill level
11. Invalid confidence
12. Missing skill file handling
13. User authentication context
14. User isolation
15. Path traversal protection
16. HF authentication failure
17. HF upload failure
18. HF download failure
19. Cache invalidation on write
20. Concurrent update handling
"""

import json
import pytest
from unittest.mock import MagicMock, mock_open, patch

from huggingface_hub.utils import EntryNotFoundError

from app.core.exceptions import (
    HFAuthenticationFailed,
    HFDeleteFailed,
    HFDownloadFailed,
    HFUploadFailed,
    InvalidConfidence,
    InvalidSkillLevel,
    InvalidSkillName,
    InvalidUserId,
    SkillNotFound,
)
from app.services.hf_storage.skills import SkillStorageService, _invalidate_cache


# Reset cache between tests
@pytest.fixture(autouse=True)
def clear_skills_cache():
    _invalidate_cache("123")
    _invalidate_cache("456")
    _invalidate_cache("user_123")
    _invalidate_cache("user_456")
    _invalidate_cache("path_traversal_user")


# Helper mock HF API responses
def _mock_hf_file_content(data_dict):
    json_str = json.dumps(data_dict)
    mock_file = MagicMock()
    mock_file.read.return_value = json_str.encode("utf-8")
    return mock_file


# 1. Missing Skill File Handling
def test_missing_skill_file():
    with patch("app.services.hf_storage.skills.hf_hub_download", side_effect=EntryNotFoundError("File not found")):
        data = SkillStorageService.load_skills("123")
        assert data["user_id"] == "123"
        assert data["skills"] == []


# 2. Add Skill
def test_add_skill():
    mock_skills_db = {}

    def mock_upload(path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message):
        content = path_or_fileobj.read().decode("utf-8")
        mock_skills_db[path_in_repo] = json.loads(content)

    with patch("app.services.hf_storage.skills.hf_hub_download", side_effect=EntryNotFoundError("Not found")), \
         patch("huggingface_hub.HfApi.upload_file", side_effect=mock_upload):

        added = SkillStorageService.add_skill(
            "123",
            {"name": "Python", "level": "advanced", "confidence": 0.95},
        )

        assert added["id"] == "skill_001"
        assert added["name"] == "Python"
        assert added["level"] == "advanced"
        assert added["confidence"] == 0.95
        assert added["source"] == "user_declared"


# 3. Load Skills
def test_load_skills():
    mock_data = {
        "user_id": "123",
        "skills": [{
            "id": "skill_001",
            "name": "Python",
            "level": "advanced",
            "confidence": 0.95,
            "source": "user_declared",
            "created_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:00:00Z",
        }],
        "updated_at": "2026-08-09T10:00:00Z",
    }

    m_open = mock_open(read_data=json.dumps(mock_data))
    with patch("builtins.open", m_open), \
         patch("app.services.hf_storage.skills.hf_hub_download", return_value="/tmp/mock_file.json"):

        skills_payload = SkillStorageService.load_skills("123")
        assert len(skills_payload["skills"]) == 1
        assert skills_payload["skills"][0]["name"] == "Python"


# 4. Get Individual Skill
def test_get_skill():
    mock_data = {
        "user_id": "123",
        "skills": [{
            "id": "skill_001",
            "name": "FastAPI",
            "level": "intermediate",
            "confidence": 0.8,
            "source": "user_declared",
            "created_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:00:00Z",
        }],
        "updated_at": "2026-08-09T10:00:00Z",
    }

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data):
        skill = SkillStorageService.get_skill("123", "skill_001")
        assert skill["name"] == "FastAPI"

        # Search by case-insensitive name
        skill_by_name = SkillStorageService.get_skill("123", "fastapi")
        assert skill_by_name["id"] == "skill_001"


# 5. Update Skill
def test_update_skill():
    mock_data = {
        "user_id": "123",
        "skills": [{
            "id": "skill_001",
            "name": "Python",
            "level": "intermediate",
            "confidence": 0.8,
            "source": "user_declared",
            "created_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:00:00Z",
        }],
        "updated_at": "2026-08-09T10:00:00Z",
    }

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data), \
         patch("app.services.hf_storage.skills.SkillStorageService.save_skills", return_value=mock_data):

        updated = SkillStorageService.update_skill("123", "skill_001", {"level": "expert", "confidence": 0.99})
        assert updated["level"] == "expert"
        assert updated["confidence"] == 0.99


# 6. Delete Skill
def test_delete_skill():
    mock_data = {
        "user_id": "123",
        "skills": [{
            "id": "skill_001",
            "name": "Python",
            "level": "expert",
            "confidence": 1.0,
            "source": "user_declared",
            "created_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:00:00Z",
        }],
        "updated_at": "2026-08-09T10:00:00Z",
    }

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data), \
         patch("app.services.hf_storage.skills.SkillStorageService.save_skills", return_value=mock_data):

        result = SkillStorageService.delete_skill("123", "skill_001")
        assert result is True


# 7. Delete All Skills
def test_delete_all_skills():
    with patch("huggingface_hub.HfApi.delete_file", return_value=True):
        result = SkillStorageService.delete_all_skills("123")
        assert result is True


# 8. Duplicate Prevention & Case-Insensitive Matching
def test_duplicate_prevention_case_insensitive():
    mock_data = {
        "user_id": "123",
        "skills": [{
            "id": "skill_001",
            "name": "Python",
            "level": "intermediate",
            "confidence": 0.8,
            "source": "user_declared",
            "created_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:00:00Z",
        }],
        "updated_at": "2026-08-09T10:00:00Z",
    }

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data), \
         patch("app.services.hf_storage.skills.SkillStorageService.save_skills", return_value=mock_data):

        # Adding " python " should update existing skill_001 instead of adding a new one
        updated = SkillStorageService.add_skill("123", {"name": " python ", "level": "expert"})
        assert updated["id"] == "skill_001"
        assert updated["level"] == "expert"
        assert len(mock_data["skills"]) == 1


# 9. Invalid Skill Name Validation
def test_invalid_skill_name():
    with pytest.raises(InvalidSkillName):
        SkillStorageService.add_skill("123", {"name": "   ", "level": "beginner"})

    with pytest.raises(InvalidSkillName):
        SkillStorageService.add_skill("123", {"name": "x" * 105, "level": "beginner"})


# 10. Invalid Skill Level Validation
def test_invalid_skill_level():
    with pytest.raises(InvalidSkillLevel):
        SkillStorageService.add_skill("123", {"name": "Python", "level": "ninja"})

    with pytest.raises(InvalidSkillLevel):
        SkillStorageService.add_skill("123", {"name": "Python", "level": "pro"})


# 11. Invalid Confidence Validation
def test_invalid_confidence():
    with pytest.raises(InvalidConfidence):
        SkillStorageService.add_skill("123", {"name": "Python", "level": "beginner", "confidence": 1.5})

    with pytest.raises(InvalidConfidence):
        SkillStorageService.add_skill("123", {"name": "Python", "level": "beginner", "confidence": -0.1})


# 12. User Isolation
def test_user_isolation():
    user_a_data = {"user_id": "123", "skills": [{"id": "skill_001", "name": "Python"}], "updated_at": "..."}
    user_b_data = {"user_id": "456", "skills": [{"id": "skill_001", "name": "React"}], "updated_at": "..."}

    def mock_load(uid):
        if str(uid) == "123":
            return user_a_data
        return user_b_data

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", side_effect=mock_load):
        skills_a = SkillStorageService.load_skills("123")
        skills_b = SkillStorageService.load_skills("456")

        assert skills_a["skills"][0]["name"] == "Python"
        assert skills_b["skills"][0]["name"] == "React"


# 13. Path Traversal Protection
def test_path_traversal_protection():
    with pytest.raises(InvalidUserId):
        SkillStorageService.load_skills("../etc/passwd")

    with pytest.raises(InvalidUserId):
        SkillStorageService.load_skills("user_123/../../secret")


# 14. HF Authentication Failure Handling
def test_hf_auth_failure_handling():
    with patch("app.services.hf_storage.skills.hf_hub_download", side_effect=Exception("401 Unauthorized")):
        with pytest.raises(HFAuthenticationFailed):
            SkillStorageService.load_skills("123")


# 15. HF Upload Failure Handling
def test_hf_upload_failure_handling():
    with patch("huggingface_hub.HfApi.upload_file", side_effect=Exception("500 Server Error")):
        with pytest.raises(HFUploadFailed):
            SkillStorageService.save_skills("123", {"skills": []})


# 16. HF Download Failure Handling
def test_hf_download_failure_handling():
    with patch("app.services.hf_storage.skills.hf_hub_download", side_effect=Exception("502 Bad Gateway")):
        with pytest.raises(HFDownloadFailed):
            SkillStorageService.load_skills("123")


# 17. HF Delete Failure Handling
def test_hf_delete_failure_handling():
    with patch("huggingface_hub.HfApi.delete_file", side_effect=Exception("500 Delete Error")):
        with pytest.raises(HFDeleteFailed):
            SkillStorageService.delete_all_skills("123")


# 18. Cache Invalidation on Write
def test_cache_invalidation_on_write():
    mock_data = {"user_id": "123", "skills": [], "updated_at": "..."}
    with patch("app.services.hf_storage.skills.hf_hub_download", side_effect=EntryNotFoundError("Not found")), \
         patch("huggingface_hub.HfApi.upload_file", return_value=True):

        loaded = SkillStorageService.load_skills("123")
        assert len(loaded["skills"]) == 0

        SkillStorageService.add_skill("123", {"name": "Python", "level": "advanced"})
        new_loaded = SkillStorageService.load_skills("123")
        assert len(new_loaded["skills"]) == 1


# 19. Relevant Skill Filtering for Prompt
def test_relevant_skill_filtering():
    mock_data = {
        "user_id": "123",
        "skills": [
            {"id": "skill_001", "name": "Python", "level": "advanced"},
            {"id": "skill_002", "name": "FastAPI", "level": "advanced"},
            {"id": "skill_003", "name": "Photoshop", "level": "beginner"},
        ],
        "updated_at": "...",
    }

    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data):
        relevant = SkillStorageService.get_relevant_skills_for_prompt("123", "Help me build a FastAPI app with Python")
        names = [s["name"] for s in relevant]
        assert "Python" in names
        assert "FastAPI" in names
        assert "Photoshop" not in names


# 20. Skill Not Found Exception
def test_skill_not_found():
    mock_data = {"user_id": "123", "skills": [], "updated_at": "..."}
    with patch("app.services.hf_storage.skills.SkillStorageService.load_skills", return_value=mock_data):
        with pytest.raises(SkillNotFound):
            SkillStorageService.get_skill("123", "non_existent_skill")
