"""Helpers for agent-facing structured observations."""

from __future__ import annotations

import json
from typing import Any, Dict


def render_observation(payload: Dict[str, Any]) -> str:
    """Return a stable JSON observation string for tool responses."""
    return json.dumps(payload, indent=2, sort_keys=True)
