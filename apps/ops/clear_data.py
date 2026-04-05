#!/usr/bin/env python
"""Clear all runtime data from ops database, keeping only schema."""

import os

DB_PATH = os.environ.get("OPS_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "data", "ops.db"))


def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}, nothing to clear.")
        return

    print(f"Clearing database: {DB_PATH}")
    os.remove(DB_PATH)
    print(f"  Deleted {DB_PATH}")

    # Re-initialize with seed data
    from apps.ops.db import init_db

    init_db()
    print("  Re-seeded with baseline data.")
    print("Done.")


if __name__ == "__main__":
    main()
