"""SkillHub registry and lifecycle tests."""

from __future__ import annotations

import pytest

from apps.skill_hub.errors import SkillHubError, SkillNotFoundError
from apps.skill_hub.models import Skill, SkillLevel, SkillStatus
from apps.skill_hub.registry import (
    get,
    list_all,
    register,
    update_status,
)


def _reset():
    import apps.skill_hub.registry as reg

    reg._registry.clear()


class TestSkillRegistry:
    """Registry tests."""

    def test_register_and_get(self):
        _reset()
        s = Skill(id="test-skill", name="Test Skill", level=SkillLevel.L2)
        register(s)
        assert get("test-skill").id == "test-skill"

    def test_get_unknown_raises(self):
        _reset()
        with pytest.raises(SkillNotFoundError):
            get("ghost")

    def test_list_all_filters_by_status(self):
        _reset()
        register(Skill(id="a", name="A", status=SkillStatus.PUBLISHED))
        register(Skill(id="b", name="B", status=SkillStatus.DRAFT))
        result = list_all(status=SkillStatus.PUBLISHED)
        assert len(result) == 1
        assert result[0].id == "a"


class TestLifecycleTransitions:
    """Lifecycle state machine tests."""

    def test_draft_to_testing_ok(self):
        _reset()
        s = Skill(id="t1", name="T1", status=SkillStatus.DRAFT)
        register(s)
        updated = update_status("t1", SkillStatus.TESTING)
        assert updated.status == SkillStatus.TESTING

    def test_draft_to_deprecated_invalid(self):
        _reset()
        s = Skill(id="t2", name="T2", status=SkillStatus.DRAFT)
        register(s)
        with pytest.raises(SkillHubError) as exc:
            update_status("t2", SkillStatus.DEPRECATED)
        assert "Invalid transition" in exc.value.message

    def test_published_to_deprecated_ok(self):
        _reset()
        s = Skill(id="t3", name="T3", status=SkillStatus.PUBLISHED)
        register(s)
        updated = update_status("t3", SkillStatus.DEPRECATED)
        assert updated.status == SkillStatus.DEPRECATED

    def test_deprecated_is_terminal(self):
        _reset()
        s = Skill(id="t4", name="T4", status=SkillStatus.DEPRECATED)
        register(s)
        with pytest.raises(SkillHubError):
            update_status("t4", SkillStatus.DRAFT)
