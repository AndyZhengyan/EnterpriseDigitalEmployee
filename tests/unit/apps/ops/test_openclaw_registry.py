# tests/unit/apps/ops/test_openclaw_registry.py
import json

import pytest

from apps.ops.openclaw_registry import OpenclawAgentRegistry, generate_soul_md


@pytest.fixture
def tmp_openclaw(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    agent_dir = tmp_path / "agents" / "deep-work" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "auth-profiles.json").write_text(json.dumps({"profiles": {}}))
    (agent_dir / "models.json").write_text(json.dumps({"models": {}}))

    return tmp_path, agents_dir


@pytest.fixture
def registry(tmp_openclaw):
    tmp_path, agents_dir = tmp_openclaw
    return OpenclawAgentRegistry(
        openclaw_dir=tmp_path,
        agents_dir=agents_dir,
    )


def test_register_agent_creates_directory_and_files(registry):
    success, agent_id = registry.register_agent(
        blueprint_id="av-test-001",
        alias="测试员",
        role="测试专员",
        department="测试部",
        soul={"description": "专业测试员", "communication_style": "简洁"},
    )
    assert success is True

    agent_dir = registry.agents_dir / "av-test-001" / "agent"
    assert agent_dir.exists()
    assert (agent_dir / "SOUL.md").exists()
    assert (agent_dir / "auth-profiles.json").exists()
    assert (agent_dir / "models.json").exists()


def test_register_agent_soul_md_content(registry):
    registry.register_agent(
        blueprint_id="av-test-001",
        alias="测试员",
        role="测试专员",
        department="测试部",
        soul={"description": "专业测试员", "communication_style": "简洁"},
    )
    soul_content = (registry.agents_dir / "av-test-001" / "agent" / "SOUL.md").read_text()
    assert "测试员" in soul_content
    assert "测试专员" in soul_content
    assert "测试部" in soul_content
    assert "av-test-001" in soul_content
    assert "专业测试员" in soul_content
    assert "简洁" in soul_content


def test_register_agent_is_idempotent(registry):
    registry.register_agent(
        blueprint_id="av-test-001",
        alias="测试员",
        role="测试专员",
        department="测试部",
        soul={"description": "v1", "communication_style": "简洁"},
    )
    success, agent_id = registry.register_agent(
        blueprint_id="av-test-001",
        alias="测试员",
        role="测试专员",
        department="测试部",
        soul={"description": "v2", "communication_style": "简洁"},
    )
    assert success is True
    soul_content = (registry.agents_dir / "av-test-001" / "agent" / "SOUL.md").read_text()
    assert "v2" in soul_content


def test_remove_agent_deletes_directory(registry):
    registry.register_agent(
        blueprint_id="av-test-001",
        alias="测试员",
        role="测试专员",
        department="测试部",
        soul={"description": "专业", "communication_style": "简洁"},
    )
    agent_dir = registry.agents_dir / "av-test-001"
    assert agent_dir.exists()
    registry.remove_agent("av-test-001")
    assert not agent_dir.exists()


def test_remove_agent_nonexistent_does_not_raise(registry):
    registry.remove_agent("nonexistent")


def test_generate_soul_md():
    md = generate_soul_md(
        blueprint_id="av-test-001",
        alias="TestAgent",
        role="Tester",
        department="QA",
        soul={"description": "Reliable", "communication_style": "Clear"},
    )
    assert "TestAgent" in md
    assert "Tester" in md
    assert "QA" in md
    assert "av-test-001" in md
    assert "Reliable" in md
    assert "Clear" in md
