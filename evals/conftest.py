"""Skip the live-LLM evals unless explicitly requested.

The tests in this directory call the real OpenCode Go API and spend real
translation quota, so they must never run as part of the normal suite or CI.
Run them deliberately with::

    RUN_EVALS=1 uv run pytest evals/ -q
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_EVALS") != "1":
        skip = pytest.mark.skip(
            reason="live-LLM eval; set RUN_EVALS=1 to run (spends API quota)"
        )
        for item in items:
            item.add_marker(skip)
