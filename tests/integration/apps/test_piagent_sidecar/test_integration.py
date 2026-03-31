"""Integration tests that spawn a real Node.js sidecar process."""
from __future__ import annotations

import asyncio
import pytest
from pathlib import Path
from apps.runtime.piagent_sidecar_client import PiAgentSidecarClient, PiAgentSidecarResult


def _check_pi_mono_available() -> bool:
    """Check that pi-mono is accessible from the worktree."""
    worktree_root = Path(__file__).parents[5]
    sidecar_pkg = worktree_root / "apps" / "runtime" / "sidecar" / "package.json"
    pi_mono = worktree_root.parent / "pi-mono" / "package.json"
    return sidecar_pkg.exists() and pi_mono.exists()


PI_MONO_SKIP = pytest.mark.skipif(
    not _check_pi_mono_available(),
    reason="pi-mono not available at expected sibling path",
)


@PI_MONO_SKIP
class TestPiAgentSidecarIntegration:
    """End-to-end integration tests with a real sidecar process."""

    @pytest.fixture
    async def client(self, tmp_path: Path) -> PiAgentSidecarClient:
        """Start a real sidecar and yield the client, then clean up."""
        worktree_root = Path(__file__).parents[5]
        sidecar_script = worktree_root / "apps" / "runtime" / "sidecar" / "src" / "index.ts"
        c = PiAgentSidecarClient(
            socket_path=tmp_path / "e2e.sock",
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
