from __future__ import annotations

"""ops.db — public API re-exported from sub-modules for backward compatibility.

New code should import directly from the sub-modules:
  from ._schema      import get_db, run_schema
  from ._seed        import seed_all, seed_tools
  from ._blueprints  import get_blueprint_config, save_blueprint_config
  from ._executions  import record_execution, get_recent_executions
  from ._dashboard   import get_status_dist, get_task_trend, get_activity_feed, ...
"""

from ._blueprints import get_blueprint_config, save_blueprint_config  # noqa: E402
from ._dashboard import (  # noqa: E402
    get_activity_feed,
    get_capability_dist,
    get_status_dist,
    get_task_detail,
    get_task_trend,
    get_token_daily,
)
from ._executions import get_recent_executions, record_execution  # noqa: E402
from ._schema import BASE_DIR, DB_PATH, get_cursor, get_db, run_schema  # noqa: E402
from ._seed import OPENCLAW_BUILTIN_TOOLS, seed_all, seed_tools  # noqa: E402

# ── Backward-compatible init_db (calls the full seed pipeline) ─────────────────


def init_db() -> None:
    """Run schema migrations + seed all data.

    Kept for backward compatibility. New code should call run_schema() and
    seed_all() separately if ordering matters.
    """
    run_schema()
    seed_all()
    seed_tools()


__all__ = [
    # Connection
    "get_db",
    "get_cursor",
    "BASE_DIR",
    "DB_PATH",
    # Schema
    "run_schema",
    "init_db",
    # Seed
    "seed_all",
    "seed_tools",
    "OPENCLAW_BUILTIN_TOOLS",
    # Blueprints
    "get_blueprint_config",
    "save_blueprint_config",
    # Executions
    "record_execution",
    "get_recent_executions",
    # Dashboard
    "get_status_dist",
    "get_capability_dist",
    "get_task_detail",
    "get_task_trend",
    "get_token_daily",
    "get_activity_feed",
]
