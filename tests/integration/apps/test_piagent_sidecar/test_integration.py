"""Integration tests that spawn a real Node.js sidecar process."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from apps.runtime.piagent_sidecar_client import PiAgentSidecarClient, PiAgentSidecarResult


def _check_pi_mono_available() -> bool:
    """Check that pi-mono is accessible from the worktree.

    Path from test file up to worktree root:
      parents[0] = test_piagent_sidecar/tests/integration/apps/
      parents[1] = test_piagent_sidecar/tests/integration/apps/
      parents[2] = test_piagent_sidecar/tests/integration/
      parents[3] = test_piagent_sidecar/tests/
      parents[4] = .worktrees/feat-piagent-sidecar/   <- worktree root
      .worktrees/feat-piagent-sidecar/parents[0] = .worktrees/
      .worktrees/feat-piagent-sidecar/parents[1] = e-agent-os/
      .worktrees/feat-piagent-sidecar/parents[2] = ai-project/
      ai-project/pi-mono = pi-mono
    """
    worktree_root = Path(__file__).parents[4]
    sidecar_pkg = worktree_root / "apps" / "runtime" / "sidecar" / "package.json"
    pi_mono = worktree_root.parents[2] / "pi-mono" / "package.json"
    return sidecar_pkg.exists() and pi_mono.exists()


def _check_api_key_available() -> bool:
    """Check that at least one pi-mono-compatible API key is present in the environment.

    pi-mono supports: ANTHROPIC_API_KEY, OPENAI_API_KEY, ANTHROPIC_AUTH_TOKEN, etc.
    The sidecar subprocess inherits the test process's env, so these must be set in
    the shell that runs pytest (or in the pytest process environment).
    """
    api_key_vars = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_OAUTH_TOKEN",
        "MINIMAX_API_KEY",
        "MINIMAX_CN_API_KEY",
        "GETNOTE_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
    ]
    return any(os.environ.get(v) for v in api_key_vars)


PI_MONO_SKIP = pytest.mark.skipif(
    not _check_pi_mono_available(),
    reason="pi-mono not available at expected sibling path",
)

API_KEY_SKIP = pytest.mark.skipif(
    not _check_api_key_available(),
    reason="No pi-mono API key in environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)",
)


@PI_MONO_SKIP
@API_KEY_SKIP
class TestPiAgentSidecarIntegration:
    """End-to-end integration tests with a real sidecar process."""

    @pytest.fixture
    async def client(self, tmp_path: Path) -> PiAgentSidecarClient:
        """Start a real sidecar and yield the client, then clean up."""
        worktree_root = Path(__file__).parents[4]
        sidecar_script = worktree_root / "apps" / "runtime" / "sidecar" / "src" / "index.ts"
        # Unix socket paths are capped at ~104 bytes on macOS; tmp_path is too long
        import uuid

        socket_path = Path(f"/tmp/piagent-test-{uuid.uuid4().hex[:8]}.sock")
        c = PiAgentSidecarClient(
            socket_path=socket_path,
            startup_timeout=20.0,
            request_timeout=60.0,
            sidecar_script=sidecar_script,
        )
        await c.start()
        yield c
        await c.stop()

    @pytest.mark.asyncio
    async def test_invoke_returns_result(self, client: PiAgentSidecarClient):
        """invoke() returns a PiAgentSidecarResult with non-empty answer."""
        result = await client.invoke("What is 1+1?")
        assert isinstance(result, PiAgentSidecarResult)
        assert result.answer != ""

    @pytest.mark.asyncio
    async def test_invoke_session_id_preserved(self, client: PiAgentSidecarClient):
        """Same session_id on two calls means the second call sees context."""
        await client.invoke("Remember: my favorite color is blue", session_id="test-sess")
        result2 = await client.invoke("What is my favorite color?", session_id="test-sess")
        assert "blue" in result2.answer.lower()

    @pytest.mark.asyncio
    async def test_invoke_streaming_yields_events(self, client: PiAgentSidecarClient):
        """invoke_streaming() yields event then result."""
        events = []
        async for event in client.invoke_streaming("Say hello in one word"):
            events.append(event)
            if event.type == "result":
                break
        assert len(events) >= 2, "Should get at least one event + result"
        assert any(e.type == "result" for e in events)
